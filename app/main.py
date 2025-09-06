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
from app.utilities import enhance_post_content_for_html, question_statement_classification, post_summary_generation, detect_game_from_query
import re
from app.security import sanitize_input, validate_query_length, log_suspicious_query
import string


app = FastAPI(title="3D Zelda games advisor")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")
templates = Jinja2Templates(directory="app/templates")

# Global variables for caching posts between endpoints
cached_posts = []
cached_query = ""

# Root endpoint to serve the HTML template
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query")
def query(q: str = Query(..., max_length=512, description="3D Zelda related question"), metric: str = Query("all", description="Time filter for Reddit search")):
    
    #delete_collection()  # For easily removing a collection in case of a database refresh.

    # Basic security validation and sanitization for input length.
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

    
    # Check if query is related to BOTW or TOTK only (For the next 5 code snippets)
    query_lower = q.lower()

    # Remove common punctuation to handle cases like "botw?" or "totk!"
    query_cleaned = query_lower.translate(str.maketrans('', '', string.punctuation))
    
    # Define allowed game terms (BOTW and TOTK only). If these are detected in the query, the game discussed will be decided.
    allowed_terms = ['botw', 'breath of the wild', 'totk', 'tears of the kingdom']
    
    is_related_query = any(term in query_cleaned for term in allowed_terms)

    # If query is unrelated to the system's purpose, return an error message
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
        
        # Check if we have good matches (distance < 0.7)
        good_matches = [doc for i, doc in enumerate(db_documents) if db_distances[i] < 0.7]
        
        #test_flag = False (Used to force the program to fetch posts instead of retrieve from database)
 
        # If relevant posts are found in the database, use them directly
        if  good_matches and len(good_matches) >= 5:  # If we have at least 5 good matches
            print("Found relevant posts in database!")
            
            all_posts = []

            # For all documents (top 10), the posts are as follows:
            for i, doc in enumerate(db_documents[:10]): 
                
                post = {
                    "title": db_metadatas[i].get("original_title", doc),  # Use original title if available, fallback to doc
                    "url": db_metadatas[i]["url"],
                    "content": db_metadatas[i].get("content", ""),
                    "comments": db_metadatas[i].get("comments", "").split(" | ") if db_metadatas[i].get("comments") else [],  # Convert string back to list
                    "subreddit": db_metadatas[i].get("subreddit", "database"),
                    "_score": 1.0 - db_distances[i],  
                    "created_utc": db_metadatas[i].get("created_utc"),
                    "game": db_metadatas[i].get("game") 
                }
                all_posts.append(post)
            
            database_message = "Found in the database"
            
        # If no relevant posts are found in the db, fetch new ones.
        else:
            print("Relevant posts not found in database. Fetching new posts...")
            database_message = "Relevant posts not found in database"
            
            results = {}
            shared = {} # Dictionaries are mutable --> Shared between threads

            # Fetch posts through duckduckgo
            def fetch_ddg():
                subreddit = None # For manual fetching using a hardcoded subreddit
                
                try:
                    posts, clean_query = reddit_query_via_ddg(q, max_posts=200, metric=metric, subreddit=subreddit) # Metric input is removed as it will always default to "all time" in the projects context.
                    results['ddg'] = posts
                    shared['clean_query'] = clean_query # Cleaned query is saved here to the common dictionary. It is the query without the part that tells the game (Example: best weapon in botw --> best weapon)
                except Exception as e:
                    print(f"Error in fetch_ddg: {e}")
                    results['ddg'] = []

            # Fetch posts through reddit's API (PRAW)   
            def fetch_reddit():
                subreddit = None
                try:
                    posts, clean_query = search_reddit(q, limit=200, metric=metric, subreddit=subreddit)
                    results['reddit'] = posts
                    shared['clean_query'] = clean_query
                except Exception as e:
                    print(f"Error in fetch_reddit: {e}")
                    results['reddit'] = []

            # Multithreading during fetching using duckduckgo and praw (reddit) for time efficiency.
            # Writing to shared being a potential race condition is not importnat as either case works fine (Both the clean and original queries work if either returns a different cleaned query)
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

            print("Num ddg: ",len(ddg_posts), "Num reddit: ",len(reddit_posts)) # For analysis purposes, should be > 0, > 0

            for post in ddg_posts + reddit_posts: # + pushshift_posts: # pushift API use was deprecated as it was too unreliable (due to problems of pushshift API)
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
            
            all_posts = list(all_posts_dict.values())   # A list of all unique posts

            # Embed all posts into the chroma collection
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
                    "game": db_metadatas[i].get("game")  # Include game name
                }
                all_posts.append(post)
            
            database_message = "Found in the database (newly added)"
            
    # If a problem occurs while querying the database
    # Duplicate code and logic with the else statement above, could be functionized to be more efficient
    except Exception as e:
        print(f"Error querying database: {e}")
        database_message = "Database query failed, fetching new posts"
        
        results = {}
        shared = {}

        def fetch_ddg():
            subreddit = "tearsofthekingdom"
            try:
                posts, clean_query = reddit_query_via_ddg(q, max_posts=200, metric=metric, subreddit=subreddit)
                results['ddg'] = posts
                shared['clean_query'] = clean_query
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
        
        db_documents, db_distances, db_metadatas = query_db(clean_query, n_results=10, game_filter=detected_game)
        print("Database query results:", len(db_documents), "documents found")
        
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
    global cached_posts, cached_query
    cached_posts = all_posts
    cached_query = q

    print(f"\nProcessing with message: {database_message}")


    # Add post time to each post (if not already present)
    for post in all_posts:
        if "created_utc" not in post:
            post["created_utc"] = None  # Default if missing
        # If post is from PRAW, try to get created_utc
        if hasattr(post, "created_utc"):
            post["created_utc"] = post.created_utc

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

    
    # Use AI to rank the top x scored posts based on the query (skip if posts are retrieved from the db)
    # DEPRACATED, else statement never runs as fetched posts are always embedded and retrieved from the db.
    # AI ranking does not affect anything but it exists in case the project scope changes in the future.
    if database_message in ["Found in the database", "Found in the database (newly added)"]:
        ai_ranked_posts = ranked_posts[:10]  # Just use top 10 database results
        print("Skipping AI ranking for database results")
    else:
        ai_ranked_posts = ai_rank_posts(ranked_posts[:20], original_query)

        # Print scores for debugging
        print("\nAI RANKED POSTS WITH SCORES:\n")
        for post in ai_ranked_posts:
            subreddit = post.get('subreddit', 'unknown')
            print(f"Subreddit: {subreddit}")
            print(f"{post['title']} [Score: {post['_score']:.2f}]")
            

    final_posts = ai_ranked_posts

    summarized_results = []
    for i, post in enumerate(final_posts):
        post_time = post.get("created_utc")
        if post_time:
            date_str = datetime.utcfromtimestamp(post_time).strftime('%Y-%m-%d')
        else:
            date_str = "Unknown date"

        # Format post content for every post
        raw_content = format_post_content(post.get("content", ""))

        # Formats the output into an HTML processable string for better display.
        post_content = enhance_post_content_for_html(raw_content) if raw_content else ""
        
        # Format comments for display
        comments = post.get("comments", [])
        formatted_comments = ""
        if comments:
            # Wraps every non-empty comment into a div and joins them into an HTML stirng separated by <br>
            formatted_comments = "<br>".join([f"<div style='background:#f9f9f9;padding:10px;margin:5px 0;border-left:3px solid #185a9d;border-radius:4px;'>{comment}</div>" for comment in comments if comment.strip()])
        
        subreddit = post.get('subreddit', 'unknown')
        
        # Output format for data for other endpoints to check.
        summarized_results.append({
            "title": f"{post['title']} [Date: {date_str}]", 
            "url": post["url"],
            "summary": "",  # No summary if ranking by title only
            "content": post_content,  # Formatted post content for all posts
            "comments": formatted_comments,  # Formatted comments for display
            "created_utc": post_time,
            "subreddit": subreddit
        })


    return {
        "query": q,
        "results": summarized_results,
        "has_summary": True,  # Indicates summary is available via separate endpoint
        "database_status": database_message  # Send database status to frontend
    }



