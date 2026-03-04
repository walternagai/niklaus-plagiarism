# Niklaus-plagiarism

## Purpose

The purpose of the Niklaus project is to provide a tool that can detect plagiarism in programming assignments. It is designed to help educators identify cases of academic dishonesty and ensure that students are submitting original work.

## How it works

Niklaus uses a combination of static analysis and machine learning techniques to compare code submissions and identify similarities. When a new assignment is submitted, Niklaus extracts features from the code, such as variable names, function names, and control structures. 

## Features

- **Automated plagiarism detection**: Niklaus can automatically compare code submissions to flag potential instances of plagiarism.
- **Multi-language support**: Supports C, C++, Java, JavaScript, and Python.
- **Customizable settings**: Educators can configure Niklaus to adjust the sensitivity of the plagiarism detection algorithm and set thresholds for similarity scores.
- **Detailed reports**: Niklaus generates detailed reports that highlight similarities between code submissions and provide AI-powered analysis via Groq LLM.
- **Security**: ZIP file validation (50MB limit, path traversal protection) and automatic cleanup of temporary files.

## Prerequisites

- Python 3.8 or higher
- Groq API key (get one at https://console.groq.com/)

## Installation

```bash
git clone https://github.com/walternagai/niklaus-plagiarism.git
cd niklaus-plagiarism
pip install -r requirements.txt
```

## Configuration

Set up your Groq API credentials using one of these methods:

### Option 1: Environment Variables (Recommended)

```bash
export GROQ_API_KEY="your-api-key-here"
export GROQ_MODEL="llama-3.1-70b-versatile"  # or your preferred model
```

### Option 2: Streamlit Secrets

Create `.streamlit/secrets.toml`:

```toml
[pytheo_groq]
GROQ_API_KEY = "your-api-key-here"
GROQ_MODEL = "llama-3.1-70b-versatile"
```

## Usage

```bash
streamlit run app.py
```

Then:
1. **Select the programming language** of the files you want to compare.
2. **Adjust the similarity threshold** (default: 0.7 or 70%).
3. **Upload a ZIP file** containing the source code files to compare.
4. **Wait for analysis** - Niklaus will generate a detailed report highlighting potential plagiarism.

**Note**: Maximum ZIP file size is 50MB. Files are automatically cleaned up after analysis.

## Supported Languages

- C (.c)
- C++ (.cpp)
- Java (.java)
- JavaScript (.js)
- Python (.py)

## Contributing

If you are interested in contributing to the Niklaus project, please read our [contributing guidelines](CONTRIBUTING.md) for more information.

## License

This project is licensed under the CC0 1.0 Universal License - see the [LICENSE](LICENSE) file for details.