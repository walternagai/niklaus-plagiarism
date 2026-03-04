# Niklaus-plagiarism

## Purpose

The purpose of the Niklaus project is to provide a tool that can detect plagiarism in programming assignments. It is designed to help educators identify cases of academic dishonesty and ensure that students are submitting original work.

## How it works

Niklaus uses a combination of static analysis and AI techniques to compare code submissions and identify similarities. When a new assignment is submitted, Niklaus extracts features from the code, such as variable names, function names, and control structures, and uses Maritaca's Sabiazinho model for intelligent analysis.

## Features

- **Automated plagiarism detection**: Niklaus can automatically compare code submissions to flag potential instances of plagiarism.
- **Multi-language support**: Supports C, C++, Java, JavaScript, Python, Go, Rust, TypeScript, and Kotlin.
- **Customizable settings**: Educators can configure Niklaus to adjust the sensitivity of the plagiarism detection algorithm and set thresholds for similarity scores.
- **Detailed reports**: Niklaus generates detailed reports that highlight similarities between code submissions and provide AI-powered analysis via Maritaca's Sabiazinho model.
- **Interactive visualizations**: 
  - Heatmaps for similarity matrices
  - Radar charts for code metrics comparison
  - **Similarity graph** showing connections between files (Phase 2)
- **Cluster analysis**: Automatic detection of plagiarism clusters with severity classification (high, moderate, low).
- **Visual diff view**: Side-by-side code comparison with highlighted differences (unified diff format).
- **Enriched PDF reports**: Color-coded similarity tables, complexity metrics, AST scores, and cluster summaries.
- **Export capabilities**: CSV, JSON, and PDF export options for reports.
- **Security**: ZIP file validation (50MB limit, path traversal protection) and automatic cleanup of temporary files.

## Prerequisites

- Python 3.8 or higher
- Maritaca API key (get one at https://maritaca.ai/)

## Installation

```bash
git clone https://github.com/walternagai/niklaus-plagiarism.git
cd niklaus-plagiarism
pip install -r requirements.txt
```

## Configuration

Set up your Maritaca API credentials using one of these methods:

### Option 1: Environment Variables (Recommended)

```bash
export MARITACA_API_KEY="your-api-key-here"
export MARITACA_MODEL="sabiazinho-4"  # default if not set
```

### Option 2: Streamlit Secrets

Create `.streamlit/secrets.toml`:

```toml
[maritaca]
MARITACA_API_KEY = "your-api-key-here"
MARITACA_MODEL = "sabiazinho-4"
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
5. **Explore tabs**:
   - **Upload & Analysis**: File upload and analysis trigger
   - **Results**: Filtered similarity table with AI analysis and visual diff
   - **Statistics**: Heatmaps and similarity distribution
   - **Advanced Analysis**: AST similarity, code metrics, and plagiarism pattern detection
   - **Similarity Graph**: Interactive network visualization of file clusters

**Note**: Maximum ZIP file size is 50MB. Files are automatically cleaned up after analysis.

## Supported Languages

| Language | Extension | AST Parsing |
|----------|-----------|-------------|
| Python | .py | Full support |
| C | .c | Fingerprint-based |
| C++ | .cpp | Fingerprint-based |
| Java | .java | Fingerprint-based |
| JavaScript | .js | Fingerprint-based |
| TypeScript | .ts | Fingerprint-based |
| Go | .go | Fingerprint-based |
| Rust | .rs | Fingerprint-based |
| Kotlin | .kt | Fingerprint-based |

## Tabs Overview

### Tab 1: Upload & Analysis
- File upload interface
- Language and threshold selection
- Last analysis summary

### Tab 2: Results
- Similarity table with progress bars
- AI-powered analysis for each suspicious pair
- **Visual diff view** (toggle between side-by-side code and unified diff)
- Export options (CSV, JSON, PDF)

### Tab 3: Statistics
- Summary metrics (mean, median, std deviation)
- Similarity heatmap
- Distribution histogram by similarity bands
- File preview

### Tab 4: Advanced Analysis
- **Structural (AST) similarity** - compares code structure, not just text
- **Code complexity metrics** - LOC, cyclomatic complexity, function count, nesting depth, maintainability index
- **Radar chart comparison** - visual metrics comparison between file pairs
- **Plagiarism pattern detection** - identifies 8 types of plagiarism with confidence scores

### Tab 5: Similarity Graph (Phase 2)
- **Interactive network visualization** showing file connections
- Nodes = files, edges = similarity above threshold
- Edge thickness proportional to similarity
- **Cluster coloring** - files grouped by similarity clusters
- **Cluster details**: central files, statistics, severity badges
- **Community detection** using greedy modularity optimization

## Technology Stack

- **Frontend**: Streamlit (interactive web interface)
- **Backend**: Python with OpenAI SDK (compatible with Maritaca API)
- **AI Model**: Maritaca Sabiazinho-4 (Brazilian LLM for code analysis)
- **Visualization**: Plotly (heatmaps, charts, network graphs)
- **Graph Analysis**: NetworkX (similarity graphs, community detection)
- **Clustering**: SciPy (hierarchical clustering)
- **Code Analysis**: AST parsing (Python native), fingerprint algorithms
- **Export**: FPDF (PDF reports), Pandas (CSV/JSON)

## Plagiarism Types Detected

1. **COPIA_DIRETA** - Direct copy (>95% similarity)
2. **RENOMEACAO_VARIAVEIS** - Variable/function renaming
3. **REORDENACAO_CODIGO** - Code block reordering
4. **INSERCAO_CODIGO_MORTO** - Dead code insertion
5. **REFATORACAO_LEVE** - Light refactoring
6. **REFATORACAO_PESADA** - Heavy refactoring
7. **SIMILARIDADE_BAIXA** - Low similarity (likely original)
8. **REUSO_LEGITIMO** - Legitimate code reuse

## Contributing

If you are interested in contributing to the Niklaus project, please read our [contributing guidelines](CONTRIBUTING.md) for more information.

## License

This project is licensed under the CC0 1.0 Universal License - see the [LICENSE](LICENSE) file for details.