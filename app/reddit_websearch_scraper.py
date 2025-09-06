import re
from ddgs import DDGS
import praw
from typing import List, Dict
from app.subreddit_finder import get_relevant_subreddits_from_ai
from app.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
import datetime

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
# Fetch reddit posts from reddit by their IDs
def fetch_posts_by_ids(post_ids: List[str], max_comments: int = 50) -> List[Dict]:
    posts = []
    for pid in post_ids:
        submission = None
        comments = []
        try:
            submission = reddit.submission(id=pid)

            # Skip video posts
            if submission.is_video:
                continue
                
            submission.comments.replace_more(limit=0)
            comments = [
                c.body for c in sorted(submission.comments, key=lambda x: x.score, reverse=True)
                if len(c.body) > 30 and not c.stickied
            ][:max_comments]
        except Exception as e:
            submission = None
            comments = []
        if submission:
            posts.append({
                "title": submission.title,
                "url": f"https://www.reddit.com{submission.permalink}",
                "score": submission.score,
                "created_utc": getattr(submission, "created_utc", None),
                "content": submission.selftext,  # Post content
                "comments": comments
            })
        else:
            posts.append({
                "title": "Unknown",
                "url": "",
                "score": 0,
                "created_utc": None,
                "comments": []
            })
    return posts

# Search Reddit posts via DuckDuckGo, with optional time filter bias (metric: 'all', 'year', 'month').
def reddit_query_via_ddg(query: str, max_posts: int = 50, max_comments: int = 5, metric: str = "all", subreddit: str = None) -> List[Dict]:
    post_ids, cleaned_query = get_reddit_post_ids_from_ai(query, max_results=max_posts, metric=metric, subreddit=subreddit)
    posts = fetch_posts_by_ids(post_ids, max_comments=max_comments)
    return posts, cleaned_query
 
# Uses AI to determine subreddits, then uses DuckDuckGo to find relevant Reddit post IDs
def get_reddit_post_ids_from_ai(query: str, max_results: int = 50, metric: str = "all", subreddit: str = None) -> List[str]:
    
    if not subreddit:
        subreddits, cleaned_query = get_relevant_subreddits_from_ai(query, max_subreddits=3)
    else:
        subreddits, cleaned_query = get_relevant_subreddits_from_ai(query, max_subreddits=3, subreddit=subreddit)
    
    post_ids = []
    now = datetime.datetime.utcnow()
    time_keywords = ""
    if metric == "month":
        curr_month = now.strftime('%B')
        curr_year = now.year
        prev_month_dt = now.replace(day=1) - datetime.timedelta(days=1)
        prev_month = prev_month_dt.strftime('%B')
        time_keywords = f"{curr_year} {curr_month} OR {curr_year} {prev_month} OR last month OR recent"
    elif metric == "year":
        curr_year = now.year
        prev_year = curr_year - 1
        time_keywords = f"{curr_year} OR {prev_year} OR this year OR last year OR recent"
    # For 'all', no extra keywords
    if not isinstance(subreddits, list):
        subreddits = [str(subreddits)]
    
    # First, limit to maximum of 3 subreddits to process
    subreddits = subreddits[:3]
    
    # Determine fetch limits based on number of subreddits
    if len(subreddits) == 1:
        # If there's 1 subreddit, fetch 100 posts
        limits = [100]
    elif len(subreddits) == 2:
        # If there are 2 subreddits, fetch 50 from 1st, 30 from 2nd
        limits = [50, 30]
    else:
        # If there are 3 subreddits, fetch 100 from 1st, 50 from 2nd, 30 from 3rd
        limits = [100, 50, 30]
    
    # For each post id clean the query to pass into DDG
    for idx, subreddit in enumerate(subreddits):
        fetch_limit = limits[idx]
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]   # eliminate the leading 'r/' if present
        ddg_query = f"{cleaned_query} site:reddit.com/r/{subreddit}"
        if time_keywords:
            ddg_query += f" {time_keywords}"
        
        # Search DuckDuckGo for Reddit posts in the specified subreddit
        with DDGS() as ddgs:
            results = ddgs.text(ddg_query, max_results=fetch_limit)
            for r in results:
                # More flexible regex that handles various Reddit URL formats
                match = re.search(r"reddit\.com/r/[^/]+/comments/([a-zA-Z0-9_-]{5,})", r["href"])
                if match:
                    post_ids.append(match.group(1))
                else:
                    # Try alternative patterns for edge cases
                    alt_match = re.search(r"reddit\.com/(?:r/[^/]+/)?comments/([a-zA-Z0-9_-]{5,})", r["href"])
                    if alt_match:
                        post_ids.append(alt_match.group(1))
    return post_ids, cleaned_query