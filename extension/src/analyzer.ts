// analyzer.ts
import { AnalysisRequest, AnalysisResponse, AnalysisType, Finding } from './types';

export class CodeAnalyzer {
  private serverUrl: string;

  constructor(serverUrl: string) {
    this.serverUrl = serverUrl;
  }

  /**
   * Gestisce la chiamata verso una o più rotte specifiche in parallelo
   */
  async analyze(request: AnalysisRequest): Promise<AnalysisResponse> {
    const promises: Promise<AnalysisResponse>[] = [];

    // 1. Per ogni tipo di analisi richiesto, prepariamo la chiamata alla rotta specifica
    for (const type of request.analysisTypes) {
      const endpoint = this.getEndpointForType(type);
      const url = `${this.serverUrl}${endpoint}`;
      
      // Lanciamo la richiesta specifica
      promises.push(this.performSingleFetch(url, request, type));
    }

    try {
      // 2. Eseguiamo tutte le richieste in parallelo 
      const results = await Promise.all(promises);

      // 3. Uniamo i risultati (Merge)
      return this.mergeResponses(results, request);

    } catch (error: any) {
      this.handleError(error);
      throw error; // Rilancia per fermare l'esecuzione
    }
  }

  /**
   * Esegue la singola fetch verso un endpoint specifico
   */
    private async performSingleFetch(url: string, request: AnalysisRequest, type: AnalysisType): Promise<AnalysisResponse> {
      const controller = new AbortController();
      
      try {
        console.log(` [Analyzer] Richiesta partita verso: ${url}`); // LOG 1
        const payload = {
        code: request.code,
        language: request.language,
        filename: request.filename,
        analysisTypes: request.analysisTypes,
        //  Se projectPath è null/undefined, mandiamo una stringa vuota ""
        projectPath: request.projectPath ? request.projectPath : "" 
      };
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Errore server (${response.status}): ${errorText}`);
        }

        // --- PUNTO CRITICO: INTERCETTIAMO IL JSON ---
        const rawData = await response.json() as any;

        // LOGGA TUTTO QUELLO CHE ARRIVA!
        console.log(` [Analyzer] Risposta RAW da ${type}:`, JSON.stringify(rawData, null, 2));
        
        // Debug aggiuntivo per vedere la struttura dei findings
        if (rawData && rawData.findings) {
          console.log(` [Analyzer] Findings da ${type}:`, rawData.findings.map((f: any) => ({
            file: f.file,
            file_path: f.file_path,
            line: f.line,
            message: f.message?.substring(0, 50) + '...'
          })));
        }
        
        if (rawData.findings && rawData.findings.length > 0) {
            const primo = rawData.findings[0];
            console.log(" [ANALISI CAMPI] Controllo il primo finding:");
            console.log("   - Chiavi presenti:", Object.keys(primo));
            console.log("   - C'è 'educationalExplanation'?", primo.educationalExplanation !== undefined ? " SÌ" : " NO (Probabile snake_case?)");
            console.log("   - C'è 'educational_explanation'?", primo.educational_explanation !== undefined ? " SÌ (Eccolo!)" : " NO");
        }
        // ---------------------------------------------

        return rawData as AnalysisResponse;

      } catch (error) {
        console.error(` [Analyzer] Errore Fetch:`, error);
        throw error;
      }
    }

  /**
   * Mappa il tipo di analisi all'endpoint API corretto
   */
  private getEndpointForType(type: AnalysisType): string {
    switch (type) {
      case AnalysisType.SECURITY:
        return '/analyze/security';
      case AnalysisType.BEST_PRACTICES:
        return '/analyze/best-practices'; // Nota l'uso del trattino nel URL standard
      case AnalysisType.FAULT_DETECTION:
        return '/analyze/fault-detection';
      default:
        return '/analyze'; // Fallback
    }
  }

  /**
   * Unisce array multipli di risposte in una sola risposta coerente
   */
  private mergeResponses(results: AnalysisResponse[], originalRequest: AnalysisRequest): AnalysisResponse {
    const allFindings: Finding[] = [];
    let maxTime = 0;

    for (const res of results) {
      if (res.findings) {
        allFindings.push(...res.findings);
      }
      if (res.analysisTime > maxTime) {
        maxTime = res.analysisTime;
      }
    }

    return {
      findings: allFindings,
      analysisTime: maxTime,
      language: originalRequest.language,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Gestione centralizzata degli errori
   */
  private handleError(error: any) {
    if (error.name === 'AbortError') {
       throw new Error(`Timeout: Il server non ha risposto in tempo.`);
    }

    // ECONNREFUSED si manifesta come TypeError in fetch o con cause specifiche
    if (error.cause && (error.cause.code === 'ECONNREFUSED' || error.message.includes('fetch failed'))) {
       throw new Error(
         `Impossibile connettersi al server Pynt su ${this.serverUrl}. ` +
         'Assicurati che il server Python sia avviato e raggiungibile.'
       );
    }
    
    // Se è già un errore formattato da noi, lo lasciamo passare, altrimenti lo wrappiamo
    if (!error.message.startsWith('Errore server') && !error.message.startsWith('Impossibile')) {
        // Loggare l'errore reale in console per debug
        console.error("Pynt Fetch Error:", error);
    }
  }

  // --- Health Check ---
  
  async healthCheck(): Promise<boolean> {
    try {
      const controller = new AbortController();
      //const timeoutId = setTimeout(() => controller.abort(), 5000); 

      const response = await fetch(`${this.serverUrl}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      
      //clearTimeout(timeoutId);
      return response.status === 200;
    } catch {
      return false;
    }
  }

  updateServerUrl(newUrl: string) {
    this.serverUrl = newUrl.replace(/\/$/, "");
  }
}