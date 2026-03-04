# Strategia di Test v2 - Quick Start

## Panoramica
Questa directory contiene **infrastruttura test formalizzata** per validare la pipeline diagnostica di Pynt (detection Semgrep + arricchimento LLM) contro ground truth.

**File Chiave:**
- `ground_truth.json` – Manifesto dataset con detection rule attese per file
- `test_diagnostic_validation.py` – Hard/soft assertions e governance checks
- `metrics.py` – Computazione Precision/recall/F1 e regression tracking
- `STRATEGY_TEST_V2.md` – Documento estrategia completo (obiettivi, KPI, roadmap)

---

## Quick Start

### 1. Validare Ground Truth (No Dependencies)
Esegui hard assertions per verificare integrità dataset:

```bash
cd pynt/tests
pytest test_diagnostic_validation.py::TestDeterministicDetection -v
```

**Output Atteso (22 check):**
```
TestDeterministicDetection::test_ground_truth_exists PASSED
TestDeterministicDetection::test_ground_truth_schema PASSED
TestDeterministicDetection::test_reviewed_cases_count PASSED
TestDeterministicDetection::test_file_exists[aa.py] PASSED
...
TestDeterministicDetection::test_rule_catalog_referenced PASSED
======================== 22 passed in 0.45s ========================
```

### 2. Verificare Copertura & Gap
Rivedi quali regole sono effettivamente nel catalogo vs. dataset needs:

```bash
pytest test_diagnostic_validation.py::TestDetectionCoverage -v -s
pytest test_diagnostic_validation.py::TestCatalogGaps -v -s
```

**Sample Output:**
```
=== Detection Coverage ===
Files with expected rules: 12/19
Coverage: 63.2%
  pynt-manual-secrets: 11 files
  pynt-sql-injection-hardcore: 1 files

=== Catalog Gaps ===
command_injection_via_os_system:
  Description: No rule for os.system() with f-strings or string concatenation
  Files affected: 15 files
  Priority: HIGH
  Suggested rule: pynt-command-injection-os-system
```

### 3. Inizializzare Baseline Metrics
(Richiede server Pynt live in esecuzione, vedi Phase 2)

```bash
# Computa e salva metriche attuali come baseline
python metrics.py --run-pynt --set-baseline

# Più tardi, compara nuove esecuzioni contro baseline
python metrics.py --run-pynt --compare-baseline
```

---

## Struttura Test

### Layer 1: Deterministic (Hard) Assertions
✅ **Sempre eseguiti** (no dipendenze, <1s)

Valida:
- JSON schema ground truth
- Esistenza file
- Rule catalog references
- Review status counts
- Campi governance (adjudication notes)

```python
pytest test_diagnostic_validation.py::TestDeterministicDetection -v
pytest test_diagnostic_validation.py::TestGovernance -v
```

### Layer 2: Generative (Soft) Assertions
⏸️ **Skipped** (richiede integrazione con Pynt server live)

Valida (quando implementato):
- Schema API response (AnalysisResponse → Finding)
- LLM section parseability (EXPLANATION, SUGGESTED_FIX, ecc.)
- Message field non-empty
- Code examples presenti

```bash
pytest test_diagnostic_validation.py::TestSoftAssertions -v -s
# Attualmente skipped; sarà eseguito quando integrazione Pynt API completa
```

### Layer 3: Regression Tests
⏸️ **Baseline-only** (esegui dopo grandi cambiamenti)

Valida:
- Metriche detection vs. baseline (precision/recall/F1)
- False positives non aumentati
- False negatives non aumentati

```bash
python metrics.py --compare-baseline
# Gate: |delta| < 0.05 su precision/recall
```

---

## Dataset Ground Truth

### Statistiche
```
File totali: 19
File con expected rules (reviewed): 12
File con expected rules (draft): 0
File senza rules (draft - catalog gaps): 7

Distribuzione Rule:
  pynt-manual-secrets: 11 file
  pynt-sql-injection-hardcore: 1 file
  (17 file hanno detected vulnerabilità non coperte dal catalogo)
```

### Riepilogo File

| File | Expected Rules | Review Status | Note |
|------|---|---|---|
| aa.py | pynt-sql-injection-hardcore | reviewed | SQL injection via concatenation |
| bb.py | (none - % formatting) | reviewed | SQL injection ma pattern unmatched |
| c1.py | pynt-manual-secrets | reviewed | Hardcoded SECRET_TOKEN |
| c2.py | pynt-manual-secrets | reviewed | DB_PASSWORD |
| c3.py | pynt-manual-secrets | reviewed | ADMIN_PASSWORD |
| c4.py | (none - catalog gap) | draft | SUPER_SECRET_KEY - TOKEN variant non coperto |
| c5.py | (none - catalog gap) | draft | STATION_ACCESS_TOKEN - TOKEN variant |
| c6.py–c10.py | pynt-manual-secrets | reviewed | Vari PASSWORD hardcodes |
| c11.py | pynt-manual-secrets | reviewed | ADMIN_PASSWORD |
| c12.py | (none - catalog gap) | draft | SECRET_KEY - KEY variant non coperto |
| c13.py | pynt-manual-secrets | reviewed | ADMIN_PASSWORD |
| c14.py | pynt-manual-secrets | reviewed | MASTER_PASSWORD |
| c15.py | (none - catalog gap) | draft | ADMIN_SECRET - ADMIN_* variant |
| c16.py | (none - catalog gap) | draft | subprocess.run with shell=True (no rule) |
| c17.py | pynt-manual-secrets | reviewed | ADMIN_PASSWORD + subprocess |

