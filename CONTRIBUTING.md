# Contributing to Shell Matrix

First off, thank you for considering contributing to Shell Matrix! It's people like you that make Shell Matrix such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps which reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include screenshots if possible**
- **Include your environment details** (OS, Python version, browser)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and explain which behavior you expected to see instead**
- **Explain why this enhancement would be useful**

### Pull Requests

- Fill in the required template
- Follow the Python style guide (PEP 8)
- Include screenshots in your pull request whenever possible
- Document new code
- End all files with a newline

## Development Setup

1. Fork the repo
2. Clone your fork:
```bash
git clone https://github.com/your-username/shell-matrix.git
cd shell-matrix
```

3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a branch:
```bash
git checkout -b feature/your-feature-name
```

6. Make your changes and test them

7. Commit your changes:
```bash
git add .
git commit -m "Add some feature"
```

8. Push to your fork:
```bash
git push origin feature/your-feature-name
```

9. Create a Pull Request

## Style Guide

### Python Code Style

- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions and classes
- Add comments for complex logic

### JavaScript Code Style

- Use camelCase for variables and functions
- Use meaningful variable names
- Add comments for complex logic
- Keep functions small and focused

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add proxy authentication support

- Add username/password fields to proxy modal
- Update proxy connection logic
- Add tests for proxy authentication

Fixes #123
```

## Testing

Before submitting a pull request, please test your changes:

1. Test the basic functionality
2. Test in different browsers (Chrome, Firefox, Edge)
3. Test with different shells (bash, zsh, fish)
4. Test workspace management
5. Test session save/restore

## Documentation

Update the README.md if you:
- Add a new feature
- Change existing functionality
- Add new configuration options
- Add new dependencies

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🎉
