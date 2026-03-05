# Eseguire i Test RAGAS Online di Pynt

Questo documento contiene le istruzioni per eseguire i test di valutazione RAG online.

## Prerequisiti

- `.env` deve essere configurato in `server/.env` con:
  - `GROQ_API_KEYS` (almeno una chiave valida)
  - Altre impostazioni LLM necessarie

## Installazione Dipendenze

Esegui questi comandi nel terminale PowerShell dalla radice del progetto:

```powershell
# Installa/aggiorna le dipendenze richieste
python -m pip install pytest-timeout ragas langchain-groq datasets -q

# Alternativamente, installa tutte le dipendenze da requirements.txt
python -m pip install -r requirements.txt -q
```

## Esecuzione Test Offline (consiglato per test rapidi)

```powershell
# Test RAG offline (solo retrieval, nessuna API esterna)
python -m pytest tests/test_rag_retrieval_offline.py -v -m rag_offline
```

## Esecuzione Test Online RAGAS (con valutazione completa)

Questi test richiedono API LLM esterne (Groq) e consumano quota.

### Opzione 1: Comando singolo in PowerShell
```powershell
$env:RUN_RAG_EVALUATION = 1; python -m pytest tests/test_rag_evaluation_online.py -v -m rag_online --tb=short
```

### Opzione 2: Su più righe (più leggibile)
```powershell
# Imposta la variabile d'ambiente
$env:RUN_RAG_EVALUATION = 1

# Esegui il test
python -m pytest tests/test_rag_evaluation_online.py -v -m rag_online --tb=short
```

### Opzione 3: Con timeout personalizzato
```powershell
$env:RUN_RAG_EVALUATION = 1; python -m pytest tests/test_rag_evaluation_online.py -v -m rag_online --timeout=300
```

## Opzioni Utili

| Opzione | Descrizione |
|---------|------------|
| `-v` | Verbose output |
| `-s` | Mostra print() e output durante l'esecuzione |
| `--tb=short` | Mostra traceback brevi in caso di errore |
| `--timeout=300` | Timeout per test (in secondi) |
| `-x` | Ferma al primo errore |
| `-k "test_name"` | Esegui solo test con il nome specificato |

## Esempi Completi

### Eseguire con output verboso e debug
```powershell
$env:RUN_RAG_EVALUATION = 1; python -m pytest tests/test_rag_evaluation_online.py -v -s --tb=short
```

### Eseguire solo test RAG online con timeout di 600 secondi
```powershell
$env:RUN_RAG_EVALUATION = 1; python -m pytest -m rag_online -v --timeout=600
```

### Eseguire tutti i test RAG (offline + online)
```powershell
python -m pytest -m "rag_offline or rag_online" -v

# Se vuoi eseguire anche online con valutazione
$env:RUN_RAG_EVALUATION = 1; python -m pytest -m "rag_offline or rag_online" -v
```

## Troubleshooting

### Errore: "ModuleNotFoundError: No module named 'ragas'"
```powershell
python -m pip install ragas -q
```

### Errore: "No GROQ_API_KEYS available"
- Verifica che `server/.env` contenga `GROQ_API_KEYS` valide
- Verifica che il percorso `server/.env` sia corretto

### Errore: "pytest-timeout not found"
```powershell
python -m pip install pytest-timeout -q
```

### Test scade (timeout)
Aumenta il timeout con `--timeout=600` per 10 minuti

## Note Importanti

- I test online consumano quota API Groq
- I test offline non consumano quota, quindi esegui quelli prima se possibile
- Il tempo di esecuzione varia in base alla connessione di rete e disponibilità API
- Usa `-s` per vedere i log [DEBUG] durante l'esecuzione
