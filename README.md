# Pynt — Educational Code Analyzer

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-green)
![VS Code](https://img.shields.io/badge/VS%20Code-1.80%2B-blue)

Pynt is a VS Code extension that analyzes your code for security vulnerabilities, style issues, and common bugs — and explains each finding in plain language so you can learn from it.

It combines **Semgrep** (fast static analysis) with **LLM-powered explanations** (via Groq) and **RAG-based project context** to give targeted, educational feedback directly in the editor.

---

## Architecture Overview

```
┌──────────────────────────────────┐
│       VS Code Extension          │
│  (TypeScript)                    │
│                                  │
│  - Highlights problematic lines  │
│  - Shows hover tooltips          │
│  - Applies quick fixes           │
└───────────────┬──────────────────┘
                │ HTTP (localhost:8000)
┌───────────────▼──────────────────┐
│       FastAPI Backend            │
│  (Python)                        │
│                                  │
│  1. Semgrep  → static findings   │
│  2. RAG      → project context   │
│  3. Agents   → LLM explanations  │
└──────────────────────────────────┘
```

---

## Requirements

- **Python** 3.9 or later
- **Node.js** 18 or later
- **VS Code** 1.80 or later
- **Semgrep** — installed as part of the Python dependencies
- **Groq API key** — free account at [console.groq.com](https://console.groq.com)

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd pynt
```

### 2. Set up the backend

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file at the project root:

```env
GROQ_API_KEYS=gsk_your_key_here
```

You can provide multiple comma-separated keys for automatic rotation on rate limits:

```env
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
```

Start the server:

```bash
cd server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`. You can verify it is running by visiting `http://localhost:8000/health`.

### 3. Set up the VS Code extension

Install extension dependencies and compile:

```bash
cd extension
npm install
npm run compile
```

To run the extension in development mode, open the `extension/` folder in VS Code and press **F5**. This launches a new VS Code window with the extension loaded.

To package the extension as a `.vsix` file for installation:

```bash
npm install -g @vscode/vsce
vsce package
```

Then install it via **Extensions → Install from VSIX...** in VS Code.

---

## Configuration

### Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEYS` | *(required)* | Comma-separated Groq API keys |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable debug mode |

### VS Code settings

Open **File → Preferences → Settings** and search for `pynt`:

| Setting | Default | Description |
|---------|---------|-------------|
| `pynt.serverUrl` | `http://localhost:8000` | URL of the backend server |
| `pynt.autoAnalyzeOnSave` | `false` | Automatically analyze the file on every save |
| `pynt.defaultAnalysisType` | `all` | Default analysis mode (`security`, `best_practices`, `fault_detection`, `all`) |

---

## Usage

### Running an analysis

1. Open a Python file in VS Code.
2. Right-click in the editor and select **Choose Analysis Type**, or open the Command Palette (`Ctrl+Shift+P`) and run **Pynt: Analyze File**.
3. Choose an analysis type:

   | Option | What it checks |
   |--------|----------------|
   | Security | Vulnerabilities, dangerous functions, hardcoded secrets |
   | Best Practices | Code style, readability, design principles |
   | Fault Detection | Bugs, type errors, edge cases |
   | All | All three types at once |

4. Wait for the analysis to complete. The status bar shows progress.

### Reading results

- **Red underline** — Error: a critical security or reliability issue.
- **Orange underline** — Warning: a best-practice violation.
- **Blue dotted underline** — Info: a suggestion.

Hover over any highlighted line to see a tooltip with:
- A plain-language explanation of the issue
- Why it matters (educational context)
- A suggested fix with a code example
- Links to relevant references (OWASP, CWE, Python docs)

### Applying Quick Fixes

Press `Ctrl+.` (or `Cmd+.` on macOS) on any highlighted line to trigger Pynt's smart quick-fix system. The `FixProvider` class intercepts the request and intelligently handles two cases:

#### 1. **AST Mode** — Function-level fixes
For findings on function definitions (`def` or `async def`), the fix provider:
- Extracts the **entire function scope** using AST analysis
- Preserves original decorators (e.g., `@app.route()`, `@staticmethod`)
- Inserts imports at the top of the file if needed
- Replaces the entire function with the LLM-generated corrected version
- Re-analyzes the file to confirm the fix resolved the issue

#### 2. **Line Mode** — Statement-level fixes
For single-line or multi-statement findings:
- Detects redundant lines that would be overwritten by the fix
- Prevents duplicate code by intelligently calculating how many subsequent lines to remove
- Preserves indentation and context
- Adds required imports automatically
- Validates the fix by re-running analysis

**Example**: If a hardcoded secret is on line 5 and the fix includes a config variable reference, Line Mode smartly overwrites just that statement rather than creating duplicates.

All fixes are validated by **automatic re-analysis** after application — if the finding persists, the status is marked accordingly.

### Deep Scan — Interactive Vulnerability Investigation

For deeper analysis beyond standard detections, run **Pynt: Deep Scan** from the Command Palette. This opens an **interactive WebView panel** with:

- **Multi-type baseline**: All three analysis types (security, best practices, faults) run simultaneously
- **Enhanced findings**: Each vulnerability is enriched with severity, confidence, and remediation examples
- **Code highlighting**: Source code is displayed side-by-side with findings
- **Executable fixes**: Click to apply any suggested fix directly to the editor
- **Project context**: RAG-powered retrieval shows similar patterns from your codebase

Deep Scan is ideal for:
- Discovering subtle false negatives
- Understanding cumulative risks across the file
- Learning from contextual examples in your own code

### Clearing results

Run **Pynt: Clear Diagnostics** from the Command Palette to remove all highlights and cached results.

---

## How It Works

Pynt processes each file through a three-stage pipeline: static analysis, context retrieval, and LLM explanation.

### Backend Architecture & API Routes

The backend exposes the following REST endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /analyze/security` | POST | Analyzes code for security vulnerabilities using SecurityAgent |
| `POST /analyze/best-practices` | POST | Checks code for style, readability, and design principles using BestPracticesAgent |
| `POST /analyze/fault-detection` | POST | Detects bugs and edge cases using FaultDetectionAgent |
| `POST /analyze/all` | POST | Runs all three agents in parallel and returns combined findings |
| `POST /analyze/deep-scan` | POST | Performs deep vulnerability investigation with LLM-enhanced reporting |
| `GET /health` | GET | Health check endpoint with agent and configuration status |

All analysis endpoints accept:
```json
{
  "code": "Python source code",
  "language": "python",
  "filename": "optional_filename.py",
  "projectPath": "optional path for RAG context"
}
```

### Semgrep — Static Analysis Engine

[Semgrep](https://semgrep.dev) is a fast, open-source static analysis tool that scans source code for patterns defined by rules. Pynt uses it as the foundation of every analysis.

When you trigger an analysis, Pynt:
1. Extracts the code and basic metadata (language, filename, file path).
2. Runs the Semgrep CLI with rule packs selected based on the analysis type.
3. Parses the JSON output into structured findings (line, column, severity, rule ID, message).

Semgrep provides fast and deterministic results without any LLM calls and acts as the foundation for deeper LLM-powered explanations.

**Rule packs used per analysis type:**

| Analysis type | Rule packs | Purpose |
|---------------|-----------|---------|
| Security | `p/security-audit`, `p/secrets`, `p/owasp-top-ten`, `p/sql-injection`, local rules | Hardcoded secrets, SQL injection, authentication bypasses |
| Best Practices | `p/python`, `r/python.style`, `r/python.complexity` | PEP 8 compliance, naming conventions, code simplification |
| Fault Detection | `r/python.lang.correctness`, `p/error-prone` | `NameError`, `TypeError`, mutable defaults, logic errors |

### Agent Pipeline — LLM-Powered Explanations

Each finding from Semgrep is enriched by one of three specialized agents, all inheriting from `BaseAgent`:

#### SecurityAgent
**Domain**: Security vulnerabilities and risk mitigation  
**Prompt Strategy**:
- Contextualizes the vulnerability (CWE, OWASP category)
- Explains the attack vector and potential impact
- Provides remediation code (parameterized queries, input validation, secret management)
- Generates references (OWASP, CWE, security best practices)

**Example Focus Areas**: SQL injection, hardcoded API keys, unsafe deserialization (`pickle.loads()`), command injection

#### BestPracticesAgent
**Domain**: Code quality, maintainability, and style  
**Prompt Strategy**:
- Aligns findings with PEP 8 and SOLID principles
- Explains why the pattern is considered a best practice
- Provides refactored code (list comprehensions, type hints, proper naming)
- References Python documentation and style guides

**Example Focus Areas**: Naming conventions, docstring requirements, unnecessary complexity, type hints

#### FaultDetectionAgent
**Domain**: Bugs, runtime errors, and edge cases  
**Prompt Strategy**:
- Identifies the root cause of the potential fault
- Explains when and why the code would fail at runtime
- Provides defensive code (null checks, exception handling, resource cleanup)
- Demonstrates safe patterns

**Example Focus Areas**: `NameError`, `TypeError`, mutable default arguments, unhandled exceptions, file handle leaks

#### BaseAgent Execution Flow
```
Semgrep Finding
     ↓
RAG Retrieval (semantic search over project codebase)
     ↓
Agent-specific prompt construction (finding + code + RAG context)
     ↓
Groq LLM API call (LLaMA-3.3-70b-versatile)
     ↓
LLM Response Parser:
  • EXPLANATION       → Educational plain-language description
  • APPLICABLE_FIX    → Executable code (IMPORTS + FIX sections)
  • CODE_EXAMPLE      → Before/after demonstration
  • REFERENCES        → Links to CWE/OWASP/docs
  • FALSE_POSITIVE    → Confidence flag (true/false)
     ↓
Finding object enriched and returned to extension
```

Findings are processed in parallel (up to 5 concurrently) for fast turnaround. Groq API keys rotate automatically on rate-limit errors (HTTP 429).

### Deep Scan — Vulnerability Investigation

The `/analyze/deep-scan` endpoint provides a dedicated investigative mode for finding false negatives and subtle vulnerabilities:

1. **Multi-Type Baseline**: Runs all three agent types against the code to establish known findings
2. **RAG Enhancement**: Retrieves similar code patterns from the project for deeper context
3. **LLM Investigation**: Sends findings + RAG context to the LLM for edge-case analysis
4. **JSON Report**: Returns a structured report with detailed vulnerability metadata and remediation steps
5. **WebView Visualizer**: The extension renders the report in an interactive panel with syntax highlighting and code exploration

The Deep Scan output includes severity, confidence, code location, and executable fix suggestions for each discovery.

### RAG Quality Evaluation with RAGAS

Pynt includes automated **RAG pipeline evaluation** using [RAGAS](https://docs.ragas.io/) (Retrieval-Augmented Generation Assessment), a framework for measuring retrieval and generation quality.

**What RAGAS measures:**

| Metric | What it evaluates | Threshold |
|--------|------------------|----------|
| **Context Precision** | How relevant the retrieved code chunks are to the query | > 0.5 |
| **Answer Relevancy** | How well the LLM answer addresses the question | > 0.65 |
| **Faithfulness** | Whether the LLM stays faithful to the retrieved context | > 0.7 |
| **Context Recall** | How much of the necessary context was retrieved | > 0.4 |

**Running RAG tests:**

Offline retrieval-only (no API keys required):

```bash
pytest tests/test_rag_retrieval_offline.py -v
# or by marker
pytest -m rag_offline -v
```

Online RAGAS evaluation (requires Groq keys):

```bash
RUN_RAG_EVALUATION=1 pytest tests/test_rag_evaluation_online.py -v
# or by marker
RUN_RAG_EVALUATION=1 pytest -m rag_online -v
```

This test:
1. Runs a set of evaluation queries (both conceptual and code-specific)
2. Retrieves context from the RAG index
3. Generates answers using the LLM
4. Computes all four RAGAS metrics
5. Validates against quality thresholds

**Note**: Code-based RAG typically scores 10-20% lower on relevancy metrics compared to text-based RAG, so thresholds are adjusted accordingly.

The evaluation uses the same production pipeline (RAGService + ChatGroq) that powers the actual analysis, ensuring realistic quality measurement.


---

## Project Structure

```
pynt/
├── extension/                  # VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts        # Activation, commands, event listeners
│   │   ├── analyzer.ts         # HTTP client for backend requests
│   │   ├── decorators.ts       # Visual highlighting of findings
│   │   ├── deepScanProvider.ts # WebView for deep scan reports
│   │   ├── FixProvider.ts      # Quick fix implementation (Ctrl+.)
│   │   ├── codeActions.ts      # Code action dispatch logic
│   │   └── types.ts            # Shared TypeScript interfaces
│   ├── views/
│   │   └── deep_scan_report.html # Deep scan WebView template
│   └── package.json
│
├── server/                     # Python FastAPI backend
│   ├── main.py                 # API routes (/analyze/*, /health)
│   ├── agents/
│   │   ├── base_agent.py       # Core agent pipeline & LLM integration
│   │   ├── security_agent.py
│   │   ├── bestpractices_agent.py
│   │   └── fault_agent.py
│   ├── analyzers/
│   │   ├── semgrep_analyzer.py # Semgrep CLI wrapper
│   │   └── rules/
│   │       └── python_rules.yaml # Local rule definitions
│   ├── service/
│   │   └── rag_service.py      # FAISS vector index & retrieval
│   ├── config/
│   │   └── settings.py         # Configuration & environment
│   └── models/
│       └── schemas.py          # Pydantic models & type contracts
│
├── tests/                      # Test suite
│   ├── test_security_analysis.py
│   ├── test_diagnostic_validation.py
│   ├── test_langchain_smoke.py      # LangChain component validation
│   ├── test_rag_evaluation.py       # RAGAS quality metrics
│   └── fixtures/
│
├── requirements.txt
└── README.md
```

---

## Technology Stack

### Backend (Python)

| Category | Technology | Version | Purpose |
|----------|-----------|---------|--------|
| **Framework** | FastAPI | 0.115.12 | REST API and async request handling |
| **Static Analysis** | Semgrep | 1.98.0 | Pattern-based code scanning |
| **LLM Provider** | Groq | - | Fast inference API (LLaMA-3.3-70b) |
| **LLM Integration** | LangChain | 1.1.2 | Agent orchestration and prompt management |
| **LLM Client** | langchain-groq | 1.1.1 | Groq API wrapper with async support |
| **Vector Store** | FAISS | 1.13.2 | Efficient similarity search for RAG |
| **Embeddings** | HuggingFace Transformers | 4.57.2 | all-MiniLM-L6-v2 embedding model |
| **Document Loading** | langchain-community | 0.4.1 | DirectoryLoader, TextLoader, text splitting |
| **RAG Evaluation** | RAGAS | 0.2.10 | Context relevancy, faithfulness, recall metrics |
| **Schema Validation** | Pydantic | 2.10.6 | Request/response models and configuration |
| **Testing** | pytest | 9.0.2 | Unit, integration, and evaluation tests |

### Extension (TypeScript)

| Category | Technology | Version | Purpose |
|----------|-----------|---------|--------|
| **Runtime** | Node.js | 18+ | JavaScript execution environment |
| **Editor API** | VS Code Extension API | 1.80+ | Diagnostics, decorators, quick fixes, WebView |
| **HTTP Client** | Node.js fetch | Built-in | Backend communication |
| **Language** | TypeScript | 5.7.2 | Type-safe extension development |
| **Linting** | ESLint | 9.17.0 | Code quality enforcement |
| **Build** | tsc (TypeScript Compiler) | 5.7.2 | Compilation to JavaScript |

### Infrastructure & Deployment

| Component | Technology | Purpose |
|-----------|-----------|--------|
| **Process Management** | uvicorn | ASGI server for FastAPI |
| **API Key Management** | python-dotenv | Environment variable loading with priority |
| **Caching** | Disk-based FAISS persistence | `.rag_cache/` directory with hash-based keys |
| **Version Control** | Git | Source control and collaboration |
| **Package Management** | pip (Python), npm (Node.js) | Dependency management |

### Key Design Choices

**Why Groq?**  
Groq provides extremely fast inference (up to 10x faster than standard cloud LLM APIs) with competitive quality, making real-time code analysis feasible.

**Why FAISS?**  
FAISS (Facebook AI Similarity Search) is optimized for billion-scale vector search with minimal memory footprint and supports disk persistence.

**Why LangChain?**  
LangChain provides standardized interfaces for RAG pipelines (loaders, splitters, retrievers) and simplifies LLM provider switching.

**Why Semgrep?**  
Semgrep is fast, deterministic, and has extensive rule packs for security vulnerabilities, making it ideal as a first-pass filter before expensive LLM calls.

**Why FastAPI?**  
FastAPI provides async request handling, automatic OpenAPI documentation, and built-in Pydantic validation for type-safe APIs.
```
