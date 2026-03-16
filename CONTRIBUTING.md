# Contributing to BotNode

Thank you for your interest in contributing to BotNode! This document provides guidelines and instructions for contributing to the project.

## 🎯 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## 🚀 Getting Started

### Prerequisites
- Python 3.14+
- Docker and Docker Compose
- Git
- Basic understanding of FastAPI and Redis

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub
   # Clone your fork
   git clone https://github.com/YOUR-USERNAME/botnode_unified.git
   cd botnode_unified
   
   # Add upstream remote
   git remote add upstream https://github.com/botnode-io/core.git
   ```

2. **Set Up Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   
   # Set up pre-commit hooks
   pre-commit install
   ```

3. **Run Services**
   ```bash
   # Start Redis and PostgreSQL
   docker-compose up -d redis postgres
   
   # Run the application
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Run worker
   python -m worker
   ```

## 📋 Contribution Workflow

### 1. Find an Issue
- Check [GitHub Issues](https://github.com/botnode-io/core/issues)
- Look for issues tagged `good-first-issue` or `help-wanted`
- Discuss your approach in the issue comments before starting

### 2. Create a Branch
```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/description-of-change
# or
git checkout -b fix/description-of-bug
# or
git checkout -b docs/description-of-docs
```

### 3. Make Changes
- Follow our [Python Documentation Standards](PYTHON_DOCSTRING_TEMPLATE.md)
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Test Your Changes
```bash
# Run tests
pytest

# Run type checking
mypy --strict --ignore-missing-imports .

# Run linters
flake8 .
black --check .
isort --check-only .

# Run documentation checks
interrogate --ignore-init-method --ignore-module --ignore-private .
```

### 5. Commit Your Changes
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new skill for data visualization

- Implement data visualization processor
- Add tests for visualization functions
- Update API documentation
- Fixes #123"

# Push to your fork
git push origin feature/description-of-change
```

### 6. Create Pull Request
1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. Fill out the PR template
4. Request review from maintainers
5. Address review comments

## 🧪 Testing Guidelines

### Unit Tests
- Place tests in `tests/` directory
- Use `pytest` framework
- Follow Arrange-Act-Assert pattern
- Aim for >80% code coverage

```python
def test_skill_execution():
    # Arrange
    processor = SkillProcessor()
    input_data = {"test": "data"}
    
    # Act
    result = processor.execute("test_skill", input_data)
    
    # Assert
    assert result["status"] == "success"
    assert "processed" in result
```

### Integration Tests
- Test interactions between components
- Use test databases (SQLite in-memory)
- Mock external APIs
- Test error conditions

### Performance Tests
- Include benchmarks for critical paths
- Test with realistic data sizes
- Monitor memory usage and response times

## 📝 Documentation Standards

### Code Documentation
- All public functions must have Google-style docstrings
- Include type hints for all parameters and return values
- Provide examples for complex functions
- Document exceptions that can be raised

### Skill Documentation
- Each skill must have a complete README.md
- Follow [SKILL_README_TEMPLATE.md](SKILL_README_TEMPLATE.md)
- Include API reference with examples
- Document configuration options

### Project Documentation
- Keep README.md up to date
- Update DIRECTORY_STRUCTURE.md when adding files
- Add to INVENTORY.md for new components

## 🎨 Code Style

### Python
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://github.com/PyCQA/isort) for imports
- Maximum line length: 88 characters

### Imports Order
```python
# Standard library
import os
import sys
from typing import Dict, List

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local
from .database import Session
from .models import User
```

### Naming Conventions
- **Variables**: `snake_case`
- **Functions**: `snake_case()`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_private_method()`

## 🔧 Skill Development

### Creating a New Skill
1. Copy template from `skill_template/`
2. Implement skill logic in `main.py`
3. Add tests in `tests/`
4. Create `Dockerfile`
5. Write `README.md`
6. Add to skills registry

### Skill Requirements
- Must have health check endpoint (`/healthz`)
- Must handle errors gracefully
- Must include comprehensive logging
- Must be stateless (use Redis for state)
- Must have timeout protection

### Skill API Contract
```python
# Request
{
    "input_data": {
        # Skill-specific input
    },
    "options": {
        # Optional configuration
    }
}

# Response
{
    "result": {
        # Processed output
    },
    "processing_time_ms": 150,
    "status": "success"
}
```

## 🚨 Pull Request Guidelines

### PR Title Format
```
type(scope): description

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance
```

### PR Description Template
```markdown
## Description
Brief description of changes

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Documentation updated

## Related Issues
Fixes #123
Related to #456

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process
1. **Automated Checks**: CI must pass
2. **Code Review**: At least one maintainer approval
3. **Documentation Review**: Docs must be updated
4. **Testing Review**: Tests must be comprehensive
5. **Merge**: Squash and merge with descriptive message

## 🐛 Bug Reports

### Reporting Bugs
1. Check if bug already reported
2. Use bug report template
3. Include steps to reproduce
4. Add error messages and logs
5. Specify environment details
