# Test script for debugging the ranking function
from app.ranking_posts import ai_rank_posts

# Sample test data
test_posts = [
    {
        "title": "Complete Guide to Elden Ring Boss Strategies",
        "created_utc": 1661433600,  # 2022-08-25
        "content": "This guide provides detailed strategies for defeating all bosses in Elden Ring. [Detailed content here]",
        "score": 500,
        "comments": ["Great guide!", "This helped me a lot"]
    },
    {
        "title": "Has anyone figured out how to beat the final boss?",
        "created_utc": 1661520000,  # 2022-08-26
        "content": "I've been stuck on the final boss for days. Any tips?",
        "score": 100,
        "comments": ["Try using fire attacks", "The weakness is its left leg", "You need to level up more"]
    },
    {
        "title": "Official Patch Notes - Version 1.05",
        "created_utc": 1661606400,  # 2022-08-27
        "content": "POST CONTAINS TABLE DATA:\n| Weapon | Old Damage | New Damage |\n| ------ | ---------- | ---------- |\n| Sword of Night | 120 | 110 |\n| Flame Axe | 95 | 105 |",
        "score": 1000,
        "comments": ["Good balance changes", "Why nerf my favorite weapon?"]
    }
]

test_query = "Elden Ring boss strategies"

# Run the ranking function - set your breakpoint on line 153 in ranking_posts.py
# before running this script with the debugger
ranked_results = ai_rank_posts(test_posts, test_query)

# Print results after debugging
print("\nRanked Results:")
for i, post in enumerate(ranked_results):
    print(f"{i+1}. Title: {post['title']}")
    print(f"   Focus: {post.get('content_focus', 'Unknown')}")
    print("")
