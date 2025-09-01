import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import openai


from app.config import OPENAI_KEY_DB

chroma_client = chromadb.PersistentClient("app/data/posts_db")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_KEY_DB,
                model_name="text-embedding-3-small"
            )

"""
#TESTING, REMOVE LATER
try:
    chroma_client.delete_collection(name="posts")
except:
    pass
"""

collection = chroma_client.get_or_create_collection(name="posts", embedding_function=openai_ef)

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

                content = post.get("content", "")
                if content and len(content) > 1000:
                    content = content[:1000]  # Truncate to first 1000 chars
                post["content"] = content
                collection.add(
                    documents=[post["title"]],
                    ids=[post["url"]],  # Use URL as unique ID
                    embeddings=[openai_ef([post["title"]])[0]],
                    metadatas=[{
                        "url": post["url"],
                        "subreddit": post.get("subreddit", "unknown"),
                        "content": post.get("content", ""),
                        "score": post.get("_score", 0)
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

    return results["documents"][0], results["distances"][0]