# New endpoint for AI summary generation.
# Provides Generate AI summary for the cached posts from the previous query
@app.get("/summary")
def get_summary(q: str = Query(..., max_length=512, description="Original query for summary generation")):
    """"""
    try:
        # Basic security validation and sanitization for max query length
        if not validate_query_length(q, 512):
            return {"error": "Query too long"}
        
        q = sanitize_input(q)
        if not q:
            return {"error": "Invalid query"}
        
        # Access cached posts (Currently the top 10 retrieved by the db)
        global cached_posts, cached_query
        
        if not cached_posts or cached_query != q:
            return {"error": "No cached posts found for this query. Please run /query first."}
        
        print(f"Generating summary for {len(cached_posts)} posts...")
        ai_summary = post_summary_generation(cached_posts, q)   # Generate a summary accross all displayed posts and comments.
        print("Summary generated successfully")
        
        return {
            "query": q,
            "ai_summary": ai_summary,
            "post_count": len(cached_posts)
        }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": f"Failed to generate summary: {str(e)}"}

# Quick endpoint to check if posts need to be fetched (To display the "wait a moment" message).
@app.get("/check-fetch-needed")
def check_fetch_needed(q: str = Query(..., max_length=512, description="Query to check in database")):
    # Duplicate logic with /query but necessary
    
    try:
        # Basic security validation and sanitization for query length
        if not validate_query_length(q, 512):
            return {"fetch_needed": False, "message": "Query too long"}
        
        original_query = q
        q = sanitize_input(q)
        if not q:
            log_suspicious_query(original_query, "Empty query after sanitization")
            return {"fetch_needed": False, "message": "Invalid query"}
        
        # Check if query is related to BOTW or TOTK only
        query_lower = q.lower()
        query_cleaned = query_lower.translate(str.maketrans('', '', string.punctuation))
        allowed_terms = ['botw', 'breath of the wild', 'totk', 'tears of the kingdom']
        is_related_query = any(term in query_cleaned for term in allowed_terms)
        
        if not is_related_query:
            return {"fetch_needed": False, "message": "Unrelated query"}
        
        # Detect which game the query is about and check database
        detected_game = detect_game_from_query(q)
        db_documents, db_distances, db_metadatas = query_db(q, n_results=10, game_filter=detected_game)
        good_matches = [doc for i, doc in enumerate(db_documents) if db_distances[i] < 0.7]
        
        # If we don't have enough good matches, fetching will be needed
        if not good_matches or len(good_matches) < 7:
            return {"fetch_needed": True, "message": "Will need to fetch new posts"}
        else:
            return {"fetch_needed": False, "message": "Posts available in database"}
            
    except Exception as e:
        return {"fetch_needed": True, "message": "Database check failed, will fetch posts"}

