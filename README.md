# AI Prompt Service

A FastAPI service that provides a unified interface for interacting with AI models like Claude and Gemini, supporting both ad hoc and stateful session modes.

## Features

- **Multiple AI Providers**: Supports both Claude and Gemini AI models
- **Flexible Usage Modes**:
  - **Ad hoc Mode**: Stateless requests for one-off interactions
  - **Session Mode**: Stateful conversations with persistent context
- **Database Integration**: PostgreSQL for session storage
- **Docker Support**: Easy containerization with Docker and Docker Compose
- **Comprehensive API**: Well-documented endpoints with OpenAPI/Swagger

## Prerequisites

- Python 3.11+
- PostgreSQL 16
- Docker and Docker Compose (optional, for containerized deployment)
- Anthropic API key (for Claude)
- Google API key (for Gemini)

## Quick Start with Docker

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your API keys
3. Run with Docker Compose:

```bash
docker-compose up -d
```

4. Access the API at http://localhost:8000/api/docs

## Manual Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys
4. Set up PostgreSQL:

```bash
# Create database
createdb prompt_service

# Run migrations
alembic upgrade head
```

5. Start the application:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### Ad hoc Mode

The ad hoc mode provides a stateless interface where you need to include all context with each request.

```bash
curl -X POST http://localhost:8000/api/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "You are a helpful AI assistant.",
    "human_input": "Tell me about quantum computing.",
    "ai_provider": "claude",
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 500
    }
  }'
```

### Session Mode

Session mode provides a stateful interface for maintaining conversation context.

1. Create a session:

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "You are a helpful AI assistant.",
    "ai_provider": "claude",
    "model": "claude-3-sonnet-20240229"
  }'
```

2. Send a message in the session (using the session ID from the previous response):

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Tell me about quantum computing.",
    "parameters": {
      "temperature": 0.7
    }
  }'
```

3. Get session details:

```bash
curl http://localhost:8000/api/sessions/{session_id}
```

## API Documentation

Full API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

## Project Structure

```
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker configuration
├── migrations/               # Database migrations
│   ├── env.py                # Alembic environment
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration versions
├── requirements.txt          # Project dependencies
├── src/                      # Source code
│   ├── config.py             # Application configuration
│   ├── database.py           # Database setup
│   ├── db_models.py          # Database models
│   ├── main.py               # FastAPI application
│   ├── models.py             # Pydantic models
│   └── services/             # Service implementations
│       ├── ai_service.py     # Base AI service interface
│       ├── claude_service.py # Claude service implementation
│       ├── gemini_service.py # Gemini service implementation
│       └── session_service.py # Session management service
```

## Database Schema

### Sessions Table
- `id` (UUID): Primary key
- `ai_provider` (String): AI provider name (claude, gemini)
- `model` (String): AI model name
- `system_prompt` (Text): System instructions for the AI
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Messages Table
- `id` (UUID): Primary key
- `session_id` (UUID): Foreign key to sessions table
- `role` (String): Message role (human, assistant)
- `content` (Text): Message content
- `created_at` (DateTime): Creation timestamp
- `order` (Integer): Message order in conversation

## Environment Variables

| Variable            | Description                               | Default                                           |
|---------------------|-------------------------------------------|---------------------------------------------------|
| DATABASE_URL        | PostgreSQL connection string              | postgresql+asyncpg://postgres:postgres@localhost:5432/prompt_service |
| DB_ECHO             | Enable SQLAlchemy query logging           | false                                             |
| ANTHROPIC_API_KEY   | Anthropic API key for Claude              | -                                                 |
| GOOGLE_API_KEY      | Google API key for Gemini                 | -                                                 |
| SESSION_EXPIRY_HOURS| Hours before session cleanup              | 24                                                |

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

Create a migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

## Security Considerations

- API keys are stored in environment variables
- No authentication is implemented - add appropriate authentication for production
- Consider implementing rate limiting for production use

## License

This project is licensed under the MIT License - see the LICENSE file for details.