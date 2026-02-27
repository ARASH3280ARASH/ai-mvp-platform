# Contributing to AI-Powered Trading Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/ai-mvp-platform.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt`

## Development Guidelines

### Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Include docstrings for all public classes and methods (NumPy style)
- Keep functions focused and under 50 lines where practical

### Financial Data Handling

- **Never use random train/test splits** — always use `TimeSeriesSplit` or temporal splits
- Validate that no look-ahead bias exists in features or signals
- Include realistic transaction costs in all backtest evaluations
- Document any assumptions about data frequency or market hours

### AI Module Development

- New models should integrate with the existing `AIPipeline`
- Use the `AIConfig` dataclass for all hyperparameters
- Include unit tests in `tests/test_ai/`
- Log all predictions when `config.log_predictions` is True

### Testing

- Write tests for new features: `pytest tests/`
- Ensure all existing tests pass before submitting
- Include edge cases (empty data, single row, missing columns)

### Commit Messages

Use conventional commit format:

```
feat: add new feature description
fix: correct bug in module
docs: update documentation
test: add tests for module
refactor: restructure code without behavior change
```

## Pull Request Process

1. Update documentation if you've changed APIs
2. Add or update tests for your changes
3. Ensure all tests pass: `pytest tests/ -v`
4. Update `requirements.txt` if you've added dependencies
5. Submit a pull request with a clear description of changes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
