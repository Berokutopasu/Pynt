# Strategia di Test Pynt - Validazione completa pipeline Semgrep + LLM

**Versione:** 2.1 Aggiornata (Direct Python Execution)  
**Data:** 2026-03-05  
**Scope:** Validazione della pipeline diagnostica Semgrep + LLM per il frontend  
**Dataset Obiettivo:** pynt/Security_test (19 file Python)

---

## 📌 Aggiornamenti Recenti (v2.0 → v2.1)

✅ **Semgrep-only execution**: Rimosso tutte le chiamate LLM per metrics collection  
✅ **No API calls**: Nessuna dipendenza da Groq API durante i test  
✅ **Direct imports**: `SemgrepAnalyzer` eseguito direttamente senza agenti  
✅ **Semplificazione**: Ridotte da 5 fasi a 4 fasi (merged Phase 2-3)  

---

## Quick Start (3 Passaggi)

### 1. Validazione Ground Truth & Schema
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
# Output atteso: 23 passed (schema, file count, rule refs)
```

### 2. Validazione Detection Regole & Metriche
```bash
pytest tests/test_security_analysis.py -v
# Test per-file detection, metriche aggregate (Precision/Recall/F1)
# Output: Numeri di TP, FP, FN per ogni file
```

### 3. Validazione Struttura LLM & Sezioni
```bash
pytest tests/test_detector_integration.py -v
# Valida Finding schema, sezioni educativeExplanation, false positive field
# Output: Conformità schema, sezioni LLM presenti, false positive detection
```

---

## Panoramica Strategia

La test strategy si articola su **3 livelli** (deterministic, generative, regression) su 19 file Python con 12 casi reviewed (alta fiducia) e 7 draft (gap catalogo noti).

| Aspetto | Dettaglio |
|---------|-----------|
| **Unit di Test** | Per-file (non per-location) |
| **Ground Truth** | expected_rule_ids (Semgrep rules) |
| **Metriche** | Precision/Recall/F1 su casi reviewed |
| **Obiettivi** | Recall ≥0.85, Precision ≥0.80, F1 ≥0.82 |
| **Target** | Nessuna regressione tra rilasci (±5%) |

---

## 1. Obiettivi & Criteri Successo

### Obiettivi Primari
- **Validare l'accuratezza della detection**: Misurare precision/recall della detection Semgrep contro ground truth
- **Validare il contratto diagnostico**: Assicurare che le risposte API conformi allo schema (AnalysisResponse → Finding)
- **Tracciare regressioni**: Stabilire metriche di baseline e rilevare degradazione tra versioni di regole/prompt/modello
- **Documentare gap**: Identificare regole mancanti nel catalogo e pianificare roadmap

### Criteri di Successo
- **Detection**: Recall ≥ 0.85, Precision ≥ 0.80, F1 ≥ 0.82 (su casi reviewed)
- **Contratto**: Conformità 100% con validazione schema API
- **Parseabilità LLM**: ≥ 95% success rate per sezioni diagnostiche (FALSE_POSITIVE, EXPLANATION, SUGGESTED_FIX, ecc.)
- **Regressione**: Nessuna regressione nelle metriche tra rilasci (tolleranza: ±0.05 su precision/recall)

---

## 2. Dataset & Taxonomy

### Test Dataset
- **Location**: `pynt/Security_test/`
- **Size**: 19 Python files (aa.py, bb.py, c1.py–c17.py)
- **Composition**:
  - 11 files with hardcoded secrets (pynt-manual-secrets)
  - 1 file with SQL injection (pynt-sql-injection-hardcore)
  - 7 files with known catalog gaps (CMDi, YAML deserialization)

### Rule Taxonomy
- **Source**: `pynt/server/analyzers/rules/python_rules.yaml`
- **Catalog depth**: 3 active rules (manual-secrets, sql-injection-hardcore, debug-execute-check)
- **Known gaps**: Command injection (os.system, subprocess), YAML unsafe deserialization, SQL injection (% formatting)

### Ground Truth Unit
- **Scope**: Per-file (not per-location)
- **Expected variable**: `expected_rule_ids` (set of Semgrep rule IDs that should fire on file)
- **Review status**: `reviewed` (high confidence), `draft` (awaiting catalog expansion)
- **Adjudication**: Manual review notes for each case

---

## 3. Livelli di Test & Esecuzione

### Layer 1: Deterministic (Hard) Assertions ✅
**Proposito**: Validare la detection delle regole (layer Semgrep) contro ground truth  
**Quando**: Ad ogni esecuzione test (veloce, no dipendenze esterne)  
**Status**: ✅ Implementato in `test_diagnostic_validation.py` + `test_security_analysis.py`

**Test Class**: `TestDeterministicDetection`, `TestDetectionCoverage`, `TestRegressionBaseline`

```python
# Esecuzione in test_security_analysis.py
analyzer = SemgrepAnalyzer()
semgrep_results = analyzer.analyze(code, language="python", ...)
detected_rule_ids = {result.check_id for result in semgrep_results}

