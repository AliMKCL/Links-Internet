import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import openai


from app.config import OPENAI_KEY_DB

chroma_client = chromadb.PersistentClient("app/data/posts_db_v2")  # Use new database name

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_KEY_DB,
                model_name="text-embedding-3-small"
            )

collection = chroma_client.get_or_create_collection(name="posts", embedding_function=openai_ef)

def delete_collection():
    # TESTING, REMOVE LATER - Delete collection to start fresh with new embedding logic
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
                
                # Add "BOTW" to title if it's from BOTW-related subreddits and doesn't already contain it
                title_for_embedding = original_title
                if (subreddit in ['breath_of_the_wild', 'botw', 'breathofthewild'] and 
                    not any(term in original_title.lower() for term in ['botw', 'breath of the wild'])):
                    title_for_embedding = f"{original_title} BOTW"
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
                        "url": post["url"],
                        "subreddit": post.get("subreddit", "unknown"),
                        "content": post.get("content", ""),
                        "score": post.get("_score", 0),
                        "original_title": original_title,  # Store original title for display
                        "comments": comments_str,  # Store comments as string
                    }]
                )
                    
        except Exception as e:
            print(f"Error embedding post {post.get('title', 'unknown')}: {e}")

def query_db(query:str, n_results:int=10):

    query_embeddings = openai_ef(query)

    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results
    )

    return results["documents"][0], results["distances"][0], results["metadatas"][0]

