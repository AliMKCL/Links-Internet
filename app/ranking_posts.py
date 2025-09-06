from datetime import datetime
from openai import OpenAI
from app.config import OPENAI_KEY
import re

client = OpenAI(api_key=OPENAI_KEY)

# Used for deciding which post to include if duplicate posts are received. (Not necessary anymore but exists)
def score_post(post: dict, query: str) -> float:
    score = 0
    title = post.get("title", "").lower()
    query = query.lower()
    title_words = re.findall(r'\w+', title)
    query_words = re.findall(r'\w+', query)

    # Normalize title and query for full phrase and word match (lowercase and singular)
    def normalize_word(word):
        w = word.lower()
        if w.endswith('s') and len(w) > 3:
            w = w[:-1]
        return w

    title_words_norm = [normalize_word(w) for w in re.findall(r'\w+', title)]
    query_words_norm = [normalize_word(w) for w in re.findall(r'\w+', query)]
    norm_title = ' '.join(title_words_norm)
    norm_query = ' '.join(query_words_norm)

    
    # Full phrase match: normalized query phrase is substring of normalized title
    if norm_query in norm_title:
        score += 2

    # Partial word matches
    partial_match_count = 0
    for qw in query_words_norm:
        for tw in title_words_norm:
            if qw == tw:
                partial_match_count += 1
                break
    if partial_match_count > 0 and score < 2:
        score += 1

    # Penalty for extra words in the title (use normalized word count only)
    """
    extra_words = max(0, len(title_words_norm) - partial_match_count)
    score -= extra_words * 0.05  # Subtract 0.05 for each extra word
    """

    # Small bonus for upvotes and comments
    score += post.get("score", 0) / 5000
    score += len(post.get("comments", [])) * 0.001
    return score


# AI based ranking of posts before displaying to user.
# Currently deprecated but kept in the codebase just in case the project scope changes in the future.
def ai_rank_posts(posts, query):
    # Prepare the prompt for ranking
    prompt = f"User query: {query}\n\n"
    for i, post in enumerate(posts):
        date_str = "Unknown date"
        if post.get("created_utc"):
            date_str = datetime.utcfromtimestamp(post["created_utc"]).strftime('%Y-%m-%d')

        post_content = post.get("content", "")
        if post_content:
            formatted_content = format_post_content(post_content)
            post_content = f"Post Content:\n{formatted_content}\n"
            
             # Alert the AI if the post contains tables
            if "POST CONTAINS TABLE DATA" in formatted_content:
                post_content = "THIS POST CONTAINS FORMATTED TABLE DATA - PAY SPECIAL ATTENTION\n" + post_content

        prompt += f"Post {i+1}:\nTitle: {post['title']}\nDate: {date_str}\n{post_content}\n"
        prompt += (
            "You are given a list of posts, each with a title, date, and post content. Your task is to rank all the posts from most to least relevant to the given query."
            "Follow these rules carefully:"
            "1) Relevance is based on how closely both the title AND post content match the meaning of the query, not just exact words."
            "Consider similar terms (e.g., 'updates' ≈ 'changes')."
            "Look for specific details in the post content that address the query."
            "Posts with tables, lists, or detailed information directly relevant to the query should be ranked higher."
            "2) Content importance:"
            "Posts that contain comprehensive information related to the query (like patch notes, detailed guides, or tables of data) are more valuable."
            "Look for specific information like version numbers, stats, or step-by-step instructions relevant to the query."
            "If a post contains table data (marked with 'POST CONTAINS TABLE DATA'), give it extra consideration as tables often contain the most relevant structured information for queries about balance changes, stats, or comparison data."
            "3) Recency matters:"
            "If two posts are equally relevant, rank the newer post higher."
            "If a post is about a specific version (e.g., patch number), prefer the most recent version."
            "4) Scoring:"
            "Posts that are clearly about the query with detailed content should be scored higher than those with minimal information."
            "5) Output format:"
            "Return ONLY a comma-separated list of post indices (1-based) in the order you rank them."
            "For example, if you rank post 3 highest, then post 1, then post 2, return: '3, 1, 2'."
            "6) If you see a duplicate post (same title and content), only rank it once. Besides that, do NOT skip any posts, all posts must appear in the output list."
        )

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response. Example: "1, 3, 2, 4, ..."
    raw_response = response.choices[0].message.content

    print("\nAI raw response:", raw_response)
    ranked_indices = [int(s) - 1 for s in re.findall(r'\b\d+\b', raw_response)]
    ranked_posts = [posts[i] for i in ranked_indices if i < len(posts)]
    return ranked_posts

def format_post_content(content):
    """Format post content, preserving table structure"""
    if not content:
        return ""
    
    # Detect if content has tables. Tables in reddit are formatted with "|", "---", or "+-"
    has_table = '|' in content or '\n---' in content or '\n+-' in content
    
    if has_table:
        # Preserve exact formatting for table content
        return "POST CONTAINS TABLE DATA:\n" + content
    else:
        # For non-table content, you can truncate or summarize
        if len(content) > 1000:
            return content[:1000] + "..."
        return content