# Validazione vs ground truth
assert detected_rule_ids == expected_rule_ids
```

**KPI**:
- Validazione schema ground truth: 100% pass
- Check esistenza file: 100% dei 19 file presenti
- Distribuzione review status: ≥ 12 reviewed, ≤ 7 draft

### Layer 2: LLM Structure & Parsing ✅
**Proposito**: Validare qualità output LLM, Finding schema, educationalExplanation sections  
**Quando**: Con LLM API disponibile (test su aa.py per evitare eccessive chiamate)  
**Status**: ✅ Implementato in `test_detector_integration.py`

**Test Classes**: `TestFindingStructure`, `TestFalsePositiveDetection`

```python
# API contract validation
finding = analyzed_findings[0]
assert finding.line > 0
assert finding.educationalExplanation != ""
assert isinstance(finding.isFalsePositive, bool)

# LLM section validation
sections = validate_educational_explanation_sections(
    finding.educationalExplanation
)
assert sections['all_sections_present']  # explanation, suggested_fix, ecc.
```

**KPI**:
- All required fields present: 100%
- educationalExplanation contains all 5 sections: ≥ 95%
- suggestedFix non-empty quando expected: ≥ 90%
- isFalsePositive field set correctly: 100%

### Layer 3: Regression (Temporal Assertions)
**Proposito**: Rilevare drift nella detection tra versioni  
**Quando**: Continuous integration dopo cambio regole  
**Status**: 🔄 Planificato (baseline da stabilire in Phase 2)

```python
# Dopo stabilire baseline
current_metrics = compute_detection_metrics()
baseline = load_baseline()

deltas = {
    "precision": current_metrics["precision"] - baseline["precision"],
    "recall": current_metrics["recall"] - baseline["recall"],
}

