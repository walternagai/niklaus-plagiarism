# Contributing

We welcome contributions to the Niklaus project! Whether you want to report a bug, request a feature, or submit a pull request, we appreciate your help in making Niklaus better.

## Code of Conduct

This project follows academic integrity principles. Please ensure all contributions respect copyright and licensing requirements.

## How to Contribute

### Reporting Issues

If you encounter a bug or issue with Niklaus, please:
1. Check existing issues to avoid duplicates
2. Open a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

Or e-mail us at [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style
4. Test your changes thoroughly
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/niklaus-plagiarism.git
cd niklaus-plagiarism

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export MARITACA_API_KEY="your-test-api-key"
export MARITACA_MODEL="sabia-4"

# Run the app
streamlit run app.py
```

## Code Style

- Follow PEP 8 guidelines
- Keep functions small and focused
- Add docstrings to new functions
- Remove unnecessary comments from production code

## Security

- **Never commit API keys or secrets**
- All ZIP files are validated for path traversal attacks
- Temporary files are automatically cleaned up after analysis
- Maximum file size limit: 50MB

## Future Features

- User management and authentication
- Additional programming languages (Rust, Go, etc.)
- Integration with learning management systems (Canvas, Moodle, etc.)
- Enhanced visualization dashboard (heatmaps, similarity networks)
- Batch processing for multiple ZIP files
- Export reports to PDF/CSV (✅ implemented)
- Interactive code comparison view (✅ implemented)
- Dark mode toggle (✅ implemented)

## Questions?

Contact the maintainer at [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)