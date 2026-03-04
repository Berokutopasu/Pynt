# Strategia di Test Pynt - Validazione completa pipeline Semgrep + LLM

**Versione:** 2.0 Unificata  
**Data:** 2026-03-03  
**Scope:** Validazione della pipeline diagnostica Semgrep + LLM per il frontend  
**Dataset Obiettivo:** pynt/Security_test (19 file Python)

---

## Quick Start (3 Passaggi)

### 1. Validazione Ground Truth
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
# Output atteso: 23 passed (schema, file count, rule refs)
```

### 2. Cobertura Attuale
```bash
pytest tests/test_diagnostic_validation.py::TestDetectionCoverage -v
# Output: 12/19 file reviewed, 7 draft (catalog gaps)
```

### 3. Imposta Baseline Metriche
```bash
python tests/metrics.py --run-pynt --set-baseline
# Crea snapshot: tests/.test_results/baseline.json
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

### Layer 1: Deterministic (Hard) Assertions
**Proposito**: Validare la detection delle regole (layer Semgrep) contro ground truth  
**Quando**: Ad ogni esecuzione test (veloce, no dipendenze esterne)

```python
# Type checks
assert all(isinstance(rid, str) for rid in case["expected_rule_ids"])
assert case["review_status"] in ["reviewed", "draft"]

# Schema validation
for case in cases:
    assert set(case.keys()) >= {"file", "expected_rule_ids", "review_status", "notes"}

# Coverage
assert len(reviewed_cases) >= 12
assert files_with_expected_rules >= 10
```

**KPI**:
- Validazione schema ground truth: 100% pass
- Check esistenza file: 100% dei 19 file presenti
- Distribuzione review status: ≥ 12 reviewed, ≤ 7 draft

### Layer 2: Generative (Soft) Assertions
**Proposito**: Validare qualità output LLM e contratto API (quando integrato)  
**Quando**: Fase test di integrazione (richiede server pynt live)

```python
# API contract
assert response["type"] == "AnalysisResponse"
for finding in response["findings"]:
    assert {"line", "column", "severity", "message", "ruleId"}.issubset(finding.keys())

# LLM section parseability
sections_found = parse_llm_response(finding["message"])
assert sections_found >= {"EXPLANATION", "SUGGESTED_FIX"}
```

**KPI**:
- Message non-empty: 100%
- Sezioni parseabili: ≥ 95% (FALSE_POSITIVE, EXPLANATION, SUGGESTED_FIX, CODE_EXAMPLE)
- Conformità schema: 100%

### Layer 3: Regression (Temporal Assertions)
**Proposito**: Rilevare drift nella detection tra versioni  
**Quando**: Continuous integration dopo cambio regole

```python
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
- Qualsiasi modifica a `python_rules.yaml` → re-run metrics
- Qualsiasi cambio prompt LLM → re-run soft assertions
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

**Layer 1 - Hard Assertions (Deterministic)**
```bash
# Validazione schema ground truth
pytest tests/test_diagnostic_validation.py::TestDeterministicDetection -v
# Output: 23/23 tests passed (file existence, rule catalog references)

# Governance checks
pytest tests/test_diagnostic_validation.py::TestGovernance -v
# Output: Verifica adjudication_notes presenti, status reviewed/draft validi
```

**Layer 2 - Soft Assertions (Requires Live Server)**
```bash
# Da eseguire quando server pynt è UP
# Attualmente skipped - sarà attivato in Phase 3
pytest tests/test_diagnostic_validation.py::TestSoftAssertions -v
# Validazione: API contract, parseabilità LLM sections
```

**Layer 3 - Regression Tracking**
```bash
# Imposta baseline (Phase 1 completato)
python tests/metrics.py --run-pynt --set-baseline
# Output: snapshot precision/recall/F1 in baseline.json