assert abs(deltas["precision"]) < 0.05, "Regressione precision rilevata"
assert abs(deltas["recall"]) < 0.05, "Regressione recall rilevata"
```

**Trigger**:
- Qualsiasi modifica a `python_rules.yaml` → re-run detection tests
- Qualsiasi cambio prompt LLM → re-run LLM structure tests
- Qualsiasi upgrade versione Semgrep → full regression suite

---

## 4. Metriche & Scoring

### Metriche Detection (Base Per-File)

Per ogni file:
```
TP (True Positive) = regole rilevate ∩ attese
FP (False Positive) = regole rilevate \ attese
FN (False Negative) = attese \ rilevate
```

Aggregate su tutti i file:
```
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × (precision × recall) / (precision + recall)
```

### Strategia di Filtro
- Computa metriche su **solo casi reviewed** per validazione rigorosa
- Traccia casi draft separatamente come "gap noti"
- Riporta FP esplicitamente (detection inaspettate vanno investigate)

### Soglie Obiettivo
| Metrica | Minimo | Obiettivo | Stato |
|--------|--------|----------|--------|
| Precision | 0.75 | 0.85 | ✓ Set |
| Recall | 0.80 | 0.90 | ✓ Set |
| F1 | 0.78 | 0.87 | ✓ Set |
| Contract Pass Rate | 95% | 100% | ✓ Set |
| LLM Parse Rate | 90% | 95% | ✓ Set |

---

## 5. Governance & Adjudication

### Stato Review

**`reviewed`** (12 casi)
- Adjudication manuale a due passaggi completata
- Verdict chiaro: expected rule IDs corrispondono alle vulnerabilità reali nel codice
- Accettabile per validazione rigorosa
- Esempio: aa.py (SQL injection via concatenazione)

**`draft`** (7 casi)
- Inferenza a un passaggio o automatica
- Marcato per re-review se:
  - Gap catalogo risolto (nuova regola aggiunta)
  - Ambiguità pattern risolta
- Ancora tracciato in metriche, ma flaggato come "limitazione nota"
- Esempio: c1.py (ha CMDi ma nessuna regola nel catalogo ancora)

### Workflow Adjudication
1. **Inferenza**: Mapping automatico usando pattern matching contro rule catalog
2. **First Review**: Un reviewer valuta file vulnerability e expected_rule_ids
3. **Adjudication**: Documenta decisione nel campo `adjudication_notes`
4. **Status**: Set a `reviewed` o `draft` con razionale
5. **Escalation**: Caso ambiguo → secondo reviewer + tag come `draft`

### Campi Governance per Caso
```json
{
  "file": "aa.py",
  "expected_rule_ids": ["pynt-sql-injection-hardcore"],
  "review_status": "reviewed",
  "adjudication_notes": "SQL injection chiara alle linee 21, 30 via string concatenation. Pattern match confermato.",
  "evidence_lines": [21, 30]
}
```

---

## 6. Esecuzione Operazionale & Piano Fasi

### Phase 1: Baseline (Attuale - Settimana 1)
- ✅ Creare ground truth (automatico + adjudication manuale)
- ✅ Scrivere hard assertion tests (schema validation)
- ✅ Scrivere computazione metriche (precision/recall/F1)
- ✅ Impostare metriche baseline
- **Deliverable**: ground_truth.json + test_diagnostic_validation.py + baseline_metrics.json

### Phase 2: Live Detection (Settimana 2–3)
- Integrare server pynt (start FastAPI server, run analyzer su Security_test)
- Collezionare detected rule_ids da ogni file
- Eseguire hard assertions (match contro ground truth)
- Computare metriche aggregate
- **Gate**: Recall ≥ 0.85 su casi reviewed

### Phase 3: Soft Assertions (Settimana 3–4)
- Validare contratto API (conformità response schema)
- Parsare sezioni diagnostiche LLM
- Misurare parse success rate
- **Gate**: ≥ 95% parse success rate

### Phase 4: Catalog Expansion (Settimana 4–6)
- Implementare regole mancanti (CMDi, YAML deserialization, SQL %)
- Re-run metriche (draft → reviewed promotion)
- Target: copertura da 12/19 a 17+/19 file
- **Gate**: Recall ≥ 0.90 su tutti casi reviewed

### Phase 5: Regression CI (Settimana 6+)
- Impostare baseline come golden standard
- Run regression suite su ogni cambio regole/prompt
- Automated gate su precision/recall delta
- **Gate**: |delta| < 0.05 su precision/recall

### Comandi di Esecuzione per Layer

**Layer 1 - Hard Assertions (Detection Accuracy) ✅**
```bash
# Validazione schema ground truth (no analysis execution)
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
# Output: 23+ tests passed (file existence, rule catalog references)

# Governance checks
pytest tests/test_diagnostic_validation.py::TestGovernance -v
# Output: Verifica adjudication_notes presenti, status reviewed/draft validi

# Detection per-file con metriche
pytest tests/test_security_analysis.py::TestDetectionCoverage -v
# Output: Detection results per file con TP/FP/FN tracking
# Tempo: ~2-3 minuti
```

**Layer 2 - LLM Structure & Parsing Validation ✅**
```bash
# Valida Finding schema e sezioni LLM
pytest tests/test_detector_integration.py::TestFindingStructure -v
# Output: Validazione campi obbligatori, tipi corretti, sezioni presenti

# Validazione false positive field
pytest tests/test_detector_integration.py::TestFalsePositiveDetection -v
# Output: Verifica isFalsePositive marcato correttamente

