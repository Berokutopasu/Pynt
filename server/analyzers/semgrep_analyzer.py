# analyzers/semgrep_analyzer.py
import subprocess
import json
import tempfile
import os
import shutil
from typing import List, Dict, Union
from models.schemas import SemgrepResult, AnalysisType
from config.settings import settings
import re

class SemgrepAnalyzer:
    """Wrapper per Semgrep che esegue analisi statica"""
    
    # Mapping linguaggi -> estensioni file
    LANGUAGE_EXTENSIONS = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "java": ".java",
        "cpp": ".cpp",
        "c++": ".cpp",   
        "c_cpp": ".cpp", 
        "c": ".c"
    }
    
    def __init__(self):
        self.semgrep_path = shutil.which("semgrep")
        if not self.semgrep_path:
            venv_path = os.environ.get("VIRTUAL_ENV")
            if venv_path:
                possible_paths = [
                    os.path.join(venv_path, "bin", "semgrep"),
                    os.path.join(venv_path, "Scripts", "semgrep.exe")
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        self.semgrep_path = p
                        break
        if not self.semgrep_path:
            raise RuntimeError(" Semgrep non trovato. Assicurati di averlo installato nel venv.")
    
    def analyze(self, code: str, language: str, analysis_type: AnalysisType, project_path: str = None, filename: str = None, extra_targets: List[str] = None) -> List[SemgrepResult]:
        """
        Analizza il codice con Semgrep.
        
        Args:
            code: Codice del file principale da analizzare (buffer corrente dell'editor)
            language: Linguaggio di programmazione
            analysis_type: Tipo di analisi (SECURITY, BEST_PRACTICES, etc.)
            project_path: Path del progetto (non usato attualmente)
            filename: Path reale del file principale
            extra_targets: Lista di path di file aggiuntivi da scansionare (es. dipendenze trovate dal RAG)
        
        Returns:
            Lista di SemgrepResult con path corretti
        """
        
        lang_id = language.lower().strip()
        suffix = self.LANGUAGE_EXTENSIONS.get(lang_id, ".txt")
        config_list = self._resolve_config(lang_id, analysis_type)
        
        targets_to_scan = []
        temp_dir = None
        scan_path = None
        
        # Mappa: path_scansionato -> path_reale
        path_mapping = {}
        
        try:
            # 1. CREAZIONE DIRECTORY TEMPORANEA
            temp_dir = tempfile.mkdtemp(prefix="semgrep_scan_")
            
            # 2. DETERMINA NOME E PATH DEL FILE PRINCIPALE
            if filename:
                # Estrai solo il basename dal filename (es: "main.py" da "C:/project/main.py")
                base_filename = os.path.basename(filename)
                # Il path reale è quello fornito (normalizzato)
                real_path = os.path.normpath(os.path.abspath(filename))
            else:
                # Fallback: genera un nome generico
                base_filename = f"code{suffix}"
                real_path = os.path.normpath(os.path.abspath(os.path.join(temp_dir, base_filename)))
            
            # 3. CREA IL FILE NELLA TEMP DIR CON IL NOME ORIGINALE
            scan_path = os.path.join(temp_dir, base_filename)
            clean_code = code.lstrip('\ufeff')
            # 2. Sostituiamo TUTTI gli spazi non-breaking (\xa0) con spazi veri in TUTTO il file
            clean_code = clean_code.replace('\xa0', ' ').replace('\u200b', '')
            # 3. Normalizziamo i ritorni a capo allo standard puro (ignorando Windows)
            clean_code = clean_code.replace('\r\n', '\n').replace('\r', '\n')
            with open(scan_path, 'wb') as f:
                f.write(clean_code.encode('utf-8'))
            # --- INIZIO BLOCCO DEBUG CODICE RICEVUTO ---
            print("\n" + "="*50)
            print(f"🔍 DEBUG CODICE: Lunghezza {len(code)} caratteri")
            if len(code) > 0:
                print(f"🔍 DEBUG CODICE: Inizia con -> {code[:50].replace(chr(10), ' ')}...")
            else:
                print("❌ ERRORE CRITICO: Il codice ricevuto da VS Code è VUOTO!")
            print("="*50 + "\n")
            # --- FINE BLOCCO DEBUG CODICE RICEVUTO ---
            # Normalizza scan_path per il mapping
            scan_path_normalized = os.path.normpath(os.path.abspath(scan_path))
            
            targets_to_scan.append(scan_path_normalized)
            path_mapping[scan_path_normalized] = real_path
            
            print(f"\n{'='*70}")
            print(f" [Semgrep] MAIN FILE:")
            print(f"   Filename:  {base_filename}")
            print(f"   Scan:      {scan_path_normalized}")
            print(f"   Real:      {real_path}")
            print(f"{'='*70}")

            # 4. AGGIUNTA FILE EXTRA (da RAG/dipendenze)
            if extra_targets:
                print(f"\n [Semgrep] EXTRA FILES ({len(extra_targets)}):")
                for idx, extra in enumerate(extra_targets, 1):
                    if extra and os.path.exists(extra):
                        abs_extra = os.path.normpath(os.path.abspath(extra))
                        
                        # Evita duplicati e il file principale
                        if abs_extra != real_path and abs_extra not in targets_to_scan:
                            targets_to_scan.append(abs_extra)
                            # I file extra mappano a se stessi (sono già file reali su disco)
                            path_mapping[abs_extra] = abs_extra
                            print(f"   [{idx}] {abs_extra}")
                        else:
                            print(f"   [{idx}] {abs_extra} (SKIPPED - duplicate or main file)")
                    else:
                        print(f"   [{idx}] {extra} (SKIPPED - non esiste)")
                print(f"{'='*70}")

            # 5. ESECUZIONE SEMGREP
            print(f"\n [Semgrep] Scansione di {len(targets_to_scan)} file...")
            print(f"   Configs: {', '.join(config_list[:3])}{'...' if len(config_list) > 3 else ''}")
            
            results = self._run_semgrep(targets_to_scan, config_list)
            parsed_results = self._parse_results(results)
            print(f"DEBUG: Semgrep ha trovato {len(parsed_results)} match RAW prima del mapping")

            # 6. DEBUG RISULTATI RAW
            print(f"\n{'='*70}")
            print(f" [Semgrep] RISULTATI RAW ({len(parsed_results)}):")
            for idx, res in enumerate(parsed_results, 1):
                print(f"   [{idx}] {res.path}")
                print(f"        → {res.check_id}")
                print(f"        → Line {res.start.get('line', '?')}")
            print(f"{'='*70}")

            # 7. RIMAPPING DEI PATH
            print(f"\n [Path Mapping] Correzione path...")
            print(f"   Mapping disponibili: {len(path_mapping)}")
            
            for res in parsed_results:
                original_path = res.path
                # Normalizza il path del risultato
                res_normalized = os.path.normpath(os.path.abspath(res.path))
                
                print(f"\n   Analisi: {original_path}")
                print(f"   Normalizzato: {res_normalized}")
                
                # Cerca nel mapping
                if res_normalized in path_mapping:
                    mapped_path = path_mapping[res_normalized]
                    res.path = mapped_path
                    
                    if mapped_path == real_path:
                        print(f"    MAIN -> {mapped_path}")
                    else:
                        print(f"    EXTRA -> {mapped_path}")
                else:
                    # Fallback: controlla se il basename corrisponde
                    found = False
                    res_basename = os.path.basename(res_normalized)
                    
                    for scan_p, real_p in path_mapping.items():
                        if os.path.basename(scan_p) == res_basename:
                            res.path = real_p
                            print(f"    BASENAME MATCH -> {real_p}")
                            found = True
                            break
                    
                    if not found:
                        # Ultimo fallback: usa il path reale del main file
                        res.path = real_path
                        print(f"     FALLBACK -> {real_path}")

            print(f"\n [Semgrep] Analisi completata: {len(parsed_results)} risultati")
            
            # 8. SUMMARY PER FILE
            file_counts = {}
            for res in parsed_results:
                file_counts[res.path] = file_counts.get(res.path, 0) + 1
            
            print(f"\n [Summary] Problemi per file:")
            for fpath, count in file_counts.items():
                print(f"   - {os.path.basename(fpath)}: {count} issue(s)")
                print(f"     Path completo: {fpath}")
            print(f"{'='*70}\n")
            
            return parsed_results

        except Exception as e:
            print(f"Errore Analisi: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # Cleanup
            if temp_dir and os.path.exists(temp_dir):
                try: 
                    shutil.rmtree(temp_dir)
                    print(f"  [Cleanup] Rimossa directory temp: {temp_dir}")
                except Exception as e:
                    print(f"  [Cleanup] Errore rimozione temp dir: {e}")

    def _resolve_config(self, language: str, analysis_type: AnalysisType) -> List[str]:
        configs = []
        lang = language.lower()
        
        # --- 1. CARICAMENTO REGOLE LOCALI ---
        base_path = os.path.dirname(os.path.abspath(__file__))
        path_subdir = os.path.join(base_path, "rules", "python_rules.yaml")
        if os.path.exists(path_subdir):
            configs.append(path_subdir)

        # --- 2. CARICAMENTO REGOLE REMOTE ---
        if lang in ["python", "py"]:
            if analysis_type == AnalysisType.SECURITY:
                configs.extend([
                    "p/security-audit",
                    "p/secrets",
                    "p/owasp-top-ten",
                    "p/insecure-transport",
                    "p/sql-injection"
                ])
            
            elif analysis_type == AnalysisType.BEST_PRACTICES:
                configs.extend([
                    "p/python",
                    "r/python.lang.best-practice",
                    "r/python.style",
                    "r/python.complexity"
                ])
            
            elif analysis_type == AnalysisType.FAULT_DETECTION:
                configs.extend([
                    "r/python.lang.correctness",
                    "r/python.lang.maintainability",
                    "p/error-prone",
                    "p/reliability"
                ])
        
        if not configs:
            return ["p/default", "p/security-audit"]
            
        return configs

    def _run_semgrep(self, file_paths: Union[str, List[str]], config: List[str]) -> Dict:
        cmd = [self.semgrep_path, "scan"] 

        for c in config:
            cmd.extend(["--config", c])

        cmd.extend([
            "--json",
            "--no-git-ignore",
        ])

        cmd.extend(file_paths)
        # --- INIZIO BLOCCO DEBUG COMANDO ---
        print("\n🔥 DEBUG SEMGREP: Comando in esecuzione:")
        print(f"   {' '.join(cmd)}")
        print("🔥" + "="*48)
        # --- FINE BLOCCO DEBUG COMANDO ---
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=settings.SEMGREP_TIMEOUT,
                startupinfo=startupinfo,
                shell=False
            )
            print("\n🔥 DEBUG SEMGREP: Output STDOUT:")
            if not result.stdout.strip():
                print("   [STDOUT VUOTO]")
            else:
                print(f"   {result.stdout[:200]}... (troncato)")
                
            if result.stderr.strip():
                print("🔥 DEBUG SEMGREP: Errori in STDERR:")
                print(f"   {result.stderr}")
            # --- FINE BLOCCO DEBUG RISULTATO ---
            if not result.stdout.strip():
                return {"results": []}

            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            print(" Semgrep Timeout")
            return {"results": []}
        except json.JSONDecodeError as je:
            print(f" Errore decodifica JSON Semgrep: {je}")
            return {"results": []}
        except Exception as e:
            print(f" Errore subprocess: {e}")
            return {"results": []}
    
    def _parse_results(self, semgrep_output: Dict) -> List[SemgrepResult]:
        """Converte output Semgrep in formato strutturato"""
        results = []
        raw_results = semgrep_output.get("results", [])
        
        for result in raw_results:
            try:
                semgrep_result = SemgrepResult(
                    check_id=result.get("check_id", "unknown"),
                    path=result.get("path"),
                    start=result.get("start", {}),
                    end=result.get("end", {}),
                    extra=result.get("extra", {})
                )
                results.append(semgrep_result)
            except Exception as e:
                print(f"Errore parsing risultato Semgrep: {e}")
                continue
        
        return results

    def get_severity_from_semgrep(self, extra: Dict) -> str:
        """Estrae severity da metadati Semgrep"""
        severity = extra.get("severity", "INFO").upper()
        severity_map = {
            "ERROR": "ERROR",
            "WARNING": "WARNING",
            "INFO": "INFO"
        }
        return severity_map.get(severity, "INFO")
    
    def extract_message(self, extra: Dict) -> str:
        """Estrae messaggio da risultato Semgrep"""
        return extra.get("message", "Problema rilevato da Semgrep")