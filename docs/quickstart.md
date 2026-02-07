# Quick Start Guide

This guide will help you get Intelligent Support Router up and running quickly.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker)
- Redis (or Docker)
- OpenAI API key

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/meryemsakin/supportiq.git
cd supportiq

# Copy environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
# Add: OPENAI_API_KEY=sk-your-api-key

# Start with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f app
```

The API will be available at `http://localhost:8000`

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/meryemsakin/supportiq.git
cd supportiq

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Edit .env with your settings
nano .env

# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py

# Start the server
uvicorn src.main:app --reload
```

## Configuration

Edit the `.env` file with your settings:

```env
# Required
OPENAI_API_KEY=sk-your-api-key

# Database (default works with Docker)
DATABASE_URL=postgresql://support_user:support_password@localhost:5432/support_router

# Redis (default works with Docker)
REDIS_URL=redis://localhost:6379/0

# Optional: Integrations
ZENDESK_SUBDOMAIN=your-subdomain
ZENDESK_EMAIL=your-email@example.com
ZENDESK_API_TOKEN=your-token
```

## First API Call

Create your first ticket:

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Uygulamanız çalışmıyor, sürekli hata veriyor",
    "subject": "Uygulama Hatası",
    "customer_email": "customer@example.com",
    "process_async": false
  }'
```

Expected response:

```json
{
  "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processed",
  "classification": {
    "primary_category": "technical_issue",
    "confidence": 0.92
  },
  "sentiment": {
    "sentiment": "negative",
    "score": -0.6
  },
  "priority": {
    "score": 4,
    "level": "high"
  }
}
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Next Steps

1. [Configure categories](configuration.md#categories)
2. [Set up routing rules](configuration.md#routing-rules)
3. [Integrate with Zendesk](integrations/zendesk.md)
4. [Deploy to production](deployment/docker.md)

## Troubleshooting

### Database connection error

Make sure PostgreSQL is running:

```bash
# Docker
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

### Redis connection error

Make sure Redis is running:

```bash
docker-compose ps redis
```

### OpenAI API errors

- Check your API key is valid
- Check your API quota/billing
- The system will fall back to rule-based classification if OpenAI fails

## Getting Help

- [GitHub Issues](https://github.com/meryemsakin/supportiq/issues)
- [Discussions](https://github.com/meryemsakin/supportiq/discussions)
