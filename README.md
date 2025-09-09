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

# Deployment

This project is available as a pre-built Docker image. No repository cloning required.

## Prerequisites

You'll need to obtain your own API keys:

**Required:**
- OpenAI API Key (for embeddings and summaries)
  - Get one at: https://platform.openai.com/api-keys
  - Free tier includes $5 credit for new accounts

- Reddit API credentials (for new post fetching)
  - Create an app at: https://www.reddit.com/prefs/apps
  - Note: App works with existing database if you skip this

**Steps:**
### Step 1: Pull the Docker image
docker pull alimkcl/zelda-advisor:latest

### Step 2: Copy environment template from container to your directory
docker run --rm alimkcl/zelda-advisor:latest cat /app/.env.example > .env

### Step 3: Edit local.env with your API key
nano .env 

### Step 4: Run container
docker run --rm --env-file .env -p 8000:8000 alimkcl/zelda-advisor:latest

### Step 5: Access application
Open http://localhost:8000 in your browser