# Validazione completa (tutte le sezioni educativeExplanation)
pytest tests/test_detector_integration.py::TestFindingStructure::test_educational_explanation_contains_all_sections -v
# Output: Verifica educationalExplanation contiene explanation, suggested_fix, code_example, references, is_false_positive
```

**Layer 3 - Regression Tracking (Future) 🔄**
```bash
# Una volta stabilito baseline, comparare con run successivo
# (sarà parte di CI pipeline)
pytest tests/test_security_analysis.py::TestRegressionBaseline -v
```

### Piano Fasi di Esecuzione

#### Phase 1: Baseline Setup ✅ (Completato)
- ✅ Creare ground truth (automatico + adjudication manuale)
- ✅ Scrivere hard assertion tests (schema validation)
- ✅ Implementare run_pynt_on_file() con import diretto
- ✅ Scrivere computazione metriche (precision/recall/F1)
- **Deliverable**: ground_truth.json + test_diagnostic_validation.py + metrics.py

#### Phase 2: Live Detection & Metrics 🔄 (In Progress)
- ✅ Implementare test_security_analysis.py con detection per-file
- ✅ Implementare metriche aggregate (precision/recall/F1)
- ✅ Implementare test_detector_integration.py con LLM validation
- ⏳ Eseguire `pytest tests/test_security_analysis.py -v`
- ⏳ Eseguire `pytest tests/test_detector_integration.py -v`
- ⏳ Validare metrics aggregate (target: Recall ≥0.85, Precision ≥0.80)
- **Gate**: Recall ≥ 0.85 su casi reviewed + Finding schema 100% conforme

**Comandi Phase 2**:
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt

# Layer 1: Detection tests
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
pytest tests/test_security_analysis.py::TestDetectionCoverage -v

# Layer 2: LLM structure tests (require GROQ_API_KEY se test non skipped)
pytest tests/test_detector_integration.py -v

# Vedi summary
pytest tests/ -v --tb=short
```

#### Phase 3: Catalog Expansion (Future)
- Implementare regole mancanti (CMDi, YAML deserialization, SQL %)
- Re-run metriche (draft → reviewed promotion)
- Target: copertura da 12/19 a 17+/19 file
- **Gate**: Recall ≥ 0.90 su tutti casi reviewed

#### Phase 4: Regression CI & Automation (Future)
- Impostare baseline come golden standard in CI
- Run regression suite su ogni cambio regole/prompt
- Automated gate su precision/recall delta
- **Gate**: |delta| < 0.05 su precision/recall

---

## 7. Gap Catalogo & Roadmap

### HIGH Priority (Blocca molti file)

**Command Injection via os.system()**
- Regola mancante: `pynt-command-injection-os-system`
- File interessati: 15 (c1–c15)
- Pattern: `os.system(f"...")` o `os.system("..." + ...)`
- Severity: ERROR (RCE risk)

**YAML Unsafe Deserialization**
- Regola mancante: `pynt-yaml-unsafe-deserialization`
- File interessati: 17 (c1–c17)
- Pattern: `yaml.load(..., Loader=yaml.FullLoader)` o default Loader
- Severity: ERROR (arbitrary code execution)

### MEDIUM Priority

**SQL Injection (% Formatting)**
- Variante pattern mancante in `pynt-sql-injection-hardcore`
- File interessati: 1 (bb.py)
- Pattern: `"SELECT ... WHERE x = %s" % user_input`
- Suggerito: Espandere regola esistente

**Hardcoded Secrets (Varianti TOKEN/KEY)**
- Limitazione in `pynt-manual-secrets` regex
- File interessati: 5 (c1, c4, c5, c12, c15)
- Regex attuale: `(API_KEY|PASSWORD|AUTH_TOKEN)`
- Suggerito: Espandere per includere `(.*_)?SECRET|TOKEN|KEY`

**Command Injection via subprocess**
- Regola mancante: `pynt-command-injection-subprocess`
- File interessati: 2 (c16, c17)
- Pattern: `subprocess.run(..., shell=True)` con f-string/concat
- Severity: ERROR

---

## 8. Integrazione & Troubleshooting

### Pre-Commit Gate
```bash
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
# Deve passare: schema validation, file count, review status checks
```

### Pre-Release Gate
```bash
pytest tests/test_security_analysis.py -v
pytest tests/test_detector_integration.py -v
# Deve passare: detection accuracy (Recall ≥0.85) + Finding schema 100% conforme
# Alert se Recall scende sotto 0.85 o Precision sotto 0.80
```

### Troubleshooting Comuni

**Problema 1: "Groq API key not configured"**
```
ERROR: Groq API key not configured - skipping LLM integration tests
```
✅ **Accettabile!** test_detector_integration.py salta automaticamente se no GROQ_API_KEY.  
Per testare LLM parsing, aggiungi chiave a `.env`, altrimenti test si salta senza errore.

