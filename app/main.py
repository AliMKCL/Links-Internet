from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.reddit_scraper import search_reddit
from app.summarizer import summarize_comments
from app.reddit_websearch_scraper import reddit_query_via_ddg
from datetime import datetime
from app.ranking_posts import ai_rank_posts, score_post, format_post_content
# from app.pushshift_scraper import search_pushshift
from app.database import embed_text, query_db, delete_collection
import threading
from app.utilities import enhance_post_content_for_html, question_statement_classification, post_summary_generation
import re
from app.security import sanitize_input, validate_query_length, log_suspicious_query


app = FastAPI(title="Reddit Gaming Advisor")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")
templates = Jinja2Templates(directory="app/templates")

# Global variables for caching posts between endpoints
# In production, use proper session management or Redis
cached_posts = []
cached_query = ""

def detect_game_from_query(query: str) -> str:
    """
    Detect which game the query is about based on game names/abbreviations in the query.
    Returns the game abbreviation (BOTW, TOTK, etc.) or None if no game detected.
    """
    query_lower = query.lower()
    
    # Game detection mappings
    game_detection = {
        'BOTW': ['botw', 'breath of the wild'],
        'TOTK': ['totk', 'tears of the kingdom'],
        'TP': ['tp', 'twilight princess'],
        'SS': ['ss', 'skyward sword'],
        'MM': ['mm', 'majoras mask', "majora's mask"],
        'OOT': ['oot', 'ocarina of time'],
        'WW': ['ww', 'wind waker'],
    }
    
    for game_abbrev, terms in game_detection.items():
        for term in terms:
            if term in query_lower:
                print(f"Detected game {game_abbrev} from query term: {term}")
                return game_abbrev
    
    return None


