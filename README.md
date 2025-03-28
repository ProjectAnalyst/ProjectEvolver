# Project Evolver

Project Evolver is a tool that automatically evolves codebases based on whitepaper specifications. It analyzes whitepaper sections, makes decisions about necessary changes, and implements them while maintaining code quality and test coverage.

## Features

- Whitepaper-driven development
- Automated code generation and modification
- Test-driven development support
- Git integration for version control
- File management with backup support
- Extensible decision engine

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/project-evolver.git
cd project-evolver
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file
echo "GITHUB_TOKEN=your_github_token_here" > .env
```

## Usage

1. Create a whitepaper for your project in markdown format:
```markdown
# Project Name

## Overview
Project description...

## Features
- Feature 1
- Feature 2
...
```

2. Run the evolver:
```bash
python main.py username/repository
```

The evolver will:
1. Clone or update the repository
2. Process the whitepaper sections
3. Generate and apply code changes
4. Run tests
5. Commit changes to git

## Testing

Run the test suite:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 