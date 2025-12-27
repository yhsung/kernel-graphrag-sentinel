# Kernel-GraphRAG Sentinel

**AI-Powered Linux Kernel Code Analysis & Impact Assessment**

Kernel-GraphRAG Sentinel is an intelligent analysis tool that parses Linux kernel C code, builds comprehensive call graphs in Neo4j, maps test coverage, and provides AI-powered impact analysis for code changes.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j](https://img.shields.io/badge/neo4j-5.14+-green.svg)](https://neo4j.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## 🎯 Features

- **📊 Call Graph Analysis**: Multi-hop function call chain traversal (up to N hops)
- **🧪 Test Coverage Mapping**: Automatic KUnit test-to-function mapping
- **🔍 Impact Assessment**: Analyze the impact of modifying any kernel function
- **⚡ Risk Evaluation**: Identify critical uncovered functions
- **🌳 Tree-sitter Parsing**: Accurate C code AST extraction
- **🗄️ Neo4j Graph Database**: Efficient storage and querying of code relationships
- **🖥️ CLI Interface**: User-friendly command-line tool
- **📝 YAML Configuration**: Flexible configuration management

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kernel Source Code                        │
│                    (Linux 6.13+)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────▼────────────────┐
        │    Module A: C Code Parser      │
        │  • tree-sitter AST extraction   │
        │  • GCC preprocessor integration │
        │  • Function/call detection      │
        └───────────────┬─────────────────┘
                        │ (Functions, Calls)
        ┌───────────────▼─────────────────┐
        │  Module B: Graph Database        │
        │  • Neo4j storage                 │
        │  • Node/relationship management  │
        │  • Batch ingestion               │
        └───────────────┬─────────────────┘
                        │ (Graph Data)
        ┌───────────────▼─────────────────┐
        │  Module C: KUnit Test Mapper     │
        │  • Test file parsing             │
        │  • Function coverage mapping     │
        │  • COVERS relationships          │
        └───────────────┬─────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │  Impact Analysis Module          │
        │  • Multi-hop call traversal      │
        │  • Test coverage assessment      │
        │  • Risk level calculation        │
        │  • Report generation             │
        └──────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Neo4j 5.14+ (local installation or Docker)
- Linux kernel source tree (tested with 6.13+)
- 4GB+ RAM recommended

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/kernel-graphrag-sentinel.git
cd kernel-graphrag-sentinel
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Install Neo4j**

Option A: Using the provided script (Ubuntu/Debian)
```bash
sudo ./scripts/install_neo4j.sh
```

Option B: Using Docker
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.14
```

4. **Configure environment**

```bash
cp .env.template .env
# Edit .env with your settings
export KERNEL_ROOT=/path/to/linux-6.13
export NEO4J_PASSWORD=password123
```

5. **Verify installation**

```bash
python3 src/main.py version
```

### First Analysis

Run the complete analysis pipeline on the ext4 filesystem:

```bash
# Extract, ingest, and map tests for ext4
python3 src/main.py pipeline fs/ext4

# Analyze a specific function
python3 src/main.py analyze ext4_map_blocks --max-depth 3

# View database statistics
python3 src/main.py stats
```

---

## 📖 Usage Guide

### CLI Commands

The `main.py` CLI provides comprehensive kernel analysis capabilities:

#### 1. **Ingest Subsystem**

Extract and ingest kernel code into Neo4j:

```bash
python3 src/main.py ingest fs/ext4
python3 src/main.py ingest fs/ext4 --clear-db  # Clear DB first
python3 src/main.py ingest net/ipv4 --skip-preprocessing
```

**Output:**
- Functions extracted and stored
- Call relationships mapped
- File and subsystem hierarchy created

#### 2. **Map Test Coverage**

Map KUnit test cases to tested functions:

```bash
python3 src/main.py map-tests fs/ext4
```

**Output:**
- Test cases identified
- COVERS relationships created
- Coverage statistics

#### 3. **Analyze Function Impact**

Comprehensive impact analysis for any function:

```bash
python3 src/main.py analyze ext4_map_blocks
python3 src/main.py analyze ext4_mb_new_blocks_simple --max-depth 5
python3 src/main.py analyze ext4_inode_bitmap --output report.txt
```

**Output:**
```
IMPACT ANALYSIS: ext4_map_blocks
================================================================================
File: fs/ext4/inode.c

SUMMARY
  Direct callers:       12
  Indirect callers:     45 (2-3 hops)
  Direct test coverage: 2 tests
  Indirect test coverage: 5 tests
  Total call chains:    57

RISK ASSESSMENT
  Risk Level: MEDIUM-HIGH (widely used, limited test coverage)
```

#### 4. **Complete Pipeline**

Run full analysis in one command:

```bash
python3 src/main.py pipeline fs/ext4
```

This executes:
1. Ingest subsystem code
2. Map test coverage
3. Display statistics

#### 5. **Database Statistics**

View current database state:

```bash
python3 src/main.py stats
```

**Output:**
```json
{
  "Function_count": 1121,
  "TestCase_count": 13,
  "File_count": 37,
  "CALLS_count": 2254,
  "COVERS_count": 17
}
```

#### 6. **Top Functions**

Identify most frequently called functions:

```bash
python3 src/main.py top-functions --limit 20
python3 src/main.py top-functions --subsystem ext4 --min-callers 10
```

**Output:**
```
TOP CALLED FUNCTIONS (min 5 callers)
  1. ext4_get_inode_loc               (28 calls) - inode.c
  2. ext4_free_blocks                 (23 calls) - mballoc.c
  3. ext4_map_blocks                  (22 calls) - inode.c
```

#### 7. **Generate Configuration**

Create configuration template:

```bash
python3 src/main.py init-config --output my-config.yaml
```

---

## ⚙️ Configuration

### YAML Configuration File

Create a configuration file for your analysis:

```yaml
# examples/analyze_ext4.yaml
kernel:
  root: /workspaces/ubuntu/linux-6.13
  subsystem: fs/ext4

neo4j:
  url: bolt://localhost:7687
  user: neo4j
  password: password123

preprocessing:
  enable_cpp: false  # Enable GCC preprocessor
  kernel_config: .config

analysis:
  max_call_depth: 3
  include_indirect_calls: true
  max_results: 100

llm:
  provider: openai
  model: gpt-4
  api_key: ${OPENAI_API_KEY}
  temperature: 0.7
```

Use the configuration:

```bash
python3 src/main.py --config my-config.yaml pipeline fs/ext4
```

### Environment Variables

Override configuration with environment variables:

```bash
export KERNEL_ROOT=/custom/path/to/linux
export NEO4J_URL=bolt://remote-server:7687
export NEO4J_PASSWORD=secret
```

---

## 📊 Example Analysis Results

### Case Study: ext4_mb_new_blocks_simple

```bash
$ python3 src/main.py analyze ext4_mb_new_blocks_simple --max-depth 3
```

**Analysis Output:**

```
IMPACT ANALYSIS: ext4_mb_new_blocks_simple
================================================================================
File: /workspaces/ubuntu/linux-6.13/fs/ext4/mballoc.c

SUMMARY
--------------------------------------------------------------------------------
  Direct callers:       1
  Indirect callers:     11 (2-3 hops)
  Direct callees:       4
  Indirect callees:     14 (2-3 hops)
  Direct test coverage: 1
  Indirect test coverage: 0
  Total call chains:    12

DIRECT CALLERS (functions that call this function)
--------------------------------------------------------------------------------
  1. ext4_mb_new_blocks (mballoc.c:6154)

INDIRECT CALLERS (multi-hop call chains)
--------------------------------------------------------------------------------
  1. ext4_alloc_branch (indirect.c) [depth: 2]
      Chain: ext4_alloc_branch → ext4_mb_new_blocks → ext4_mb_new_blocks_simple
  2. ext4_ext_map_blocks (extents.c) [depth: 2]
      Chain: ext4_ext_map_blocks → ext4_mb_new_blocks → ext4_mb_new_blocks_simple
  3. ext4_map_blocks_es_recheck (inode.c) [depth: 3]
      Chain: ext4_map_blocks_es_recheck → ext4_ext_map_blocks →
             ext4_mb_new_blocks → ext4_mb_new_blocks_simple

TEST COVERAGE
--------------------------------------------------------------------------------
  Direct coverage:
    - test_new_blocks_simple (mballoc-test.c)

RISK ASSESSMENT
--------------------------------------------------------------------------------
  Risk Level: MEDIUM-HIGH (used often, limited test coverage)
================================================================================
```

**Insights:**
- Function has 1 direct caller but 11 indirect callers
- Call chains extend up to 3 hops deep
- Has 1 test covering it directly
- Risk level is MEDIUM-HIGH due to widespread usage with limited testing

---

## 🗂️ Project Structure

```
kernel-graphrag-sentinel/
├── src/
│   ├── main.py                # CLI entry point
│   ├── config.py              # Configuration management
│   ├── module_a/              # C Code Parser
│   │   ├── preprocessor.py    # GCC preprocessor integration
│   │   ├── parser.py          # tree-sitter C parser
│   │   └── extractor.py       # Function/call extraction
│   ├── module_b/              # Graph Database
│   │   ├── graph_store.py     # Neo4j driver integration
│   │   ├── schema.py          # Graph schema definitions
│   │   └── ingestion.py       # Data ingestion pipeline
│   ├── module_c/              # KUnit Test Mapper
│   │   ├── kunit_parser.py    # Test file parsing
│   │   └── test_mapper.py     # Test-to-function mapping
│   └── analysis/              # Impact Analysis
│       ├── queries.py         # Cypher query templates
│       └── impact_analyzer.py # Impact analysis engine
├── scripts/
│   ├── install_neo4j.sh       # Neo4j installation script
│   └── setup_tree_sitter.sh   # tree-sitter setup
├── examples/
│   └── analyze_ext4.yaml      # Example configuration
├── docs/
│   └── DEVELOPMENT_PLAN.md    # Development documentation
├── requirements.txt           # Python dependencies
├── .env.template              # Environment template
└── README.md                  # This file
```

---

## 🔬 Technical Details

### Supported Kernel Versions

Tested with:
- Linux 6.13
- Linux 6.12
- Should work with 6.x series

### Graph Schema

**Nodes:**
- `Function`: Kernel functions
- `TestCase`: KUnit test cases
- `File`: Source files
- `Subsystem`: Kernel subsystems

**Relationships:**
- `CALLS`: Function → Function (call relationship)
- `COVERS`: TestCase → Function (test coverage)
- `CONTAINS`: File → Function (containment)
- `BELONGS_TO`: File → Subsystem (hierarchy)

### Query Performance

**Benchmarks (ext4 subsystem):**
- Parsing: ~20 seconds for 37 files
- Ingestion: ~5 seconds for 1,121 functions
- Impact analysis: ~1 second per function (depth=3)

### Limitations

- **Macro expansion**: Optional GCC preprocessing (can be slow)
- **Function pointers**: Static analysis limitations
- **External calls**: Functions outside subsystem marked as external
- **Header files**: Currently analyzes .c files only

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest tests/

# Specific module
pytest tests/test_parser.py

# With coverage
pytest --cov=src tests/
```

### Test a Different Subsystem

```bash
# Test with btrfs filesystem
python3 src/main.py pipeline fs/btrfs

# Test with networking stack
python3 src/main.py pipeline net/ipv4
```

---

## 🛠️ Development

### Code Quality

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/
```

### Adding New Features

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Implement changes with tests
4. Run test suite: `pytest tests/`
5. Submit pull request

---

## 📚 Use Cases

### 1. Code Change Impact Assessment

Before modifying a kernel function:
```bash
python3 src/main.py analyze <function_name>
```
Understand:
- What functions will be affected
- Which tests need to run
- Risk level of the change

### 2. Test Coverage Analysis

Identify untested critical functions:
```bash
python3 src/main.py top-functions --min-callers 20
```
Then check each for test coverage.

### 3. Subsystem Architecture Understanding

Build call graph for any subsystem:
```bash
python3 src/main.py ingest fs/ext4
python3 src/main.py stats
```

### 4. Refactoring Planning

Before refactoring, analyze call chains:
```bash
python3 src/main.py analyze <target_function> --max-depth 5
```

---

## 🐛 Troubleshooting

### Neo4j Connection Issues

```bash
# Check Neo4j status
sudo service neo4j status

# Start Neo4j
sudo service neo4j start

# Test connection
python3 -c "from src.module_b.graph_store import Neo4jGraphStore; Neo4jGraphStore().execute_query('RETURN 1')"
```

### Parsing Errors

If parsing fails:
1. Try with `--skip-preprocessing` flag
2. Check kernel source path: `echo $KERNEL_ROOT`
3. Verify tree-sitter installation: `python3 -c "import tree_sitter_c"`

### Performance Issues

For large subsystems:
- Use `--skip-preprocessing` for faster parsing
- Increase Neo4j heap size in `neo4j.conf`
- Run analysis in batches

---

## 🗺️ Roadmap

### Completed (v0.1.0)
- ✅ Tree-sitter C parser integration
- ✅ Neo4j graph database storage
- ✅ KUnit test mapping
- ✅ Multi-hop call chain analysis
- ✅ CLI interface
- ✅ YAML configuration

### Planned (v0.2.0)
- [ ] LLM-powered natural language reports
- [ ] Web UI for visualization
- [ ] Data flow analysis
- [ ] Struct field tracking
- [ ] Git integration for historical analysis

### Future
- [ ] IDE integration (VS Code, Neovim)
- [ ] CI/CD pipeline integration
- [ ] Performance profiling integration
- [ ] Kernel module analysis

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **tree-sitter**: https://tree-sitter.github.io/
- **Neo4j**: https://neo4j.com/
- **Click**: https://click.palletsprojects.com/
- **Linux Kernel**: https://kernel.org/

---

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/kernel-graphrag-sentinel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/kernel-graphrag-sentinel/discussions)

---

## 📊 Statistics

**Current Database (ext4 subsystem):**
- 1,121 Functions
- 2,254 Call relationships
- 13 Test cases
- 17 Test coverage mappings
- 37 Source files analyzed

**Analysis Capabilities:**
- Multi-hop traversal (up to 10 hops)
- Risk assessment (4 levels)
- Test coverage tracking
- Cross-subsystem call detection

---

**Built with ❤️ for the Linux kernel community**