**Key:** reviewed = high confidence, draft = awaiting catalog expansion (es. new rules per CMDi, YAML deserialization)

---

## Esecuzione Test

### Esegui tutto
```bash
cd pynt/tests
pytest -v
```

### Esegui per layer
```bash
# Hard assertions only (veloce, sempre sicuro)
pytest test_diagnostic_validation.py::TestDeterministicDetection -v

# Coverage analysis
pytest test_diagnostic_validation.py::TestDetectionCoverage -v -s

# Governance review
pytest test_diagnostic_validation.py::TestGovernance -v

# Soft assertions (skipped, richiede integrazione)
pytest test_diagnostic_validation.py::TestSoftAssertions -v -s
```

### Esegui con coverage
```bash
pytest --cov=pynt.Security_test --cov-report=html
```

---

## Metrics & Regression

### Compute Current Metrics
(Placeholder: requires live Pynt execution)

```bash
python metrics.py --run-pynt
```

**Sample Output:**
```
======================================================================
PYNT DETECTION METRICS REPORT
======================================================================
Generated: 2026-03-03T10:45:23.456789

AGGREGATE METRICS
------================================================================
Precision: 0.850
Recall: 0.900
F1 Score: 0.875

True Positives: 9
False Positives: 1
False Negatives: 1
Total Expected: 10
Total Detected: 10

PER-FILE BREAKDOWN
----------------------------------------------------------------------
REVIEWED CASES (12):
  aa.py
    Expected: ['pynt-sql-injection-hardcore']
    Detected: ['pynt-sql-injection-hardcore']

  c1.py
    Expected: ['pynt-manual-secrets']
    Detected: ['pynt-manual-secrets']
  ...

DRAFT CASES (7) - Known catalog gaps:
  c4.py
    Expected: [] (pending catalog expansion - TOKEN variant)
  ...
```

### Set Baseline
```bash
python metrics.py --set-baseline
# Saves snapshot of current metrics to .test_results/baseline.json
```

### Compare Against Baseline
```bash
python metrics.py --compare-baseline
# ✅ Regression test PASSED if precision/recall deltas < ±0.05
# ❌ Regression test FAILED if significant regression detected
```

---

## Catalog Gaps & Roadmap

### HIGH Priority (Blocks 15+ files)
1. **Create rule `pynt-command-injection-os-system`**
   - Pattern: `os.system(f"...")` or `os.system("..." + ...)`
   - Affects: 15 files (c1–c15)
   - Severity: ERROR

2. **Create rule `pynt-yaml-unsafe-deserialization`**
   - Pattern: `yaml.load(..., Loader=yaml.FullLoader|yaml.Loader)` or default
   - Affects: 17 files (c1–c17)
   - Severity: ERROR

### MEDIUM Priority
3. **Expand `pynt-sql-injection-hardcore`** to cover `"%s" % user_input`
   - Affects: 1 file (bb.py)

4. **Expand `pynt-manual-secrets`** regex to include `.*_(TOKEN|SECRET|KEY)`
   - Affects: 5 files (c1, c4, c5, c12, c15)

5. **Create rule `pynt-command-injection-subprocess`**
   - Pattern: `subprocess.run(..., shell=True)` with f-string/concat
   - Affects: 2 files (c16–c17)

---

## Criteri di Successo

### Phase 1 (Attuale- Completata ✅)
- [x] Ground truth creato (12 reviewed, 7 draft)
- [x] Hard assertions scritti (22 check)
- [x] Framework metriche pronto
- [x] Gap catalogo documentati

### Phase 2 (Prossima - Integrazione)
- [ ] Esegui live Pynt su Security_test
- [ ] Misura detection (expected precision ≥0.80, recall ≥0.85)
- [ ] Hard assertions pass 100%
- [ ] Baseline metriche stabilito

### Phase 3 (Futuro - Soft Assertions)
- [ ] LLM section parsing funzionante (≥95% success)
- [ ] API contract validation 100% pass
- [ ] Soft assertions abilitate

### Phase 4 (Futuro - Catalog Expansion)
- [ ] Command injection rule implementato
- [ ] YAML deserialization rule implementato
- [ ] Copertura → 17+/19 file
- [ ] Recall → ≥0.90

---

## Risoluzione Problemi

### Errore ground truth non trovato
```
FileNotFoundError: Ground truth not found at pynt/Security_test/ground_truth.json
```
**Soluzione:** Esegui da directory root `pynt/` o aggiorna path nel file test.

### Errore baseline metriche non trovato
```
FileNotFoundError: Baseline not found at .../.test_results/baseline.json
```
**Soluzione:** Esegui `python metrics.py --run-pynt --set-baseline` prima di stabilire baseline.

### Errore server Pynt non in esecuzione (integration tests)
```
ConnectionError: Could not connect to http://localhost:8000
```
**Soluzione:** Start Pynt server: `uvicorn pynt.server.main:app --reload`

---

## Contatti & Domande

Riferisciti a [STRATEGY_TEST_V2.md](../STRATEGY_TEST_V2.md) per dettagli strategia completa.
