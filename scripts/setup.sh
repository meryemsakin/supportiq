#!/bin/bash

# =============================================================================
# Intelligent Support Router - Setup Script
# =============================================================================

set -e

echo "=============================================="
echo "Intelligent Support Router - Setup"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}1. Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python 3.11+ is required. Found: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}Python $python_version found${NC}"

# Create virtual environment
echo -e "\n${YELLOW}2. Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}3. Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}Virtual environment activated${NC}"

# Upgrade pip
echo -e "\n${YELLOW}4. Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "\n${YELLOW}5. Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed${NC}"

# Copy environment file
echo -e "\n${YELLOW}6. Setting up environment file...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}.env file created from .env.example${NC}"
    echo -e "${YELLOW}Please edit .env and add your OPENAI_API_KEY${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Create data directories
echo -e "\n${YELLOW}7. Creating data directories...${NC}"
mkdir -p data/chroma
echo -e "${GREEN}Data directories created${NC}"

# Run database migrations (if alembic is set up)
echo -e "\n${YELLOW}8. Setting up database...${NC}"
if [ -f "alembic.ini" ]; then
    # Check if DATABASE_URL is set
    if grep -q "DATABASE_URL" .env 2>/dev/null; then
        echo "Running Alembic migrations..."
        alembic upgrade head 2>/dev/null || echo "Note: Run 'alembic revision --autogenerate' to create initial migration"
    else
        echo -e "${YELLOW}Note: Set DATABASE_URL in .env to run migrations${NC}"
    fi
fi

# Seed database (optional)
echo -e "\n${YELLOW}9. Seeding database (optional)...${NC}"
read -p "Do you want to seed the database with sample data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/seed_data.py
fi

echo -e "\n=============================================="
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "=============================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Start the development server:"
echo "   source venv/bin/activate"
echo "   uvicorn src.main:app --reload"
echo ""
echo "Or use Docker:"
echo "   docker-compose up -d"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
