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

This project is designed to run via Docker for the best experience. Follow these steps after cloning the repository:

## Prerequisites

You'll need to obtain your own API keys:

**Required:**
- OpenAI API Key (for embeddings and summaries)
  - Get one at: https://platform.openai.com/api-keys
  - Free tier includes $5 credit for new accounts

- Reddit API credentials (for new post fetching)
  - Create an app at: https://www.reddit.com/prefs/apps
  - Note: App works with existing database if you skip this

Once you obtain these, replace them in the .env_example file, then rename the file to .env.

**Steps:**
### Step 1: Copy template to actual .env file
cp .env.example .env

### Step 2: Edit .env with real values
nano .env  # or code .env, vim .env, etc.

### Step 3: Build the container
docker build -t zelda-advisor .

### Step 4: Run container
docker run --env-file .env -p 8000:8000 zelda-advisor

### Step 5: Access application
Access the application: Open http://localhost:8000 in your browser