# Root endpoint to serve the HTML template
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query")
def query(q: str = Query(..., max_length=512, description="3D Zelda related question"), metric: str = Query("all", description="Time filter for Reddit search")):
    
    #delete_collection()  # For testing, remove later

    # Basic security validation and sanitization
    if not validate_query_length(q, 512):
        log_suspicious_query(q, "Query exceeds maximum length")
        return {
            "query": q[:100] + "..." if len(q) > 100 else q,
            "results": [],
            "has_summary": False,
            "database_status": "Invalid query",
            "error": "Query is too long. Please keep your question under 512 characters."
        }
    
    # Sanitize input to prevent injection and encoding attacks
    original_query = q
    q = sanitize_input(q)
    
    if not q or len(q.strip()) < 3:
        log_suspicious_query(original_query, "Query too short or empty after sanitization")
        return {
            "query": original_query,
            "results": [],
            "has_summary": False,
            "database_status": "Invalid query",
            "error": "Please enter a valid question (at least 3 characters)."
        }

    initial_query = q
    print(question_statement_classification(q))  # Print the classification result for debugging
    
    # Check if query is related to BOTW or TOTK only
    query_lower = q.lower()
    # Remove common punctuation to handle cases like "botw?" or "totk!"
    import string
    query_cleaned = query_lower.translate(str.maketrans('', '', string.punctuation))
    
    # Define allowed game terms (BOTW and TOTK only)
    allowed_terms = ['botw', 'breath of the wild', 'totk', 'tears of the kingdom']
    
    # Check if any of the allowed terms are in the query
    is_related_query = any(term in query_cleaned for term in allowed_terms)
    
    if not is_related_query:
        return {
            "query": q,
            "results": [],
            "has_summary": False,
            "database_status": "Unrelated query",
            "error": "This service only supports queries related to Breath of the Wild (BOTW) or Tears of the Kingdom (TOTK). Please ask a question about one of these games."
        }
    
    # Detect which game the query is about
    detected_game = detect_game_from_query(q)
    
    # First, check if relevant posts exist in the database
    try:
        db_documents, db_distances, db_metadatas = query_db(q, n_results=10, game_filter=detected_game)
        # Check if we have good matches (distance < 0.3 is generally considered a good match)
        good_matches = [doc for i, doc in enumerate(db_documents) if db_distances[i] < 0.5]
        
        #test_flag = False

        # If relevant posts are found in the database, use them directly
        if  good_matches and len(good_matches) >= 5:  # If we have at least 5 good matches
            print("Found relevant posts in database!")
            
            # Create mock post objects from database results for consistent formatting
            all_posts = []
            for i, doc in enumerate(db_documents[:10]):  # For all documents (top 10), the posts are as follows:
                
                post = {
                    "title": db_metadatas[i].get("original_title", doc),  # Use original title if available, fallback to doc
                    "url": db_metadatas[i]["url"],
                    "content": db_metadatas[i].get("content", ""),
                    "comments": db_metadatas[i].get("comments", "").split(" | ") if db_metadatas[i].get("comments") else [],  # Convert string back to list
                    "subreddit": db_metadatas[i].get("subreddit", "database"),
                    "_score": 1.0 - db_distances[i],  # Convert distance to score
                    "created_utc": db_metadatas[i].get("created_utc"),
                    "game": db_metadatas[i].get("game")  # Include game metadata
                }
                all_posts.append(post)
            
            database_message = "Found in the database"
            
        # If no relevant posts are found in the db, fetch new ones.
        else:
            print("Relevant posts not found in database. Fetching new posts...")
            database_message = "Relevant posts not found in database"
            
            # Original fetching logic
            results = {}
            shared = {} # Dictionaries are mutable --> Shared between threads

            def fetch_ddg():
                subreddit = "tearsofthekingdom"
                try:
                    posts, clean_query = reddit_query_via_ddg(q, max_posts=200, metric=metric, subreddit=subreddit)
                    results['ddg'] = posts
                    shared['clean_query'] = clean_query # Cleaned query is saved here to the common dictionary
                except Exception as e:
                    print(f"Error in fetch_ddg: {e}")
                    results['ddg'] = []
                    
            def fetch_reddit():
                subreddit = "tearsofthekingdom"
                try:
                    posts, clean_query = search_reddit(q, limit=200, metric=metric, subreddit=subreddit)
                    results['reddit'] = posts
                    shared['clean_query'] = clean_query
                except Exception as e:
                    print(f"Error in fetch_reddit: {e}")
                    results['reddit'] = []

            ddg_thread = threading.Thread(target=fetch_ddg)
            reddit_thread = threading.Thread(target=fetch_reddit)
            ddg_thread.start()
            reddit_thread.start()
            ddg_thread.join()
            reddit_thread.join()

            clean_query = shared.get('clean_query', q)  # Use cleaned query if available
            q = clean_query # For easy changes
            
            print("Cleaned query main: ", clean_query)

            ddg_posts = results['ddg']  # is a dict
            reddit_posts = results['reddit'] # is a list

            # Combine and deduplicate posts by URL 
            all_posts_dict = {}

            print(type(ddg_posts), type(reddit_posts)) # Should be list, list
            print("Num ddg: ",len(ddg_posts), "Num reddit: ",len(reddit_posts)) # Should be > 0, > 0

            for post in ddg_posts + reddit_posts: # + pushshift_posts:
                url = post["url"]
                # Extract subreddit if not present
                if 'subreddit' not in post or not post['subreddit'] or post['subreddit'] == 'unknown':
                    match = re.search(r"reddit.com/r/([a-zA-Z0-9_]+)/", url)
                    if match:
                        post['subreddit'] = match.group(1)
                    else:
                        post['subreddit'] = 'unknown'
                if url not in all_posts_dict or score_post(post, q) > score_post(all_posts_dict[url], q):
                    all_posts_dict[url] = post  # Overwrites duplicates, keeps highest scored occurrence.
            all_posts = list(all_posts_dict.values())   # A list of all unique post values

            #clean_comments(all_posts)

            embed_text(all_posts)
            print("Embedded all posts. Now querying database for results...")
            
            # Query the database to get the newly embedded posts
            db_documents, db_distances, db_metadatas = query_db(clean_query, n_results=10, game_filter=detected_game)
            print("Database query results:", len(db_documents), "documents found")
            
            # Create post objects from database results for consistent formatting
            all_posts = []
            for i, doc in enumerate(db_documents):
                post = {
                    "title": db_metadatas[i].get("original_title", doc),  # Use original title if available, fallback to doc
                    "url": db_metadatas[i]["url"],
                    "content": db_metadatas[i].get("content", ""),
                    "comments": db_metadatas[i].get("comments", "").split(" | ") if db_metadatas[i].get("comments") else [],  # Convert string back to list
                    "subreddit": db_metadatas[i].get("subreddit", "database"),
                    "_score": 1.0 - db_distances[i],  # Convert distance to score (database similarity score)
                    "created_utc": db_metadatas[i].get("created_utc"),
                    "game": db_metadatas[i].get("game")  # Include game metadata
                }
                all_posts.append(post)
            
            database_message = "Found in the database (newly added)"
            
    except Exception as e:
        print(f"Error querying database: {e}")
        database_message = "Database query failed, fetching new posts"
        
        # Fallback to original fetching logic
        results = {}
        shared = {}

        def fetch_ddg():
            subreddit = "Breath_of_the_Wild"
            try:
                posts, clean_query = reddit_query_via_ddg(q, max_posts=200, metric=metric, subreddit=subreddit)
                results['ddg'] = posts
                shared['clean_query'] = clean_query
            except Exception as e:
                print(f"Error in fetch_ddg: {e}")
                results['ddg'] = []
                
        def fetch_reddit():
            subreddit = "Breath_of_the_Wild"
            try:
                posts, clean_query = search_reddit(q, limit=200, metric=metric, subreddit=subreddit)
                results['reddit'] = posts
                shared['clean_query'] = clean_query
            except Exception as e:
                print(f"Error in fetch_reddit: {e}")
                results['reddit'] = []

        ddg_thread = threading.Thread(target=fetch_ddg)
        reddit_thread = threading.Thread(target=fetch_reddit)
        ddg_thread.start()
        reddit_thread.start()
        ddg_thread.join()
        reddit_thread.join()

        clean_query = shared.get('clean_query', q)
        q = clean_query

        ddg_posts = results['ddg']
        reddit_posts = results['reddit']
        all_posts_dict = {}

        for post in ddg_posts + reddit_posts:
            url = post["url"]
            if 'subreddit' not in post or not post['subreddit'] or post['subreddit'] == 'unknown':
                match = re.search(r"reddit.com/r/([a-zA-Z0-9_]+)/", url)
                if match:
                    post['subreddit'] = match.group(1)
                else:
                    post['subreddit'] = 'unknown'
            if url not in all_posts_dict or score_post(post, q) > score_post(all_posts_dict[url], q):
                all_posts_dict[url] = post
        all_posts = list(all_posts_dict.values())
        
        embed_text(all_posts)
        print("Embedded all posts. Now querying database for results...")
        
        # Query the database to get the newly embedded posts
        db_documents, db_distances, db_metadatas = query_db(clean_query, n_results=10, game_filter=detected_game)
        print("Database query results:", len(db_documents), "documents found")
        
        # Create post objects from database results for consistent formatting
        all_posts = []
        for i, doc in enumerate(db_documents):
            post = {
                "title": db_metadatas[i].get("original_title", doc),  # Use original title if available, fallback to doc
                "url": db_metadatas[i]["url"],
                "content": db_metadatas[i].get("content", ""),
                "comments": db_metadatas[i].get("comments", "").split(" | ") if db_metadatas[i].get("comments") else [],  # Convert string back to list
                "subreddit": db_metadatas[i].get("subreddit", "database"),
                "_score": 1.0 - db_distances[i],  # Convert distance to score (database similarity score)
                "created_utc": db_metadatas[i].get("created_utc"),
                "game": db_metadatas[i].get("game")  # Include game metadata
            }
            all_posts.append(post)
        
        database_message = "Found in the database (newly added)"

    # Store posts in a global variable for the summary endpoint
    # In production, you'd use a proper cache like Redis
    global cached_posts, cached_query
    cached_posts = all_posts
    cached_query = q

    # Up to here: Fetched and collected under all_posts

    print(f"\nProcessing with message: {database_message}")

    print(("\n ALL POSTS !!!!!!!!!!! \n"))
    for post in all_posts:
        print("Title: ", post["title"] + "\n")
        #if post["content"]:
        #    print("Content: ", post["content"] + "\n")

    # Add post time to each post (if not already present)
    for post in all_posts:
        if "created_utc" not in post:
            post["created_utc"] = None  # Default if missing
        # If post is from PRAW, try to get created_utc
        if hasattr(post, "created_utc"):
            post["created_utc"] = post.created_utc

    # Compute and attach scores to each post for consistent display and sorting
    for post in all_posts:
        if "_score" not in post:  # Only calculate if not already set
            post["_score"] = score_post(post, q)

    # Sort by score, then by recency
    ranked_posts = sorted(
        all_posts,
        key=lambda post: (post["_score"], post.get("created_utc", 0)),
        reverse=True
    )

    # Print scores for debugging
    print("\nRANKED POSTS WITH SCORES:")
    for post in ranked_posts:
        subreddit = post.get('subreddit', 'unknown')
        print(f"Subreddit: {subreddit}")
        print(f"{post['title']} [Score: {post['_score']:.2f}]")
        #question_statement_classification(post["title"])

    """"""
    # Use AI to rank the top x scored posts based on the query (skip if from database)
    if database_message in ["Found in the database", "Found in the database (newly added)"]:
        ai_ranked_posts = ranked_posts[:10]  # Just use top 10 database results
        print("Skipping AI ranking for database results")
    else:
        ai_ranked_posts = ai_rank_posts(ranked_posts[:20], initial_query)

        # Print scores for debugging
        print("\nAI RANKED POSTS WITH SCORES:\n")
        for post in ai_ranked_posts:
            subreddit = post.get('subreddit', 'unknown')
            print(f"Subreddit: {subreddit}")
            print(f"{post['title']} [Score: {post['_score']:.2f}]")
            

    # Skip subreddit grouping - just use the AI-ranked posts in score order
    ai_ranked_posts_sorted = ai_ranked_posts  # Posts are already sorted by score from AI ranking or database query

    summarized_results = []
    for i, post in enumerate(ai_ranked_posts_sorted):
        post_time = post.get("created_utc")
        if post_time:
            date_str = datetime.utcfromtimestamp(post_time).strftime('%Y-%m-%d')
        else:
            date_str = "Unknown date"
        # Format post content for every post
        raw_content = format_post_content(post.get("content", ""))
        post_content = enhance_post_content_for_html(raw_content) if raw_content else ""
        
        # Format comments for display
        comments = post.get("comments", [])
        formatted_comments = ""
        if comments:
            formatted_comments = "<br>".join([f"<div style='background:#f9f9f9;padding:10px;margin:5px 0;border-left:3px solid #185a9d;border-radius:4px;'>{comment}</div>" for comment in comments if comment.strip()])
        
        subreddit = post.get('subreddit', 'unknown')
        
        # Add database message to the first result's title
        title = post['title']
        """
        if i == 0:
            title = f'[{database_message}] {title}'
        """
        
        summarized_results.append({
            "title": f"{title} [Date: {date_str}]", # [Score: {post['_score']:.2f}]
            "url": post["url"],
            "summary": "",  # No summary if ranking by title only
            "content": post_content,  # Formatted post content for all posts
            "comments": formatted_comments,  # Formatted comments for display
            "created_utc": post_time,
            "is_top_post": i == 0,  # Flag to identify top post
            "subreddit": subreddit
        })

    return {
        "query": q,
        "results": summarized_results,
        "has_summary": True,  # Indicates summary is available via separate endpoint
        "database_status": database_message  # Send database status to frontend
    }


