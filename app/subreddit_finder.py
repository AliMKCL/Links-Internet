from ddgs import DDGS
import re
from collections import Counter
from app.config import OPENAI_KEY
from openai import OpenAI
import ast
import json
import os

client = OpenAI(api_key=OPENAI_KEY)

# Load gaming abbreviations from a JSON file
# The JSON file contains abbreviations for 300+ games, which is now unnecessary but still kept for potential future expansion.
def load_gaming_abbreviations():
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'gaming_abbreviations.json')
    with open(file_path, 'r') as f:
        abbreviations = json.load(f)
    return abbreviations

# Provides relevant subreddit names based on a query using OpenAI API
# Created before narrowing scope to 2 games
# Could be replaced with hard coded subreddits as now only 2 games with 2 subreddits each are used.
def get_relevant_subreddits_from_ai(query: str, max_subreddits: int = 3, subreddit:str = None) -> list[str]:

    abbreviations = load_gaming_abbreviations()
    query_words = query.split(" ")
    abbreviation_word = ""
    for word in query_words:
        if word in abbreviations:
            #query = query.replace(word, abbreviations[word])
            abbreviation_word = word
    
    print(f"Abbreviation word: {abbreviation_word}")  # Debugging line to check abbreviation word
    
    # If a subreddit is not provided, use AI to suggest relevant subreddits based on the query
    if not subreddit:
        prompt = f"User query: {query}\n\n"
        prompt += f"Suggest up to {max_subreddits} relevant subreddit names (without 'r/' prefix). Try to return as much as possible, but do not return anymore if the subreddits are not closely related to the query.\n"
        prompt += "Do not suggest vaguely related subreddits that are not specifically about the queried game."
        prompt += f"The term '{abbreviation_word}' is a fully capitalized abbreviation of a phrase that hints at the target subreddits. If the abbreviation or its full form matches a subreddit name, include both if relevant.\n"
        prompt += "Use abbreviations or full forms if they match subreddit names. Prefer abbreviations when they are used as subreddit names.\n"
        prompt += "Return only a Python tuple: (list of subreddit names, remaining query after removing matched parts).\n"

    # If a specific subreddit is provided, use it directly  
    else:
        prompt = f"User query: {query}\n\n"
        prompt += f"The user has specified the subreddit '{subreddit}'.\n"
        prompt += f"Return only a Python tuple: (list containing the specified subreddit name '{subreddit}', remaining query after removing the part from the query that makes you infer the subreddit).\n"

    
    # After this if-else, the user query is also cleaned where the subreddit pointing part is removed.


    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )


    raw_response = response.choices[0].message.content.strip()

    # Return the relevant subreddits, fallback (to "zelda") if parsing fails
    try:
        subreddits, remaining_query = ast.literal_eval(raw_response) # Converts the response string to a tuple.
        if isinstance(subreddits, str):
            subreddits = [subreddits]
        elif not isinstance(subreddits, list):
            subreddits = ["zelda"]
    except Exception:
        subreddits, remaining_query = ["zelda"], query  # fallback
    return subreddits[:max_subreddits], remaining_query