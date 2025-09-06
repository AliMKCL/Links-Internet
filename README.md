# 3D Zelda Games Advisor

**🎥 Demo Video**: https://youtu.be/gH4BUbcch-8

A FastAPI-based intelligent advisor for Breath of the Wild (BOTW) and Tears of the Kingdom (TOTK) that uses RAG (Retrieval-Augmented Generation) with vector embeddings to provide contextual answers from Reddit discussions.

## Features

- **Smart Query Processing**: Automatically detects which Zelda game you're asking about
- **Vector Search**: Uses ChromaDB with OpenAI embeddings for semantic similarity matching
- **Multi-source Data**: Fetches from Reddit API (PRAW) and DuckDuckGo search
- **AI Summarization**: Generates comprehensive summaries of relevant discussions
- **Production-Ready**: Built with security, caching, and production deployment in mind

## Tech Stack

- **Backend**: FastAPI, Python 3.12+
- **Vector Database**: ChromaDB
- **Embeddings**: OpenAI text-embedding-ada-002
- **Data Sources**: Reddit API (PRAW), DuckDuckGo Search
- **Frontend**: HTML/CSS with Jinja2 templates

## Quick Start

### Prerequisites

- Python 3.12+
- OpenAI API key
- Reddit API credentials (optional, for PRAW)

### Setup

1. **Clone and setup environment**:
   ```bash
   git clone <your-repo-url>
   cd Reddit_adv_bot
   ```

2. **Create `.env` file** (copy from `.env.example`):
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USER_AGENT=your_app_name
   DISABLE_FETCHING=0
   ```

3. **Run the development server**:
   ```bash
   make dev
   ```

   This will:
   - Create a virtual environment (if needed)
   - Install all dependencies
   - Load environment variables
   - Start the FastAPI server on `http://localhost:8000`

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Create venv, install deps, run development server |
| `make run` | Run server (assumes deps already installed) |
| `make prod-run` | Run with `DISABLE_FETCHING=1` (production mode) |
| `make install` | Install/upgrade dependencies only |
| `make fmt` | Format code with black & isort |
| `make lint` | Run code linting (ruff/pyflakes) |
| `make clean` | Remove caches, build artifacts, venv |
| `make clean-db` | Remove ChromaDB vector store |
| `make freeze` | Update requirements.txt with exact versions |
| `make help` | Show all available targets |

## Usage

### Expected Response Times
- **Database retrieval**: 2-3 seconds for relevant posts
- **AI summary generation**: 20-40 seconds
- **New data fetching**: Variable (20-60 seconds depending on query)

### Using the Web Interface

1. **Visit the web interface**: Open `http://localhost:8000`

2. **Try these sample queries** (pre-populated data):
   - "Best weapons in BOTW"
   - "Best armor in TOTK" 
   - "Best recipes in Tears of the Kingdom"
   - "How to beat Ganon in BOTW"
   - "How to kill/farm Lynels in TOTK"
   - "Best ways to get rupees in Breath of the Wild"
   - "How to activate towers in TOTK"
   - "How to get dragon items in BOTW"
   - "How to dupe in Tears of the Kingdom"

3. **Get AI summaries**: Click "Generate Summary" for comprehensive analysis

> **Note**: All data comes from Reddit discussions. If answers seem irrelevant, it may indicate insufficient Reddit posts exist for that topic.

## API Endpoints

- `GET /` - Web interface
- `GET /query?q=<question>&metric=<timeframe>` - Search for answers
- `GET /summary?q=<question>` - Generate AI summary
- `GET /check-fetch-needed?q=<question>` - Check if new data fetching is needed

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - Required for embeddings and summarization
- `REDDIT_CLIENT_ID` - Reddit API credentials (optional)
- `REDDIT_CLIENT_SECRET` - Reddit API credentials (optional)
- `REDDIT_USER_AGENT` - Your app identifier for Reddit
- `DISABLE_FETCHING` - Set to `1` in production to use only pre-embedded data

### Production Mode

For production deployment, set `DISABLE_FETCHING=1` to prevent new data fetching:

```bash
make prod-run
```

Or set the environment variable:
```bash
export DISABLE_FETCHING=1
make run
```

## Project Structure

```
Reddit_adv_bot/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Environment configuration
│   ├── database.py          # ChromaDB operations
│   ├── reddit_scraper.py    # Reddit API (PRAW) scraping
│   ├── reddit_websearch_scraper.py # DuckDuckGo scraping
│   ├── utilities.py         # Helper functions
│   ├── security.py          # Input validation & sanitization
│   ├── ranking_posts.py     # Post scoring and AI ranking
│   ├── subreddit_finder.py  # Subreddit detection logic
│   ├── data/
│   │   ├── posts_db_v2/     # ChromaDB vector store
│   │   └── gaming_abbreviations.json
│   ├── static/              # CSS and images
│   └── templates/           # HTML templates
├── requirements.txt         # Python dependencies
├── Makefile                # Development and deployment commands
├── .gitignore              # Git ignore rules
└── .env                    # Environment variables (create from .env.example)
```

## Development

### Adding New Features

1. **Format code**: `make fmt`
2. **Run linting**: `make lint`
3. **Test locally**: `make dev`

### Database Management

- The ChromaDB vector store is pre-populated with gaming discussions
- Use `make clean-db` to reset the database (will require re-embedding)
- The app automatically embeds new posts when `DISABLE_FETCHING=0`

## Deployment

### Cloud Platforms

Recommended platforms for free/low-cost deployment:

1. **AWS EC2 Free Tier** (12 months free)
2. **Oracle Cloud Always Free** (permanent)
3. **Fly.io** (3 apps free)
4. **Railway** (trial credits)

### Deployment Steps

1. **Prepare for production**:
   ```bash
   export DISABLE_FETCHING=1
   make prod-run
   ```

2. **Set environment variables** on your platform

3. **Use the provided Makefile** for consistent deployment

## Security Features

- Input validation and sanitization
- Query length limits (512 characters)
- Game-specific query filtering (BOTW/TOTK only)
- Suspicious query logging
- Production mode with disabled data fetching

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `make fmt` and `make lint`
4. Test with `make dev`
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built for Zelda gaming community
- Uses OpenAI embeddings for semantic search
- Reddit data via PRAW and web scraping