# New endpoint for AI summary generation
@app.get("/summary")
def get_summary(q: str = Query(..., max_length=512, description="Original query for summary generation")):
    """Generate AI summary for the cached posts from the previous query"""
    try:
        # Basic security validation and sanitization
        if not validate_query_length(q, 512):
            return {"error": "Query too long"}
        
        q = sanitize_input(q)
        if not q:
            return {"error": "Invalid query"}
        
        # Access cached posts (in production, use proper session management)
        global cached_posts, cached_query
        
        if not cached_posts or cached_query != q:
            return {"error": "No cached posts found for this query. Please run /query first."}
        
        print(f"Generating summary for {len(cached_posts)} posts...")
        ai_summary = post_summary_generation(cached_posts, q)
        print("Summary generated successfully")
        
        return {
            "query": q,
            "ai_summary": ai_summary,
            "post_count": len(cached_posts)
        }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": f"Failed to generate summary: {str(e)}"}

# New endpoint to check database status immediately
@app.get("/check-db")
def check_database(q: str = Query(..., max_length=512, description="Query to check in database")):
    """Check if relevant posts exist in database without fetching new ones"""
    try:
        # Basic security validation and sanitization
        if not validate_query_length(q, 512):
            return {"found_in_database": False, "message": "Query too long"}
        
        original_query = q
        q = sanitize_input(q)
        if not q:
            log_suspicious_query(original_query, "Empty query after sanitization")
            return {"found_in_database": False, "message": "Invalid query"}
        
        # Check if query is related to BOTW or TOTK only
        query_lower = q.lower()
        # Remove common punctuation to handle cases like "botw?" or "totk!"
        import string
        query_cleaned = query_lower.translate(str.maketrans('', '', string.punctuation))
        
        # Define allowed game terms (BOTW and TOTK only)
        allowed_terms = ['botw', 'breath of the wild', 'totk', 'tears of the kingdom']
        
        # Check if any of the allowed terms are in the query
        is_related_query = any(term in query_cleaned for term in allowed_terms)
        
        if not is_related_query:
            return {"found_in_database": False, "message": "Unrelated query"}
        
        # Detect which game the query is about
        detected_game = detect_game_from_query(q)
        db_documents, db_distances, db_metadatas = query_db(q, n_results=10, game_filter=detected_game)
        good_matches = [doc for i, doc in enumerate(db_documents) if db_distances[i] < 0.5]
        
        if good_matches and len(good_matches) >= 5:
            return {"found_in_database": True, "message": "Found in the database"}
        else:
            return {"found_in_database": False, "message": "Relevant posts not found in database"}
    except Exception as e:
        return {"found_in_database": False, "message": "Database query failed"}