# Monitora regressioni
python tests/metrics.py --run-pynt --compare-baseline
# Alert se delta > ±0.05 su precision/recall
```

### Piano Fasi di Esecuzione

#### Phase 1: Baseline (✅ Completato - Settimana 1)
- ✅ Creare ground truth (automatico + adjudication manuale)
- ✅ Scrivere hard assertion tests (schema validation)
- ✅ Scrivere computazione metriche (precision/recall/F1)
- ✅ Impostare metriche baseline
- **Deliverable**: ground_truth.json + test_diagnostic_validation.py + baseline_metrics.json

#### Phase 2: Live Detection (Settimana 2–3)
- Integrare server pynt (start FastAPI server, run analyzer su Security_test)
- Collezionare detected rule_ids da ogni file
- Eseguire hard assertions (match contro ground truth)
- Computare metriche aggregate
- **Gate**: Recall ≥ 0.85 su casi reviewed

**Comandi Phase 2**:
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt
uvicorn server.main:app --reload  # Start server
python tests/metrics.py --run-pynt  # Esegui detection reale
```

#### Phase 3: Soft Assertions (Settimana 3–4)
- Validare contratto API (conformità response schema)
- Parsare sezioni diagnostiche LLM
- Misurare parse success rate
- **Gate**: ≥ 95% parse success rate

#### Phase 4: Catalog Expansion (Settimana 4–6)
- Implementare regole mancanti (CMDi, YAML deserialization, SQL %)
- Re-run metriche (draft → reviewed promotion)
- Target: copertura da 12/19 a 17+/19 file
- **Gate**: Recall ≥ 0.90 su tutti casi reviewed

#### Phase 5: Regression CI (Settimana 6+)
- Impostare baseline come golden standard
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
python tests/metrics.py --run-pynt --compare-baseline
# Deve passare: regressione entro ±5% su precision/recall
# Alert se nuovo FP introdotto
```

### Post-Deployment Monitoring
- Weekly metrics run su diagnostiche produzione
- Alert su P50 latency increase > 100ms
- Alert su message parse failure rate > 5%

### Troubleshooting Comuni

**Problema 1: pytest tests not found**
```
ERROR: file not found: tests/test_diagnostic_validation.py
```
Soluzione: Verifica path da directory pynt/
```bash
cd c:\Users\ladyc\Documents\GitHub\pynt
ls tests/test_diagnostic_validation.py  # Deve esistere
```

**Problema 2: ground_truth.json parsing fails**
```
JSONDecodeError: Expecting value on line 1
```
Soluzione: Valida JSON sintassi
```bash
python -m json.tool Security_test/ground_truth.json | head -20
```

**Problema 3: Metrics baseline not set**
```
FileNotFoundError: tests/.test_results/baseline.json
```
Soluzione: Crea baseline initialization
```bash
python tests/metrics.py --run-pynt --set-baseline
```

---

## 9. File Test & Ubicazioni

| Componente | Ubicazione | Proposito |
|-----------|----------|---------|
| Ground Truth | `Security_test/ground_truth.json` | Dataset autoritativo + metadata |
| Hard Assertions | `tests/test_diagnostic_validation.py` | Schema validation, coverage checks |
| Metrics Script | `tests/metrics.py` | Calcolo Precision/recall/F1 |
| Baseline | `tests/.test_results/baseline.json` | Riferimento regressione |
| Catalog | `server/analyzers/rules/python_rules.yaml` | Regole Semgrep attive |

---

## 10. Acceptance Criteria & Prossimi Task

### Definition of Done
- [ ] Ground truth rivisto da 2+ persone (internal audit)
- [ ] Hard assertions pass 100% (23/23 tests)
- [ ] Catalog gaps documentati con priority/suggested rules
- [ ] Metrics baseline stabilito (snapshot precision/recall/F1)
- [ ] Regression gate implementato in CI
- [ ] Tutte le fasi esecuzione completate per il rilascio

### Task Prossimo Sprint
1. Implementare live pynt execution (Phase 2)
2. Misurare actual detection (hard assertions)
3. Implementare command injection rule
4. Implementare YAML deserialization rule
5. Re-compute metriche (target: → 0.90+ recall)

---

## 11. Riferimenti

- Ground Truth: [security_test/ground_truth.json](security_test/ground_truth.json)
- API Contract: [server/models/schemas.py](server/models/schemas.py) (linea 32–68)
- Rule Catalog: [server/analyzers/rules/python_rules.yaml](server/analyzers/rules/python_rules.yaml)
- Frontend Integration: [extension/src/types.ts](extension/src/types.ts) (Finding interface)
- LLM Parsing: [server/agents/base_agent.py](server/agents/base_agent.py) (linea 392–459)
