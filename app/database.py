import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import openai


from app.config import OPENAI_KEY_DB

chroma_client = chromadb.PersistentClient("app/data/posts_db")  # Use new database name

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_KEY_DB,
                model_name="text-embedding-3-small"
            )

collection = chroma_client.get_or_create_collection(name="posts", embedding_function=openai_ef)

# Delete existing collection to start fresh
def delete_collection():
        
        # Note: This will remove all existing data in the collection
        # Use with caution in production environments
    try:
        chroma_client.delete_collection(name="posts")
        print("Deleted existing collection to start fresh with enhanced embedding")
    except Exception as e:
        print("Could not delete the collection:", e)



def embed_text(posts: list[dict]) -> None:
    for post in posts:
        try:
            # Check if post already exists
            existing = collection.query(
                query_texts=["dummy"],
                n_results=1,
                where={"url": post["url"]}
            )
            
            if len(existing['ids'][0]) == 0:  # Post doesn't exist
                
                # Get the original title and subreddit
                original_title = post["title"]
                subreddit = post.get("subreddit", "unknown").lower()
                
                # Define game mappings: subreddits -> (abbreviation, full_names_to_check)
                game_mappings = {
                    # Breath of the Wild
                    'breath_of_the_wild': ('BOTW', ['botw', 'breath of the wild']),
                    'botw': ('BOTW', ['BOTW', 'breath of the wild']),
                    'breathofthewild': ('BOTW', ['botw', 'breath of the wild']),
                    
                    # Tears of the Kingdom
                    'tears_of_the_kingdom': ('TOTK', ['totk', 'tears of the kingdom']),
                    'totk': ('TOTK', ['TOTK', 'tears of the kingdom']),
                    'tearsofthekingdom': ('TOTK', ['totk', 'tears of the kingdom']),
                }
                
                # Determine game metadata based on subreddit
                game_metadata = None
                if subreddit in game_mappings:
                    game_metadata = game_mappings[subreddit][0]  # Use the abbreviation as game metadata
                
                # Add abbreviation of game to title if it's from a game-related subreddit and doesn't already contain it
                title_for_embedding = original_title
                if subreddit in game_mappings:
                    abbreviation_full = game_mappings[subreddit][1][1]
                    abbreviation, terms_to_check = game_mappings[subreddit]
                    # Check if any of the terms are already in the title (case insensitive)
                    if not any(term in original_title.lower() for term in terms_to_check):
                        title_for_embedding = f"{original_title} {abbreviation}"
                        print(f"Enhanced title: '{original_title}' -> '{title_for_embedding}'")

                content = post.get("content", "")
                if content and len(content) > 1000:
                    content = content[:1000]  # Truncate to first 1000 chars
                post["content"] = content
                
                # Convert comments list to string for ChromaDB compatibility
                comments = post.get("comments", [])
                comments_str = " | ".join(comments) if comments else ""  # Join comments with separator
                
                collection.add(
                    documents=[title_for_embedding],  # Use enhanced title for embedding
                    ids=[post["url"]],  # Use URL as unique ID
                    embeddings=[openai_ef([title_for_embedding])[0]],
                    metadatas=[{
                        "url": post["url"],                             # url of post
                        "subreddit": post.get("subreddit", "unknown"),  # subreddit the post comes from
                        "content": post.get("content", ""),             # Content of the post
                        "score": post.get("_score", 0),                 # Score of the post (the distance)
                        "original_title": original_title,               # Title of the post
                        "comments": comments_str,                       # Store comments as string
                        "created_utc": post.get("created_utc"),         # Store post creation timestamo
                        "game": game_metadata,                          # The game name related to the post
                    }]
                )
                    
        except Exception as e:
            print(f"Error embedding post {post.get('title', 'unknown')}: {e}")

def query_db(query: str, n_results: int = 10, game_filter: str = None):
    # Normalize query so that mentions of full game names are converted / augmented with
    # the same abbreviations used when embedding titles (ensures better vector matches).
    query_lower = query.lower()
    game_aliases = {
        'botw': ['botw', 'breath of the wild'],
        'totk': ['totk', 'tears of the kingdom']
    }

    # Build a query string for embedding that includes the abbreviation if a game term is present
    query_for_embedding = query
    for abbrev, aliases in game_aliases.items():
        for alias in aliases:
            if alias in query_lower:
                # append uppercase abbreviation if not already present
                if abbrev.upper() not in query and abbrev not in query_lower:
                    query_for_embedding = f"{query_for_embedding} {abbrev.upper()}"
                    print(f"Augmented query for embedding with game abbrev: {abbrev.upper()}")
                break

    query_embeddings = openai_ef(query_for_embedding)

    # Build where clause for game filtering
    where_clause = None
    if game_filter:
        where_clause = {"game": game_filter}
        print(f"Filtering results for game: {game_filter}")

    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where_clause
    )

    return results["documents"][0], results["distances"][0], results["metadatas"][0]
