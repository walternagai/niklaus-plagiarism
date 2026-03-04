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
export MARITACA_MODEL="sabiazinho-4"  # optional, defaults to sabiazinho-4

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

## Project Structure

```
niklaus-plagiarism/
├── app.py                      # Main Streamlit application (5 tabs)
├── analyzer/                   # Advanced analysis modules
│   ├── __init__.py            # Module exports
│   ├── ast_parser.py          # AST parsing and structural similarity
│   ├── metrics.py             # Code complexity metrics
│   ├── clustering.py          # Similarity clustering and graph analysis
│   └── patterns.py            # Plagiarism pattern detection
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── ANALYZER_GUIDE.md           # Analyzer module usage guide
├── CONTRIBUTING.md             # This file
├── .env.example                # Environment variables template
└── .streamlit/
    └── secrets.toml.example    # Streamlit secrets template
```

## Features Implementation Status

| Feature | Status | Description |
|---------|--------|-------------|
| Basic similarity detection | ✅ | Text-based comparison using SequenceMatcher |
| Multi-language support | ✅ | C, C++, Java, JavaScript, Python, Go, Rust, TypeScript, Kotlin |
| AI-powered analysis | ✅ | Maritaca Sabiazinho-4 integration |
| Heatmap visualization | ✅ | Plotly interactive similarity matrix |
| CSV/JSON/PDF export | ✅ | Multiple export formats |
| Dark mode | ✅ | Theme switcher in sidebar |
| AST structural analysis | ✅ | Phase 1 - Python native, others fingerprint |
| Code metrics | ✅ | LOC, CC, functions, nesting, maintainability |
| Plagiarism patterns | ✅ | 8 types with confidence scores |
| Similarity graph | ✅ | Phase 2 - Interactive NetworkX visualization |
| Cluster detection | ✅ | Phase 2 - Hierarchical clustering + communities |
| Visual diff | ✅ | Phase 2 - Unified diff with highlighting |
| Enriched PDF | ✅ | Phase 2 - Metrics, AST, cluster summaries |
| User authentication | 🔜 | Future feature |
| LMS integration | 🔜 | Canvas, Moodle |
| Batch ZIP processing | 🔜 | Multiple uploads |

## Future Features

- User management and authentication
- Integration with learning management systems (Canvas, Moodle)
- Batch processing for multiple ZIP files
- Real-time collaboration
- Test suite with automated testing
- Performance optimization for large datasets (>100 files)

## Questions?

Contact the maintainer at [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)