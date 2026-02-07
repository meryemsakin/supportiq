# Contributing to Intelligent Support Router

First off, thank you for considering contributing to Intelligent Support Router! It's people like you that make this project a great tool for the community.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include logs and screenshots if applicable**

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- **A clear and descriptive title**
- **A detailed description of the proposed enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure the test suite passes
4. Make sure your code follows the existing style
5. Issue the pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/meryemsakin/supportiq.git
cd supportiq

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run tests
pytest

# Run the development server
uvicorn src.main:app --reload
```

## Coding Standards

### Python Style

- Follow PEP 8
- Use Black for formatting
- Use isort for import sorting
- Maximum line length: 88 characters
- Use type hints where possible

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/
mypy src/
```

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests liberally

### Documentation

- Update the README.md if needed
- Add docstrings to all public functions
- Update API documentation for endpoint changes

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_classifier.py

# Run tests matching a pattern
pytest -k "test_priority"
```

## Project Structure

```
src/
├── api/          # FastAPI endpoints
├── models/       # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
├── integrations/ # External system clients
├── workers/      # Celery tasks
└── utils/        # Utility functions
```

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🎉
