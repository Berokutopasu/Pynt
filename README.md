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

### Applying quick fixes

Press `Ctrl+.` on any highlighted line. If an automatic fix is available, a **Quick Fix** option will appear. Selecting it will:

1. Insert any required imports at the top of the file.
2. Replace the problematic code with the corrected version.
3. Automatically re-run the analysis to confirm the issue is resolved.

### Clearing results

Run **Pynt: Clear Diagnostics** from the Command Palette to remove all highlights and cached results.

---

## How It Works

Pynt processes each file through a three-stage pipeline: static analysis, context retrieval, and LLM explanation.

### Semgrep — Static Analysis Engine

[Semgrep](https://semgrep.dev) is a fast, open-source static analysis tool that scans source code for patterns defined by rules. Pynt uses it as the first stage of the pipeline.

When you trigger an analysis, Pynt:
1. Writes the code to a temporary file.
2. Runs the Semgrep CLI with a set of rule packs selected based on the analysis type.
3. Parses the JSON output into structured findings (line, column, severity, rule ID, message).

Semgrep provides fast and deterministic results without any LLM calls. It catches well-defined vulnerabilities and patterns reliably and acts as the foundation for the deeper explanations that follow.

**Rule packs used per analysis type:**

| Analysis type | Semgrep rule packs |
|---------------|--------------------|
| Security | `p/security-audit`, `p/secrets`, `p/owasp-top-ten`, `p/sql-injection` |
| Best Practices | `p/python`, `r/python.style`, `r/python.complexity` |
| Fault Detection | `r/python.lang.correctness`, `p/error-prone` |

### RAG Service — Retrieval-Augmented Generation

The RAG (Retrieval-Augmented Generation) service enriches LLM prompts with code from your own project, making explanations more relevant and accurate.

**How it works:**

1. **Indexing**: When you provide a project path, Pynt scans the directory and loads all source files. Each file is split into overlapping chunks (1000 tokens, 100-token overlap) and embedded using the HuggingFace model `all-MiniLM-L6-v2`. The embeddings are stored in a **FAISS** vector index. This step runs locally — no API calls are made.

2. **Retrieval**: When the LLM is about to explain a Semgrep finding, the RAG service performs a semantic similarity search in the FAISS index using the finding's message as the query (e.g., "SQL sanitization validation"). It returns the top-40 most relevant code snippets from your project.

3. **Augmentation**: The retrieved snippets are injected into the LLM prompt as additional context, so the model can reason about how the issue appears in your specific codebase, not just in the abstract.

The RAG service caches the index per project path to avoid re-indexing on every request.

### Agents — LLM-powered Explanation Pipeline

Pynt uses three specialized agents, each focused on a different domain:

| Agent | Domain | Focus areas |
|-------|--------|-------------|
| `SecurityAgent` | Security vulnerabilities | SQL injection, XSS, CSRF, `eval()`, `pickle.loads()`, hardcoded secrets |
| `BestPracticesAgent` | Code quality | PEP 8, naming, SOLID/DRY, type hints, docstrings, list comprehensions |
| `FaultDetectionAgent` | Bug detection | `NameError`, `TypeError`, mutable defaults, file handle leaks, race conditions |

All three agents inherit from `BaseAgent`, which orchestrates the full pipeline for each Semgrep finding:

```
Semgrep finding
     ↓
RAG context retrieval (semantic search over project code)
     ↓
LLM prompt construction (finding + code snippet + RAG context)
     ↓
Groq API call (LLaMA-3.3-70b-versatile)
     ↓
Parse LLM response:
  - EXPLANATION     → plain-language description
  - SUGGESTED_FIX   → textual recommendation
  - APPLICABLE_FIX  → executable code (IMPORTS + FIX sections)
  - CODE_EXAMPLE    → before/after snippet
  - REFERENCES      → links to OWASP, CWE, docs
     ↓
Finding object returned to extension
```

Findings are processed in parallel (up to 5 concurrently) to keep analysis time low. If multiple Groq API keys are configured, the agent rotates automatically on rate-limit errors (HTTP 429).

---

## Project Structure

```
pynt/
├── extension/                  # VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts        # Activation, commands, event listeners
│   │   ├── analyzer.ts         # HTTP client for backend requests
│   │   ├── decorators.ts       # Visual highlighting of findings
│   │   ├── FixProvider.ts      # Quick fix implementation (Ctrl+.)
│   │   └── types.ts            # Shared TypeScript interfaces
│   └── package.json
│
├── server/                     # Python FastAPI backend
│   ├── main.py                 # API routes and server startup
│   ├── agents/
│   │   ├── base_agent.py       # Core pipeline logic
│   │   ├── security_agent.py
│   │   ├── bestpractices_agent.py
│   │   └── fault_agent.py
│   ├── analyzers/
│   │   ├── semgrep_analyzer.py
│   │   └── rules/              # Custom Semgrep rules (optional)
│   ├── service/
│   │   └── rag_service.py
│   ├── config/
│   │   └── settings.py
│   └── models/
│       └── schemas.py
│
├── requirements.txt
└── README.md
```
