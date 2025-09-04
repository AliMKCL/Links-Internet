# praw: API wrapper for reddit
# psaw: A wrapper for pushlift API (Unofficial/External reddit search, better but unstable)

import praw
from app.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from app.subreddit_finder import get_relevant_subreddits_from_ai
import re


# Initialize Reddit API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def search_reddit(query: str, limit: int = 50, metric: str = "all", subreddit: str = None): 
    results = []
    if not subreddit:
        subreddits, cleaned_query = get_relevant_subreddits_from_ai(query, max_subreddits=3)
    else:
        subreddits, cleaned_query = get_relevant_subreddits_from_ai(query, max_subreddits=3, subreddit=subreddit)


    print("subreddits: ",subreddits)
    print("Cleaned query: ", cleaned_query)

    if not isinstance(subreddits, list):
        subreddits = [str(subreddits)]

    # First, limit to maximum of 3 subreddits to process
    subreddits = subreddits[:3]

    # Map metric to Reddit time_filter
    if metric == "all":
        time_filter = "all"
    elif metric == "year":
        time_filter = "year"
    elif metric == "month":
        time_filter = "month"
    else:
        time_filter = "all"  # fallback

    
    # Determine fetch limits based on number of subreddits
    if len(subreddits) == 1:
        # If there's 1 subreddit, fetch 100 posts
        limits = [100]
    elif len(subreddits) == 2:
        # If there are 2 subreddits, fetch 100 from 1st, 100 from 2nd
        limits = [100, 100]
    else:
        # If there are 3 subreddits, fetch 100 from 1st, 100 from 2nd, 100 from 3rd
        limits = [100, 100, 100]

    #print(f"[PRAW] Fetching from {len(subreddits)} subreddits: {subreddits}")
    #print(f"[PRAW] Using fetch limits: {limits}")

    # Loop over each subreddit and fetch a different number of posts per subreddit
    for idx, subreddit in enumerate(subreddits):
        fetch_limit = limits[idx]
        #print(f"[PRAW] Subreddit {idx+1}/{len(subreddits)}: r/{subreddit} - fetching up to {fetch_limit} posts")
        try:
            for submission in reddit.subreddit(subreddit).search(query, sort="relevance", time_filter=time_filter, limit=fetch_limit):
                # Skip video posts
                
                if submission.is_video:
                    continue
                
                submission.comments.replace_more(limit=0)
                top_comments = [c.body for c in submission.comments[:3]]
                results.append({
                    "title": submission.title,
                    "url": f"https://www.reddit.com{submission.permalink}",
                    "score": submission.score,
                    "created_utc": getattr(submission, "created_utc", None),
                    "content": submission.selftext,  # Post content
                    "comments": top_comments
                })
        except Exception as e:
            print(f"Error fetching from subreddit {subreddit}: {e}")

    return results, query  # Return cleaned query for further processing
