# 3D Zelda Games Advisor

**🎥 Demo Video**: https://youtu.be/gH4BUbcch-8

A FastAPI-based intelligent advisor for Breath of the Wild (BOTW) and Tears of the Kingdom (TOTK) that uses RAG (Retrieval-Augmented Generation) with vector embeddings to provide contextual answers from Reddit discussions.

## Features

- **Smart Query Processing**: Automatically detects which Zelda game you're asking about
- **Vector Search**: Uses ChromaDB with OpenAI embeddings for semantic similarity matching
- **Multi-source Data**: Fetches from Reddit API (PRAW) and DuckDuckGo search
- **AI Summarization**: Generates comprehensive summaries of relevant discussions

## Tech Stack

- **Backend**: FastAPI, Python 3.12+
- **Vector Database**: ChromaDB
- **Embeddings**: OpenAI text-embedding-ada-002
- **Data Sources**: Reddit (through Reddit API (PRAW), DuckDuckGo Search)
- **Frontend**: HTML/CSS with Jinja2 templates

