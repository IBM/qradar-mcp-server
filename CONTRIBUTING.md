# Contributing to QRadar MCP Server

Thank you for your interest in contributing to this project! This document provides guidelines for contributing.

## Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/). All commits must be signed off to certify that you have the right to submit your contribution under the project's license.

### Signing Your Commits

To sign off your commits, use the `-s` flag:

```bash
git commit -s -m "Your commit message"
```

This adds a `Signed-off-by` line to your commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

**All commits without DCO sign-off will be rejected.**

### Configuring Git

Set your name and email (public GitHub credentials):

```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## How to Contribute

### 1. Fork and Clone

```bash
git clone https://github.com/IBM/qradar-mcp-server.git
cd qradar-mcp-server
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/description` — New features
- `fix/issue-number` — Bug fixes
- `docs/description` — Documentation updates

### 3. Make Your Changes

- Follow existing code style (PEP 8 for Python)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Commit and Push

```bash
git add .
git commit -s -m "feat: add new feature description"
git push origin feature/your-feature-name
```

Commit message format:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `chore:` — Maintenance tasks
- `refactor:` — Code refactoring

### 5. Open a Pull Request

1. Go to https://github.com/IBM/qradar-mcp-server/pulls
2. Click "New Pull Request"
3. Select your branch
4. Provide a clear description of your changes

## Code Guidelines

### Python Code Style

- Follow PEP 8
- Use type hints where appropriate
- Add docstrings for functions and classes
- Keep functions focused (single responsibility)

### Security

- Never commit credentials, tokens, or secrets
- Use environment variables for sensitive data
- Validate user input
- Follow least privilege principle

## Review Process

1. Automated checks must pass
2. Code review by maintainer(s)
3. Address review feedback
4. Maintainer merges PR

## Questions?

- Open an issue: https://github.com/IBM/qradar-mcp-server/issues
- Email the maintainer: ashrivastava@ibm.com

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
