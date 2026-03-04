# agents/base_agent.py
from abc import ABC, abstractmethod
from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import time
import re
from models.schemas import Finding, AnalysisType, SemgrepResult, SeverityLevel
from config.settings import settings
from typing import List, Dict, Any, Optional # <--- Aggiungi Any e Optional
from analyzers.semgrep_analyzer import SemgrepAnalyzer
import asyncio

class BaseAgent(ABC):
    """Classe base per tutti gli agenti di analisi"""
    
    """Rotazione chiavi"""
    def __init__(self, analysis_type: AnalysisType, language: str):
        self.analysis_type = analysis_type
        self.language = language
        
        # MODIFICA PER PERFORMANCE: Lazy Loading
        # Invece di self.llm = self._initialize_llm(), lo impostiamo a None.
        # Questo impedisce che il server si blocchi all'avvio tentando connessioni.
        self.groq_keys = settings.EFFECTIVE_GROQ_KEYS
        if not self.groq_keys:
            print(" ATTENZIONE: Nessuna chiave GROQ_API_KEYS trovata nel .env!")
            # Fallback dummy per evitare crash immediato, ma l'analisi fallirà
            self.groq_keys = ["dummy_key"]

        self.current_key_index = 0
        self._llm_instance = None 
    @property
    def llm(self):
        """
        Restituisce l'istanza corrente. Se non esiste (o è stata resettata), la crea
        usando la chiave corrente (current_key_index).
        """
        if self._llm_instance is None:
            print(f" Inizializzazione LLM con chiave index {self.current_key_index}")
            current_key = self.groq_keys[self.current_key_index]
            #maschera della chiave nei log per sicurezzza
            self._llm_instance = ChatGroq(
                temperature=0,
                model_name="llama-3.3-70b-versatile",
                api_key=current_key,
                max_retries=0 
            )
        return self._llm_instance
    
    def _rotate_key(self):
        """
        Passa alla prossima chiave E RESETTA L'ISTANZA.
        Questo è il trucco: mettendo a None l'istanza, forziamo la property 'llm'
        a ricrearla con la nuova chiave alla prossima chiamata.
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.groq_keys)
        print(f" Ruoto alla chiave Groq #{self.current_key_index}")
        
        # DISTRUGGERE L'ISTANZA VECCHIA
        self._llm_instance = None

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Ritorna il system prompt specifico per questo agente"""
        pass
    
    @abstractmethod
    def get_analysis_focus(self) -> str:
        """Ritorna la descrizione del focus di analisi"""
        pass
    
    # =========================================================================
    async def analyze(self, code: str, language: str, project_path: str = None, rag_service: Any = None, filename: str = None) -> List[Finding]:
        """
        Orchestra il flusso: Scansione -> Deduplicazione -> LLM Parallelo
        """
        scanner = SemgrepAnalyzer()
        extra_targets = []
        # 1. Eseguiamo Semgrep in un thread separato
        semgrep_results = await asyncio.to_thread(
            scanner.analyze, 
            code, 
            language, 
            self.analysis_type,
            project_path,
            filename, 
            extra_targets
        )

        # --- MODIFICA FONDAMENTALE PER IL RAG ---
        # 2. Se abbiamo un path e il servizio RAG, dobbiamo indicizzare i file!
        if project_path and rag_service:
            print(f" [RAG] Verificando indicizzazione per: {project_path}")
            # Eseguiamo l'ingestione in un thread separato (perché legge file da disco)
            await asyncio.to_thread(
                rag_service.ingest_project,
                project_path,
                language
            )
        # ----------------------------------------

        # 3. Processiamo i risultati con l'LLM (in parallelo)
        findings = await self.process_semgrep_results(semgrep_results, code, rag_service)
        
        return findings


    async def process_semgrep_results(
        self,
        semgrep_results: List[SemgrepResult],
        code: str,
        rag_service: Any = None
    ) -> List[Finding]:
        
        # 1. Deduplicazione
        processed_keys = set()
        unique_results = []
        for result in semgrep_results:
            start_line = self._safe_get(result.start, 'line', -1)
            rule_id = result.check_id
            dedup_key = (start_line, rule_id)
            if dedup_key in processed_keys: continue
            processed_keys.add(dedup_key)
            unique_results.append(result)

        if not unique_results: return []

        # 2. Configurazione SEMAFORO (Max 5 richieste parallele)
        MAX_CONCURRENT_REQUESTS =5
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        print(f" [BaseAgent] Avvio analisi parallela di {len(unique_results)} problemi...")

        # Funzione interna per gestire il singolo task col semaforo
        async def process_single_item(semgrep_result):
            async with semaphore: 
                try:
                    await asyncio.sleep(0.5) #per evitare di colpire il limite delle richieste al secondo
                    rag_context = ""
                    if rag_service:
                        msg = semgrep_result.extra.get('message', '') if isinstance(semgrep_result.extra, dict) else ""
                        target_code = code.split('\n')[semgrep_result.start.get('line', 1)-1]
                        query = f"security validation sanitization for {msg} and usage of {target_code[:50]}"
                        # RAG su thread separato
                        rag_context = await asyncio.to_thread(rag_service.retrieve_context, query)
                        # --- [RAG DEBUG] AGGIUNGI QUESTO BLOCCO ---
                        if rag_context:
                            print(f"\n [RAG DEBUG] Trovato contesto per {semgrep_result.check_id}:")
                            print(f"   {rag_context[:300]}...") # Stampa i primi 300 caratteri
                        else:
                            print(f"\n [RAG DEBUG] Nessun contesto trovato per {semgrep_result.check_id}")

                    # Chiamata LLM su thread separato (fondamentale per non bloccare)
                    educational_content = await self._generate_educational_explanation(
                        semgrep_result,
                        code,
                        rag_context
                    )

                    return self._create_finding(semgrep_result, educational_content)

                except Exception as e:
                    print(f" ERRORE ASYNC: {e}")
                    return self._create_basic_finding(semgrep_result)

        # 3. LANCIO PARALLELO (Gather)
        tasks = [process_single_item(res) for res in unique_results]
        findings = await asyncio.gather(*tasks)

        return list(findings)
    
    async def _generate_educational_explanation(
        self,
        semgrep_result: SemgrepResult,
        code: str,
        rag_context: str = ""
    ) -> Dict[str, str]:
        """
        Genera spiegazione educativa usando LLM
        
        Returns:
            Dict con: explanation, suggested_fix, code_example, references
        """
        # Estrai snippet di codice problematico
        code_lines = code.split('\n')
        start_line = self._safe_get(semgrep_result.start, 'line', 1)
        end_line = self._safe_get(semgrep_result.end, 'line', start_line)
        
        # Prendi contesto (3 righe prima e dopo)
        context_start = max(0, start_line - 4)
        context_end = min(len(code_lines), end_line + 3)
        # MODIFICA 2: Creazione snippet numerato con puntatore
        annotated_lines = []
        for i in range(context_start, context_end):
            actual_line_num = i + 1
            line_content = code_lines[i]
            
            # Se è la riga dell'errore, aggiungiamo un marcatore
            if actual_line_num == start_line:
                marker = "  # <--- [TARGET LINE]"
                annotated_lines.append(f"{actual_line_num}: {line_content}{marker}")
            else:
                annotated_lines.append(f"{actual_line_num}: {line_content}")
        code_snippet = '\n'.join(annotated_lines)
        # Crea prompt per LLM
        prompt = self._build_educational_prompt(
            semgrep_result,
            code_snippet,
            start_line,
            end_line,
            rag_context=rag_context
        )
        print(f"\n{'='*60}")
        print(f" CHIAMATA LLM per riga {start_line}")
        print(f"{'='*60}")
        start_time = time.time()
         # Tentiamo tante volte quante sono le chiavi x 2
        max_attempts = len(self.groq_keys) * 2
        # Se per qualche motivo il prompt è None o vuoto, mettiamo una stringa di fallback
        if not prompt:
            print("⚠️ ATTENZIONE: Il prompt generato era None. Uso un fallback.")
            prompt = "Spiega questa vulnerabilità di sicurezza e come risolverla."
        elif not isinstance(prompt, str):
            # Se è una lista o un dizionario, lo forziamo a stringa
            prompt = str(prompt)
        for attempt in range(max_attempts):
            try:
                start_time = time.time()
                
                # 1. Chiamata ASINCRONA (ainvoke)
                # Fondamentale usare 'await' e 'ainvoke' per non bloccare il server
                response = await self.llm.ainvoke([
                    SystemMessage(content=self.get_system_prompt()),
                    HumanMessage(content=prompt)
                ])
                
                # 2. Calcolo Tempi e Contenuto
                end_time = time.time()
                duration = end_time - start_time
                content = response.content if hasattr(response, 'content') else str(response)
                
                # --- LE TUE PRINT DI DEBUG (MANTENUTE) ---
                print(f"RISPOSTA (Tentativo {attempt + 1}) in {duration:.2f}s")
                print(f"Lunghezza: {len(content)} caratteri")
                print(f"CONTENUTO COMPLETO:")
                print(content)
                print(f"{'='*60}\n")
                
                # 3. Parsing risposta
                parsed = self._parse_llm_response(content)
                
                print("VALIDAZIONE PARSING:")
                for key, value in parsed.items():
                    status = "[OK]" if value and value != "Nessun contenuto disponibile." else "[FAIL]"
                    print(f"  {status} {key}: {len(value) if value else 0} caratteri")
                
                # Se arriviamo qui, è andato tutto bene: ritorniamo il risultato
                return parsed
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 4. Gestione Specifica Rate Limit (Rotazione)
                if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                    print(f" Rate Limit Groq (Key Index {self.current_key_index}): {error_msg[:100]}...")
                    self._rotate_key()
                    await asyncio.sleep(1) # Piccolo backoff
                    continue # Riprova il ciclo con la nuova chiave
                
                # 5. Gestione Errori Fatali (Print originali)
                else:
                    print(f"ERRORE LLM IRRECUPERABILE: {e}")
                    import traceback
                    print(traceback.format_exc())
                    break # Esce dal loop e va al fallback

        # Fallback se il loop finisce senza successo (tutte le chiavi esaurite o errore grave)
        return {
            'explanation': 'Errore durante generazione spiegazione (Servizio non disponibile).',
            'suggested_fix': 'Consulta la documentazione ufficiale.',
            'code_example': '',
            'references': ''
        }
    
    def _build_educational_prompt(
            self,
            semgrep_result: SemgrepResult,
            code_snippet: str,
            start_line: int,
            end_line: int,
            rag_context: str = "" # <--- Il parametro arriva qui
        ) -> str:
            """Costruisce prompt educativo per LLM OTTIMIZZATO CON RAG"""
            
            extra = semgrep_result.extra if isinstance(semgrep_result.extra, dict) else {}
            message = extra.get('message', 'Problema rilevato')
            rule_id = semgrep_result.check_id

            # --- 1. PREPARAZIONE SEZIONE RAG ---
            # Se abbiamo trovato codice correlato nel progetto, lo formattiamo bene.
            # Altrimenti lasciamo la stringa vuota per non sporcare il prompt.
            context_section = ""
            if rag_context:
                context_section = f"""
                 CONTESTO AGGIUNTIVO (Codice trovato in altri file del progetto):
                =================================================================
                {rag_context}
                =================================================================
                ISTRUZIONE RAG: Usa il contesto qui sopra per verificare se esistono già
                funzioni di sicurezza, validatori o configurazioni che mitigano il problema.
                """

            # --- 2. COSTRUZIONE DEL PROMPT FINALE ---
            return f"""You are a Security Engineer explaining vulnerabilities to students.
    EXCLUSIVELY analyze the line marked with "[TARGET LINE]". Evaluate if it is a false positive. 

    Technical Data:
    - Rule: {rule_id}
    - Semgrep Message: {message}
    - Target Line: {start_line}

    {context_section}

    Code to analyze (numbered):
    ```python
    {code_snippet}
    CRITICAL RULES:

    1. Ignore any other errors present in nearby (unmarked) lines.

    2. Focus solely on the vulnerability indicated by the Technical Data.

    3. If the "ADDITIONAL CONTEXT" shows that the data is sanitized elsewhere, flag it as a False Positive.

    4. Generate a STRUCTURED response in ITALIAN following EXACTLY this format:

    FALSE_POSITIVE:
        [true if the finding is a false positive (e.g., data is already sanitized, the rule does not apply in this context), false otherwise. Answer with only 'true' or 'false'.]

    EXPLANATION:
        [Explain in 2-3 sentences WHY line {start_line} is vulnerable. Mention the possible attack type. If the context mitigates the risk, explain it here.]

    SUGGESTED_FIX:
        [Explain HOW to fix line {start_line}. Be specific.]

    APPLICABLE_FIX:
        [MANDATORY RULES AND RESPECT THE STRUCTURE (IMPORTS, FIX REPORTING THE FUNCTION NAME):
        1. NO BOILERPLATE: Do not include 'if name == "main":', do not include external classes or functions unless they are the subject of the fix.
        2. CONTEXT: Return EXCLUSIVELY the lines that replace the vulnerable logic. If the fix requires modifying the function signature or a decorator, return the entire 'def' block. Otherwise, return only the affected line.
        3. COMPLETENESS: The code must be syntactically correct for Python but limited to the affected block.
        4. ABSOLUTELY DO NOT INCLUDE COMMENTS OR NON-CODE TEXT.
        5. DO NOT include lines of code that are already present in the file (like function calls or command executions) unless they are the direct subject of the correction.
        6. If the fix requires multiple lines for a single target line, ensure they do not introduce redundancy with the rest of the context.
        7. Markdown (no ): Do not include markdown code blocks (), return only pure code.
        8. SEPARATE IMPORTS FROM CODE BY INSERTING IN THE IMPORTS SECTION ONLY THE IMPORTS NECESSARY FOR THE FIX, BUT ONLY IF THEY ARE NOT ALREADY PRESENT IN THE FILE. IF THE FIX CAN BE APPLIED WITHOUT NEW IMPORTS, LEAVE THE IMPORTS SECTION EMPTY.]
     IMPORTS:
        [Insert here ONLY the imports necessary for the fix, but only if they are not already present in the file. If no new imports are needed, leave this section empty.]
        [DO NOT INCLUDE COMMENTS OR NON-CODE TEXT, PURE IMPORTS ONLY]
        [Preserve the business logic of the file; do not add imports that are not strictly necessary for the fix.]
    FIX:
        [Insert here ONLY the lines of code that replace the vulnerable logic, following the rules above. If the vulnerable line is contextless, return only that corrected line.]
        [PRESERVE THE BUSINESS LOGIC, TRY TO MINIMIZE THE CHANGES TO THE ORIGINAL CODE, DO NOT INTRODUCE UNNECESSARY NEW IMPORTS. (e.g if I use MySQL in the file, do not change the database connection logic, just fix the vulnerable line, and if I need to import a sanitization function, only import that function, not the entire library)]
        [DO NOT INCLUDE COMMENTS OR NON-CODE TEXT, PURE CODE ONLY, Ensure correct Python indentation! If the fix requires changing the function signature, return the entire function block with the new signature and body.]
        [If the fix includes import statements, they should be included in the IMPORTS section, not here.]
    CODE_EXAMPLE:
        [Insert here an example of ONLY the corrected code for line {start_line}, well formatted.]

    REFERENCES:
        [1-2 official OWASP links or Python documentation]

    NOTE: Each section MUST start with its header (FALSE_POSITIVE:, EXPLANATION:, etc.) on a separate line.
    """
    def _is_valid_python_code(self, code: str) -> bool:
        """Verifica se la stringa è codice Python o semplice testo descrittivo"""
        if not code or len(code.strip()) < 5:
            return False
        
        # Marcatori di linguaggio naturale (se presenti, probabilmente non è codice puro)
        natural_language_markers = [
            "necessario", "modifiche", "falso positivo", 
            "già corretto", "codice sembra ok", "nessun", "spiegazione"
        ]
        
        code_lower = code.lower()
        # Se contiene frasi discorsive tipiche, scartiamo
        if any(marker in code_lower for marker in natural_language_markers):
            return False

        # Requisito minimo strutturale: deve contenere almeno un operatore, 
        # una chiamata di funzione o una keyword Python
        python_patterns = [r'=', r'\(.*\)', r'import\s+', r'def\s+', r'from\s+', r'\[.*\]']
        if not any(re.search(p, code) for p in python_patterns):
            return False

        return True

    def _parse_llm_response(self, response_text: str) -> Dict[str, str]:
        import re
        
            # 1. ESTRAZIONE SEZIONE APPLICABLE_FIX (TUTTA, non solo il primo blocco ```)
        applicable_fix = None
        # Cerchiamo tutto il testo tra APPLICABLE_FIX e la sezione successiva (CODE_EXAMPLE o REFERENCES)
        fix_section_match = re.search(r'APPLICABLE_FIX:\s*(.*?)(?=CODE_EXAMPLE:|REFERENCES:|$)', response_text, re.DOTALL | re.IGNORECASE)

        if fix_section_match:
            # Prendiamo tutto il blocco grezzo, inclusi i tag IMPORTS: e FIX:
            raw_fix = fix_section_match.group(1).strip()
            clean_fix = re.sub(r'```(?:python|py)?|```', '', raw_fix).strip()
            # VALIDAZIONE: Se è testo discorsivo, lo impostiamo a None
            if self._is_valid_python_code(clean_fix):
                applicable_fix = clean_fix
                print(f" [BACKEND] Fix validato: {applicable_fix[:30]}...")
            else:
                print(f" [BACKEND] Fix scartato (rilevato testo discorsivo): {clean_fix[:40]}...")
                applicable_fix = None

            # Log di debug per vedere cosa stiamo mandando al plugin
            if applicable_fix:
                print(f"DEBUG BACKEND - Fix estratto: {applicable_fix[:50]}...")
            else:
                print("DEBUG BACKEND - Fix estratto: Nessuno (scartato)")
        # 2. ESTRAZIONE DELLE ALTRE SEZIONI
        sections = {
            'explanation': '',
            'suggested_fix': '',
            'code_example': '',
            'references': '',
            'is_false_positive': False
        }

        patterns = {
            'explanation': r'EXPLANATION:\s*(.*?)(?=SUGGESTED_FIX:|APPLICABLE_FIX:|CODE_EXAMPLE:|REFERENCES:|$)',
            'suggested_fix': r'SUGGESTED_FIX:\s*(.*?)(?=APPLICABLE_FIX:|CODE_EXAMPLE:|REFERENCES:|$)',
            'code_example': r'CODE_EXAMPLE:\s*(.*?)(?=REFERENCES:|$)',
            'references': r'REFERENCES:\s*(.*?)$'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Pulizia aggressiva SOLO per il testo descrittivo
                sections[key] = re.sub(r'\*\*|\#\#\#?', '', content).strip()

        # Estrazione FALSE_POSITIVE
        fp_match = re.search(r'FALSE_POSITIVE:\s*(true|false)', response_text, re.IGNORECASE)
        if fp_match:
            sections['is_false_positive'] = fp_match.group(1).strip().lower() == 'true'
            print(f" [PARSER] isFalsePositive: {sections['is_false_positive']}")

        # 3. ASSEGNAZIONE FINALE
        # Riassociamo il fix estratto inizialmente
        sections['applicable_fix'] = applicable_fix

        # Pulizia fallback per i campi vuoti
        for key in sections:
            if key in ('applicable_fix', 'is_false_positive'):
                if sections[key] is None or sections[key] == '':
                    sections[key] = None if key == 'applicable_fix' else False
            elif not sections[key]:
                sections[key] = "Nessun contenuto disponibile."

        print(f" FINE PARSING - Fix trovato: {sections['applicable_fix'] is not None}")
        return sections

    def _extract_code_block(self, text: str) -> str:
        import re
        # Cerca esclusivamente il contenuto tra i blocchi di codice Markdown
        # Ignora tutto ciò che sta fuori
        blocks = re.findall(r'```(?:python|py)?\n(.*?)\n```', text, re.DOTALL | re.IGNORECASE)
        
        if blocks:
            # Prende l'ultimo blocco se ce ne sono più di uno (spesso l'LLM corregge se stesso alla fine)
            code = blocks[-1].strip()
            # Rimuove righe residue di "commento" dell'LLM che a volte finiscono dentro
            lines = [l for l in code.split('\n') if not l.strip().startswith('if T')]
            return "\n".join(lines)
        
        return text.strip()
    def _create_finding(
        self,
        semgrep_result: SemgrepResult,
        educational_content: Dict[str, str]
    ) -> Finding:
        """ Crea Finding con COORDINATE NORMALIZZATE (risolve hover sovrapposti)"""
        
        # 1. Gestione robusta di 'extra'
        # In Pydantic 'extra' è spesso un Dict, quindi .get() va bene.
        # Se fosse un oggetto, useremmo getattr(semgrep_result, 'extra', {})
        raw_extra = getattr(semgrep_result, 'extra', {})
        extra = raw_extra if isinstance(raw_extra, dict) else {}
        # 2. FIX CRITICO COORDINATE: Gestione Ibrida (Dict o Object)
        # I log mostrano che .start è spesso un DIZIONARIO, non un oggetto.
        # getattr(dict, 'line') fallisce e ritorna 1. Bisogna usare dict.get()
        
        start_obj = getattr(semgrep_result, 'start', {})
        end_obj = getattr(semgrep_result, 'end', None)

        # Estrazione Start
        if isinstance(start_obj, dict):
            start_line = start_obj.get('line', 1)
            start_col = start_obj.get('col', 0)
        else:
            start_line = getattr(start_obj, 'line', 1)
            start_col = getattr(start_obj, 'col', 0)

        # Estrazione End (con fallback su Start)
        if end_obj:
            if isinstance(end_obj, dict):
                raw_end_line = end_obj.get('line', start_line)
                end_col = end_obj.get('col', 0)
            else:
                raw_end_line = getattr(end_obj, 'line', start_line)
                end_col = getattr(end_obj, 'col', 0)
        else:
            raw_end_line = start_line
            end_col = 0

        #Limito range a max 2 righe 
        if raw_end_line - start_line > 2:
            print(f" Range troppo ampio ({start_line}-{raw_end_line}), normalizzo a {start_line}-{start_line+1}")
            end_line = start_line + 1
        else:
            end_line = raw_end_line

        # 3. Estrai references da testo in modo sicuro
        references = []
        ref_text = educational_content.get('references', '') # Default a stringa vuota se manca
        
        if ref_text:
            ref_lines = ref_text.split('\n')
            for line in ref_lines:
                if 'http' in line:
                    import re
                    # Regex per trovare URL
                    urls = re.findall(r'https?://[^\s]+', line)
                    references.extend(urls)
        # 4. Gestione Quick Fix
        # 4. Gestione Quick Fix Sicura
        raw_exec_fix = educational_content.get('applicable_fix')
        # Se raw_exec_fix è None o stringa vuota, exec_fix diventa None
        exec_fix = raw_exec_fix.strip() if raw_exec_fix else None
        # 5. Return dell'oggetto Finding
        return Finding(
            line=start_line,
            column=start_col,
            endLine=end_line,
            endColumn=end_col,

            # Mappa la severity (assicurati che extra contenga 'severity')
            severity=self._map_severity(extra.get('severity', 'INFO')),

            message=f"{self.get_analysis_focus()}: {extra.get('message', 'Vulnerabilità rilevata')[:80]}...",

            # Contenuto educativo
            educationalExplanation=educational_content.get('explanation', 'N/A'),
            suggestedFix=educational_content.get('suggested_fix', ''),
            executableFix=exec_fix,
            codeExample=educational_content.get('code_example', ''),

            references=references if references else None,
            analysisType=self.analysis_type,
            ruleId=semgrep_result.check_id,
            isFalsePositive=educational_content.get('is_false_positive', False),
            file_path=semgrep_result.path
        )
    
    def _create_basic_finding(self, semgrep_result: SemgrepResult) -> Finding:
        """Crea Finding base senza enhancement LLM (fallback)"""
        # 1. Gestione robusta di 'extra'
        raw_extra = getattr(semgrep_result, 'extra', {})
        extra = raw_extra if isinstance(raw_extra, dict) else {}
        
        # 2. FIX CRITICO COORDINATE (Identico a sopra)
        start_obj = getattr(semgrep_result, 'start', {})
        end_obj = getattr(semgrep_result, 'end', None)

        # Estrazione Start
        if isinstance(start_obj, dict):
            start_line = start_obj.get('line', 1)
            start_col = start_obj.get('col', 0)
        else:
            start_line = getattr(start_obj, 'line', 1)
            start_col = getattr(start_obj, 'col', 0)

        # Estrazione End
        if end_obj:
            if isinstance(end_obj, dict):
                raw_end_line = end_obj.get('line', start_line)
                end_col = end_obj.get('col', 0)
            else:
                raw_end_line = getattr(end_obj, 'line', start_line)
                end_col = getattr(end_obj, 'col', 0)
        else:
            raw_end_line = start_line
            end_col = 0

        if raw_end_line - start_line > 2:
            end_line = start_line + 1
        else:
            end_line = raw_end_line

        return Finding(
            line=start_line,
            column=start_col,
            endLine=end_line,
            endColumn=end_col,
            severity=self._map_severity(extra.get('severity', 'INFO')),
            message=extra.get('message', 'Problema rilevato'),
            
            # Messaggio fisso di fallback
            educationalExplanation="Consulta la documentazione per maggiori dettagli.",
            executableFix=None, # Nessun fix automatico nel fallback
            analysisType=self.analysis_type,
            ruleId=semgrep_result.check_id,
            file_path=semgrep_result.path
        )
    
    def _map_severity(self, semgrep_severity: str) -> SeverityLevel:
        """Mappa severity Semgrep -> nostro enum"""
        severity_map = {
            'ERROR': SeverityLevel.ERROR,
            'WARNING': SeverityLevel.WARNING,
            'INFO': SeverityLevel.INFO
        }
        return severity_map.get(semgrep_severity.upper(), SeverityLevel.INFO)
    
#funzione d'utilità
    def _safe_get(self, obj, field, default=None):
            """Estrae un valore da un oggetto o da un dizionario in modo sicuro"""
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(field, default)
            return getattr(obj, field, default)