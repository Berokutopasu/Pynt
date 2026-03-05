# Copilot Instructions for Pynt

These instructions apply to the whole workspace.

## Project Context

Pynt is composed of two tightly coupled parts:
- `server/`: FastAPI backend (Python) that runs Semgrep, RAG retrieval, and LLM-based explanation/fix generation.
- `extension/`: VS Code extension (TypeScript) that calls backend APIs, renders diagnostics, and applies quick fixes.

Main goal: keep the backend-extension contract stable while iterating quickly on analysis quality.

## High Priority Rules

1. Preserve API and schema compatibility unless explicitly requested.
2. Prefer minimal and local edits over broad refactors.
3. Do not remove existing behavior in async pipeline, key rotation, or fallback logic without a clear reason.
4. Keep fixes executable and business-logic-safe.

## Backend Contract (Do Not Break)

When editing `server/`, preserve these contracts:

- Endpoints in `server/main.py`:
  - `POST /analyze/security`
  - `POST /analyze/best-practices`
  - `POST /analyze/fault-detection`
  - `POST /analyze/all`
  - `GET /health`

- Request model fields (`AnalysisRequest`):
  - `code`, `language`, `filename`, `projectPath`, `analysisTypes`

- `Finding` model key fields used by extension:
  - `line`, `column`, `endLine`, `endColumn`, `severity`, `message`
  - `educationalExplanation`, `suggestedFix`, `executableFix`, `codeExample`
  - `references`, `analysisType`, `ruleId`, `isFalsePositive`, `file_path`

- `AnalysisType` values must remain:
  - `security`, `best_practices`, `fault_detection`

## LLM Output and Parsing Rules

When modifying `BaseAgent` prompt/parsing logic:

- Keep parser resilient to malformed markdown and partial sections.
- Keep `APPLICABLE_FIX` extraction stable and safe.
- `executableFix` must be code-only (no prose, no markdown wrappers).
- If no valid fix is available, return `None` instead of unsafe text.
- Preserve false-positive extraction (`FALSE_POSITIVE: true|false`).

## Quick Fix Safety Rules

When generating or applying automatic fixes:

- Keep changes minimal and targeted to the vulnerable block.
- Preserve existing business logic and data flow.
- Add imports only if strictly required and not already present.
- Never inject comments inside executable fix payload.
- Ensure Python indentation is correct in generated fix code.

## RAG and Deep Scan Rules

- Do not remove project-path-based RAG ingestion and retrieval flow.
- Keep deep scan JSON response machine-parseable.
- If JSON parsing fails, keep robust fallback and return safe empty structures.

## Extension Rules

When editing `extension/`:

- Keep command IDs stable:
  - `pynt.showAnalysisMenu`
  - `pynt.analyzeFile`
  - `pynt.clearDiagnostics`
  - `pynt.toggleAutoAnalysis`
- Keep configuration keys stable:
  - `pynt.serverUrl`
  - `pynt.autoAnalyzeOnSave`
  - `pynt.defaultAnalysisType`

## Testing and Validation

Before closing a change, run what is relevant:

- Backend tests from repo root:
  - `pytest -v`
- Deterministic diagnostic checks:
  - `pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v`
- Extension build checks:
  - `cd extension && npm run compile`
  - `cd extension && npm run lint`

If a full run is too heavy, run at least the nearest targeted test and report what was not executed.

## Code Style and Change Discipline

- Follow existing style in each folder; do not reformat unrelated files.
- Add concise comments only where logic is non-obvious.
- Keep logs useful for debugging but avoid noisy or sensitive output.
- Avoid adding new dependencies unless required.

## Security and Secrets

- Never hardcode real keys or tokens.
- Keep `.env` usage and key rotation behavior intact.
- Prefer defensive fallbacks over crashing behavior in analysis paths.

## Typical Safe Workflow for Changes

1. Identify whether change affects backend contract, extension contract, or both.
2. Implement smallest viable patch.
3. Validate parser/output shape for findings.
4. Run targeted tests/build.
5. Summarize behavior impact and remaining risks.
