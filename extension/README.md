# Pynt — VS Code Extension

The Pynt extension is a lightweight TypeScript client that communicates with the Python FastAPI backend to deliver real-time code analysis, diagnostics, and interactive fix suggestions directly in your editor.

## Features

- ✅ **Real-time Analysis** — Analyze any Python file for security, best practices, and bug detection
- ✅ **Smart Quick Fixes** — Apply LLM-suggested fixes with two intelligent modes (AST and Line)
- ✅ **Interactive Deep Scan** — Visualize vulnerabilities in a WebView with context and remediation examples
- ✅ **Diagnostic Highlighting** — Color-coded underlines (error, warning, info) with hover tooltips
- ✅ **Project-aware Context** — Optional RAG integration for project-specific insights
- ✅ **Auto-Analysis** — Optionally analyze files automatically on save

## How to Use

### Running an Analysis

1. Open any Python file in VS Code
2. Press `Ctrl+Shift+P` and select **Pynt: Analyze File**, or right-click and choose **Choose Analysis Type**
3. Select an analysis type:
   - **Security** — Detects hardcoded secrets, SQL injection, insecure deserialization
   - **Best Practices** — Checks PEP 8 compliance, naming conventions, code optimization
   - **Fault Detection** — Finds runtime errors, type mismatches, edge cases
   - **All** — Runs all three types in parallel

4. Wait for the status bar to show "Analysis complete"

### Reading Diagnostics

The extension decorates your code with visual indicators:

- 🔴 **Red underline (Error)** — Critical security or reliability issue
- 🟠 **Orange underline (Warning)** — Best-practice violation
- 🔵 **Blue dotted underline (Info)** — Suggestion or optimization

**Hover over any underline** to see a rich tooltip containing:
- Plain-language explanation of the issue
- Educational context about why it matters
- A suggested fix with a code example
- Links to relevant references (OWASP, CWE, Python docs)

### Applying Quick Fixes

Press `Ctrl+.` on any highlighted line to see available quick fixes:

#### **AST Mode** (for function-level fixes)
- Detects when the finding is inside a function definition
- Preserves decorators (e.g., `@app.route()`, `@staticmethod`)
- Replaces the entire function while maintaining its context
- Auto-adds required imports

#### **Line Mode** (for statement-level fixes)
- Intelligently detects and removes redundant lines that would be overwritten
- Applies the fix to the problematic statement
- Preserves surrounding code and indentation
- Auto-adds required imports

All fixes are validated by **automatic re-analysis** after application.

### Deep Scan — Interactive Investigation

Press `Ctrl+Shift+P` and select **Pynt: Deep Scan** to open an interactive WebView panel:

- **Enhanced Vulnerability Report** — Lists all findings with severity, confidence, and context
- **Source Code Display** — Side-by-side view of your code with findings highlighted
- **Executable Fixes** — Click any suggested fix to apply it directly to your editor
- **Project Context** — RAG-retrieved similar patterns from your codebase
- **Multi-type Analysis** — All three analysis types run simultaneously for comprehensive coverage

**Use Deep Scan when:**
- You want to investigate subtle or edge-case vulnerabilities
- You need a comprehensive report of all issues in a file
- You want to see how similar patterns appear elsewhere in your project

### Auto-Analysis on Save

Enable **`pynt.autoAnalyzeOnSave`** in VS Code settings to automatically run analysis every time you save a file.

### Clearing Results

Run **Pynt: Clear Diagnostics** from the Command Palette to remove all highlights and cached results for the active file.

---

## Configuration

Open **File → Preferences → Settings** and search for `pynt`:

| Setting | Default | Type | Description |
|---------|---------|------|-------------|
| `pynt.serverUrl` | `http://localhost:8000` | string | URL of the Pynt backend server |
| `pynt.autoAnalyzeOnSave` | `false` | boolean | Automatically analyze on every save |
| `pynt.defaultAnalysisType` | `all` | enum | Default analysis mode (`security`, `best_practices`, `fault_detection`, `all`) |

---

## Diagnostic Management

The extension manages diagnostics through the `DiagnosticDecorator` class:

### Visual Representation

