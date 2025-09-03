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
import threading
from app.utilities import enhance_post_content_for_html, question_statement_classification

import sys
import numpy

print('Python executable:', sys.executable)
print('Numpy version:', numpy.__version__)
# Initialize FastAPI app
app = FastAPI(title="Reddit Gaming Advisor")
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")
templates = Jinja2Templates(directory="app/templates")


# Root endpoint to serve the HTML template
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query")
def query(q: str = Query(..., description="Gaming-related question"), metric: str = Query("all", description="Time filter for Reddit search")):
    
    results = {}
    shared = {} # Dictionaries are mutable --> Shared between threads

    def fetch_ddg():
        try:
            posts, clean_query = reddit_query_via_ddg(q, 50, metric)
            results['ddg'] = posts
            shared['clean_query'] = clean_query # Cleaned query is saved here to the common dictionary
        except Exception as e:
            print(f"Error in fetch_ddg: {e}")
            results['ddg'] = []
    def fetch_reddit():
        try:
            posts, clean_query = search_reddit(q, 100, metric)
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

    initial_query = q
    clean_query = shared.get('clean_query', q)  # Use cleaned query if available
    q = clean_query # For easy changes

    # Causing numpy error???
    print(question_statement_classification(q))  # Print the classification result for debugging
    
    print("Cleaned query main: ", clean_query)

    ddg_posts = results['ddg']  # is a dict
    reddit_posts = results['reddit'] # is a list

    # Combine and deduplicate posts by URL 
    all_posts_dict = {}

    print(type(ddg_posts), type(reddit_posts)) # Should be list, list
    print("Num ddg: ",len(ddg_posts), "Num reddit: ",len(reddit_posts)) # Should be > 0, > 0

    import re
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
    

    # Add post time to each post (if not already present)
    for post in all_posts:
        if "created_utc" not in post:
            post["created_utc"] = None  # Default if missing
        # If post is from PRAW, try to get created_utc
        if hasattr(post, "created_utc"):
            post["created_utc"] = post.created_utc


    # Compute and attach scores to each post for consistent display and sorting
    for post in all_posts:
        post["_score"] = score_post(post, q)

    # Sort by score, then by recency
    ranked_posts = sorted(
        all_posts,
        key=lambda post: (post["_score"], post.get("created_utc", 0)),
        reverse=True
    )


    # Print scores for debugging
    print("\nRANKED POSTS WITH SCORES:\n")
    for post in ranked_posts:
        subreddit = post.get('subreddit', 'unknown')
        print(f"Subreddit: {subreddit}")
        print(f"{post['title']} [Score: {post['_score']:.2f}]")

    # Use AI to rank the top x scored posts based on the query
    ai_ranked_posts = ai_rank_posts(ranked_posts[:20], initial_query)

    # Print scores for debugging
    print("\nAI RANKED POSTS WITH SCORES:")
    for post in ai_ranked_posts:
        subreddit = post.get('subreddit', 'unknown')
        print(f"Subreddit: {subreddit}")
        print(f"{post['title']} [Score: {post['_score']:.2f}]")
    

    # Get the order of subreddits as they appear in the ranked posts
    subreddit_order = []
    for post in ai_ranked_posts:
        sub = post.get('subreddit', 'unknown')
        if sub not in subreddit_order:
            subreddit_order.append(sub)

    # Sort posts so that all posts from the 1st subreddit come first, then 2nd, etc., preserving their relative order
    def subreddit_sort_key(post):
        sub = post.get('subreddit', 'unknown')
        try:
            return subreddit_order.index(sub)   # The index of the subreddit in the order list
        except ValueError:
            return len(subreddit_order)

    ai_ranked_posts_sorted = sorted(ai_ranked_posts, key=subreddit_sort_key)

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
        subreddit = post.get('subreddit', 'unknown')
        summarized_results.append({
            "title": f"{post['title']} [Score: {post['_score']:.2f}] [Date: {date_str}]",
            "url": post["url"],
            "summary": "",  # No summary if ranking by title only
            "content": post_content,  # Formatted post content for all posts
            "created_utc": post_time,
            "is_top_post": i == 0,  # Flag to identify top post
            "subreddit": subreddit
        })

    return {
        "query": q,
        "results": summarized_results
    }