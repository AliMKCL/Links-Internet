# Pushshift API Reddit search (via psaw)
# This module provides functions to fetch Reddit posts using the Pushshift API for broader and more flexible search.

# Not used throughout the project as the API is too unreliable, but kept for reference.

from psaw import PushshiftAPI
from datetime import datetime
from typing import List, Dict, Optional
import praw
from app.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

# Initialize Reddit and Pushshift API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
api = PushshiftAPI(reddit)

# Scrape reddit via the pushshift API
def search_pushshift(query: str, 
                     subreddits: Optional[List[str]] = None, 
                     limit: int = 50, 
                     metric: str = "all",
                     after: Optional[int] = None, 
                     before: Optional[int] = None) -> List[Dict]:
                    
    subreddit_str = None
    if subreddits:
        subreddit_str = ','.join(subreddits)
    results = []

    if metric == "year":
        after = int(datetime.now().timestamp()) - 31536000  # 1 year ago
    elif metric == "month":
        after = int(datetime.now().timestamp()) - 2592000  # 1 month ago
    
    gen = api.search_submissions(
        q=query,
        subreddit=subreddit_str,
        limit=limit,
        after=after,
        before=before,
        sort='desc',
        sort_type='created_utc'
    )
    for submission in gen:
        submission.comments.replace_more(limit=0)
        top_comments = [c.body for c in submission.comments[:3]]
        results.append({
            "title": submission.title,
            "url": f"https://www.reddit.com{submission.permalink}",
            "score": submission.score,
            "created_utc": getattr(submission, "created_utc", None),
            "comments": top_comments
        })
    return results

# Example usage:
# posts = search_pushshift("1.61.38 balance changes", subreddits=["gaming"], limit=20, after=int(datetime(2024,1,1).timestamp()))