For each finding, the decorator:
1. **Groups findings by line** — Multiple findings on the same line are combined into a single decoration
2. **Applies color-coded borders** — Red (error), orange (warning), blue (info)
3. **Adds hover messages** — Clicking reveals all findings for that line with full details
4. **Shows issue count** — Displays "(n issues)" as a label when multiple findings are on one line

### Diagnostic Collection

- Each analysis request clears and repopulates the diagnostics for the active file
- Findings are keyed by line number to avoid duplicates
- Diagnostics persist until a new analysis runs or **Clear Diagnostics** is invoked
- The `diagnosticFixMap` class global maps diagnostics to their LLM-generated fix code

### Update Flow

```
User triggers analysis
     ↓
extension.ts → analyzer.ts (HTTP POST to backend)
     ↓
Backend returns findings
     ↓
decorators.ts → DiagnosticDecorator.applyDecorations()
     ↓
Findings grouped, colored, and displayed
     ↓
FixProvider registers fixes for interactive application
```

---

## Extension Architecture

```
extension/
│
├── src/
│   ├── extension.ts
│   │   └── Entry point; registers commands:
│   │       - Pynt: Analyze File
│   │       - Pynt: Clear Diagnostics
│   │       - Pynt: Deep Scan
│   │       - Choose Analysis Type
│   │
│   ├── analyzer.ts
│   │   └── HTTP client for backend communication
│   │       - POST /analyze/security
│   │       - POST /analyze/best-practices
│   │       - POST /analyze/fault-detection
│   │       - POST /analyze/all
│   │       - POST /analyze/deep-scan
│   │
│   ├── decorators.ts
│   │   └── DiagnosticDecorator class
│   │       - Applies color-coded underlines
│   │       - Groups findings by line
│   │       - Generates hover messages
│   │       - Caches decorations
│   │
│   ├── FixProvider.ts
│   │   └── CodeActionProvider implementation
│   │       - AST Mode: Function-level fixes
│   │       - Line Mode: Statement-level fixes
│   │       - Smart redundancy detection
│   │       - Auto-import insertion
│   │       - Post-fix re-analysis
│   │
│   ├── deepScanProvider.ts
│   │   └── WebView management for Deep Scan
│   │       - Creates interactive panel
│   │       - Sends analysis request to backend
│   │       - Passes full response data to WebView
│   │       - Error handling & progress indication
│   │
│   ├── codeActions.ts
│   │   └── Code action dispatch logic
│   │       - Routes quick-fix requests
│   │       - Invokes FixProvider
│   │
│   └── types.ts
│       └── Shared TypeScript interfaces
│           - Finding, SeverityLevel, AnalysisType
│           - AnalysisRequest, AnalysisResponse
│
├── views/
│   └── deep_scan_report.html
│       └── Interactive WebView template
│           - Renders vulnerability report
│           - Displays source code with highlights
│           - Provides fix application UI
│           - Shows project context & references
│
├── test/
│   └── extension.test.ts
│       └── Basic extension tests
│
├── package.json
│   └── Extension manifest
│       - Commands, keybindings
│       - Configuration contribution points
│       - Activation events
│
├── tsconfig.json
│   └── TypeScript configuration
│
└── eslint.config.mjs
    └── Linting rules
```

## Development

### Building the Extension

```bash
cd extension
npm install
npm run compile
```

### Running in Development Mode

Press **F5** in VS Code to launch the extension in a new window with debugging enabled.

### Linting

```bash
npm run lint
```

### Testing

```bash
npm test
```

---

## Requirements

- **VS Code** 1.80 or later
- **Python backend** running at configured server URL (default: `http://localhost:8000`)
- **Groq API keys** configured in the backend `.env` file

## Known Limitations

- Currently supports **Python** files only
- Deep Scan works best with project paths for RAG context
- Quick fixes are generated by LLM and may require manual review in complex cases

---

## Tips & Best Practices

1. **Use Project Path** — Configure `pynt.serverUrl` with a valid project path for RAG-enhanced analysis
2. **Review Fixes** — While quick fixes are usually accurate, always review the suggested changes
3. **Combine Analysis Types** — Run "All" analysis periodically for comprehensive coverage
4. **Use Deep Scan for Learning** — Deep Scan shows context from your own codebase, making it a great learning tool
5. **Auto-Analysis** — Enable auto-analysis on save for continuous feedback during development

---

For more details, see the [main README](../README.md).

