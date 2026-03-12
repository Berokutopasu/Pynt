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
                # FIX 1: Estraiamo il nome del file convertendo prima tutte le backslash in slash normali,
                # così funziona perfettamente sia su Windows che dentro Docker (Linux)
                base_filename = filename.replace('\\', '/').split('/')[-1]
                
                # FIX 2: Non applichiamo 'abspath' al filename. Lo salviamo esattamente com'è! 
                # (es. "c:\Users\...") così VS Code lo riconosce per fare gli hover.
                real_path = filename
            else:
                # Fallback: genera un nome generico
                base_filename = f"code{suffix}"
                real_path = os.path.normpath(os.path.abspath(os.path.join(temp_dir, base_filename)))
            
            # 3. CREA IL FILE NELLA TEMP DIR CON IL NOME ORIGINALE
            scan_path = os.path.join(temp_dir, base_filename)
            clean_code = code.lstrip('\ufeff')
            clean_code = clean_code.replace('\xa0', ' ').replace('\u200b', '')
            clean_code = clean_code.replace('\r\n', '\n').replace('\r', '\n')
            
            with open(scan_path, 'wb') as f:
                f.write(clean_code.encode('utf-8'))
                
            # Normalizza scan_path per il mapping (questo su Linux funziona bene)
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
                        if abs_extra != real_path and abs_extra not in targets_to_scan:
                            targets_to_scan.append(abs_extra)
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

            # 7. RIMAPPING DEI PATH
            for res in parsed_results:
                res_normalized = os.path.normpath(os.path.abspath(res.path))
                
                # Applica il mapping per restituire il path puro di Windows a VS Code
                if res_normalized in path_mapping:
                    res.path = path_mapping[res_normalized]
                else:
                    found = False
                    res_basename = os.path.basename(res_normalized)
                    for scan_p, real_p in path_mapping.items():
                        if os.path.basename(scan_p) == res_basename:
                            res.path = real_p
                            found = True
                            break
                    if not found:
                        res.path = real_path

            return parsed_results

        except Exception as e:
            print(f"Errore Analisi: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try: 
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"  [Cleanup] Errore rimozione temp dir: {e}")

    def _resolve_config(self, language: str, analysis_type: AnalysisType) -> List[str]:
        configs = []
        lang = language.lower()
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        security_rules = os.path.join(base_path, "rules", "security_rules.yaml")

        fault_rules = os.path.join(base_path, "rules", "fault_rules.yaml")
        bestpractice_rules = os.path.join(base_path, "rules", "bestpractice_rules.yaml")

      

        if lang in ["python", "py"]:
            if analysis_type == AnalysisType.SECURITY:
                configs.extend([
                    "p/security-audit",
                    "p/secrets",
                    "p/owasp-top-ten",
                    "p/insecure-transport",
                    "p/sql-injection"
                ])
                if os.path.exists(security_rules):
                    configs.append(security_rules)
            elif analysis_type == AnalysisType.BEST_PRACTICES:
                configs.extend([
                    "p/python",
                    "r/python.lang.best-practice",
                    "r/python.style",
                    "r/python.complexity"
                ])
                if os.path.exists(bestpractice_rules):
                    configs.append(bestpractice_rules)
            elif analysis_type == AnalysisType.FAULT_DETECTION:
                configs.extend([
                    "p/python",
                    "p/default"
                ])
                if os.path.exists(fault_rules):
                    configs.append(fault_rules)

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
                continue
        
        return results

    def get_severity_from_semgrep(self, extra: Dict) -> str:
        severity = extra.get("severity", "INFO").upper()
        severity_map = {
            "ERROR": "ERROR",
            "WARNING": "WARNING",
            "INFO": "INFO"
        }
        return severity_map.get(severity, "INFO")
    
    def extract_message(self, extra: Dict) -> str:
        return extra.get("message", "Problema rilevato da Semgrep")