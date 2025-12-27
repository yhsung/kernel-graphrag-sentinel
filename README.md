# Kernel-GraphRAG Sentinel

An intelligent Linux kernel analysis tool that combines static code analysis with Graph Retrieval-Augmented Generation (GraphRAG) to understand kernel subsystems, track function call chains, and provide AI-powered insights.

## Overview

Kernel-GraphRAG Sentinel parses Linux kernel C code using tree-sitter, builds a knowledge graph in Neo4j, and leverages LLMs to answer complex questions about kernel internals, data flows, and code relationships.

## Features

- **C Code Parsing**: Tree-sitter-based AST extraction from kernel source code
- **Preprocessor Support**: Handles C preprocessor directives and macro expansions
- **Graph Database**: Stores code relationships in Neo4j for efficient querying
- **Multi-LLM Support**: Works with OpenAI, Google Gemini, Anthropic Claude, and local Ollama models
- **Call Chain Analysis**: Tracks function call relationships with configurable depth
- **Subsystem Focus**: Analyze specific kernel subsystems (e.g., fs/ext4, mm, net)
- **AI-Powered Q&A**: Natural language queries about kernel code using GraphRAG

## Architecture

```
┌─────────────────┐
│  Kernel Source  │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Module A│ Tree-sitter Parser
    │         │ + Preprocessor
    └────┬────┘
         │
    ┌────▼────┐
    │ Module B│ Graph Builder
    │         │ (Neo4j)
    └────┬────┘
         │
    ┌────▼────┐
    │ Module C│ GraphRAG Query
    │         │ + LLM Integration
    └─────────┘
```

## Prerequisites

- Python 3.9+
- Neo4j 5.14+ (local or cloud instance)
- Linux kernel source tree (tested with 6.13+)
- API key for your chosen LLM provider (or Ollama for local inference)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yhsung/kernel-graphrag-sentinel.git
cd kernel-graphrag-sentinel
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Tree-sitter (Optional)

If tree-sitter-c needs manual setup:

```bash
./scripts/setup_tree_sitter.sh
```

### 4. Install Neo4j

Use the provided script or install manually:

```bash
./scripts/install_neo4j.sh
```

Or use Docker:

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest
```

### 5. Configure Environment

Copy the template and edit with your settings:

```bash
cp .env.template .env
```

Edit `.env` with your configuration:

```bash
# Kernel source location
KERNEL_ROOT=/path/to/linux-6.13

# Neo4j connection
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM provider (openai, gemini, anthropic, ollama)
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Basic Analysis

```python
from src.module_a.parser import CParser
from src.module_a.preprocessor import Preprocessor

# Parse a kernel file
preprocessor = Preprocessor()
parser = CParser()

with open('/path/to/kernel/file.c', 'r') as f:
    source = f.read()

# Preprocess and parse
preprocessed = preprocessor.preprocess(source)
ast = parser.parse(preprocessed)

# Find functions
functions = parser.find_functions(ast)
for node, name in functions:
    print(f"Function: {name}")
```

### Build Knowledge Graph

```python
# Example: Build graph for ext4 filesystem
from src.module_b import GraphBuilder

builder = GraphBuilder(kernel_root="/path/to/linux-6.13")
builder.analyze_subsystem("fs/ext4")
```

### Query with GraphRAG

```python
from src.module_c import GraphRAGQuery

query_engine = GraphRAGQuery()

# Ask natural language questions
response = query_engine.ask(
    "What is the call chain from ext4_file_write_iter to the block layer?"
)
print(response)
```

## Project Structure

```
kernel-graphrag-sentinel/
├── src/
│   ├── module_a/          # Parsing & Preprocessing
│   │   ├── parser.py      # Tree-sitter C parser
│   │   ├── preprocessor.py # C preprocessor handler
│   │   └── extractor.py   # AST feature extraction
│   ├── module_b/          # Graph Construction
│   ├── module_c/          # GraphRAG Query Engine
│   ├── analysis/          # Analysis utilities
│   └── utils/             # Common utilities
├── scripts/               # Setup scripts
├── tests/                 # Unit tests
├── examples/              # Example usage
├── docs/                  # Documentation
└── requirements.txt       # Python dependencies
```

## Configuration Options

Edit `.env` to customize:

- **`MAX_CALL_DEPTH`**: Maximum depth for call chain analysis (default: 3)
- **`ENABLE_CPP_PREPROCESSING`**: Enable C preprocessor (default: true)
- **`INCLUDE_INDIRECT_CALLS`**: Track function pointer calls (default: true)
- **`LOG_LEVEL`**: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ tests/
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

## Roadmap

- [ ] Support for kernel module analysis
- [ ] Visualization of call graphs
- [ ] Integration with kernel documentation
- [ ] Performance optimization for large subsystems
- [ ] Web UI for interactive exploration

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Specify your license here]

## Acknowledgments

- Built with [tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- Graph database powered by [Neo4j](https://neo4j.com/)
- LLM integration via [LlamaIndex](https://www.llamaindex.ai/)

## Support

For issues and questions, please open an issue on GitHub.