**Problema 2: ModuleNotFoundError per SemgrepAnalyzer**
```
ModuleNotFoundError: No module named 'analyzers'
```
Soluzione: Esegui da directory pynt/
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt
pytest tests/ -v
```

**Problema 3: Semgrep not found**
```
RuntimeError: Semgrep non trovato. Assicurati di averlo installato nel venv.
```
Soluzione: Installa Semgrep
```bash
pip install semgrep
```

**Problema 4: ground_truth.json parsing fails**
```
JSONDecodeError: Expecting value on line 1
```
Soluzione: Valida JSON sintassi
```bash
python -c "import json; json.load(open('tests/Security_test/ground_truth.json'))"
```

**Problema 5: Test skipped (no API key)**
```
SKIPPED: Groq API key not configured - skipping LLM integration tests
```
✅ Normale! Aggiungi GROQ_API_KEY a `.env` per run LLM tests, altrimenti ignora.

---

## 9. File Test & Ubicazioni

| Componente | Ubicazione | Proposito |
|-----------|----------|---------|
| Ground Truth | `tests/Security_test/ground_truth.json` | Dataset autoritativo + metadata |
| Schema Validation | `tests/test_diagnostic_validation.py` | Hard assertions: schema, governance, coverage |
| Detection Tests | `tests/test_security_analysis.py` | Per-file detection, metriche aggregate precision/recall/F1 |
| LLM Structure Tests | `tests/test_detector_integration.py` | Finding schema validation, educationalExplanation sections, false positive detection |
| Test Data | `tests/Security_test/aa.py, bb.py, c1-c17.py` | 19 file Python con vulnerability patterns |
| Catalog | `server/analyzers/rules/python_rules.yaml` | Regole Semgrep attive |
| Config | `tests/pytest.ini` | Configurazione pytest (markers, test discovery)

---

## 10. Acceptance Criteria & Prossimi Task

### Definition of Done (Phase 2)
- ✅ Ground truth completato e revisionato (19 file)
- ✅ Hard assertions implementati (TestDeterministicDetection, TestGovernance)
- ✅ Detection tests implementati (TestDetectionCoverage con metriche per-file)
- ✅ LLM structure tests implementati (TestFindingStructure, TestFalsePositiveDetection)
- ✅ educationalExplanation section validation (5 sections: explanation, suggested_fix, code_example, references, is_false_positive)
- ✅ Pulizia test folder (rimossi file inutili: conftest.py, metrics.py, fixtures/)
- ⏳ Eseguire `pytest tests/test_security_analysis.py -v` - validare Recall ≥0.85
- ⏳ Eseguire `pytest tests/test_detector_integration.py -v` - validare Finding schema 100%
- ⏳ Catalog gaps documentati con priority/suggested rules
- ⏳ Regression gate implementato per CI

### Task Prossimo Sprint
1. ✅ **Cleanup test folder**: Rimossi conftest.py, metrics.py, fixtures/
2. ⏳ **Eseguire Layer 1 + Layer 2 tests**:
   ```bash
   pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
   pytest tests/test_security_analysis.py -v
   pytest tests/test_detector_integration.py -v
   ```
3. ⏳ **Analizzare risultati**:
   - Recall vs soglia 0.85 (detection coverage)
   - Finding schema 100% conforme (no field missing)
   - educationalExplanation sections presenti (all 5 sections)
   - false positive detection accuracy
4. 🔮 **Implementare regole mancanti** (Phase 3, se Recall < 0.85)
   - Command injection (os.system, subprocess)
   - YAML unsafe deserialization
   - SQL injection % formatting
5. 🔮 **Soft assertions & LLM quality** (Phase 4)
   - Parse success rate ≥ 95%
   - suggestedFix quality
   - executableFix validity

---

## 11. Riferimenti

- Ground Truth: [tests/Security_test/ground_truth.json](tests/Security_test/ground_truth.json)
- Schema Validation Tests: [tests/test_diagnostic_validation.py](tests/test_diagnostic_validation.py)
- Detection Tests: [tests/test_security_analysis.py](tests/test_security_analysis.py)
- LLM Structure Tests: [tests/test_detector_integration.py](tests/test_detector_integration.py)
- API Contract: [server/models/schemas.py](server/models/schemas.py) (linea 32–68)
- Rule Catalog: [server/analyzers/rules/python_rules.yaml](server/analyzers/rules/python_rules.yaml)
- Frontend Integration: [extension/src/types.ts](extension/src/types.ts) (Finding interface)
- LLM Parsing: [server/agents/base_agent.py](server/agents/base_agent.py) (linea 392–459)
