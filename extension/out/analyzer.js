"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CodeAnalyzer = void 0;
// analyzer.ts
const types_1 = require("./types");
class CodeAnalyzer {
    constructor(serverUrl) {
        this.serverUrl = serverUrl;
    }
    /**
     * Gestisce la chiamata verso una o più rotte specifiche in parallelo
     */
    async analyze(request) {
        const promises = [];
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
        }
        catch (error) {
            this.handleError(error);
            throw error; // Rilancia per fermare l'esecuzione
        }
    }
    /**
     * Esegue la singola fetch verso un endpoint specifico
     */
    async performSingleFetch(url, request, type) {
        const controller = new AbortController();
        try {
            console.log(`🚀 [Analyzer] Richiesta partita verso: ${url}`); // LOG 1
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
            const rawData = await response.json();
            // LOGGA TUTTO QUELLO CHE ARRIVA!
            console.log(`📦 [Analyzer] Risposta RAW da ${type}:`, JSON.stringify(rawData, null, 2));
            if (rawData.findings && rawData.findings.length > 0) {
                const primo = rawData.findings[0];
                console.log("🔍 [ANALISI CAMPI] Controllo il primo finding:");
                console.log("   - Chiavi presenti:", Object.keys(primo));
                console.log("   - C'è 'educationalExplanation'?", primo.educationalExplanation !== undefined ? "✅ SÌ" : "❌ NO (Probabile snake_case?)");
                console.log("   - C'è 'educational_explanation'?", primo.educational_explanation !== undefined ? "⚠️ SÌ (Eccolo!)" : "❌ NO");
            }
            // ---------------------------------------------
            return rawData;
        }
        catch (error) {
            console.error(`❌ [Analyzer] Errore Fetch:`, error);
            throw error;
        }
    }
    /**
     * Mappa il tipo di analisi all'endpoint API corretto
     */
    getEndpointForType(type) {
        switch (type) {
            case types_1.AnalysisType.SECURITY:
                return '/analyze/security';
            case types_1.AnalysisType.BEST_PRACTICES:
                return '/analyze/best-practices'; // Nota l'uso del trattino nel URL standard
            case types_1.AnalysisType.FAULT_DETECTION:
                return '/analyze/fault-detection';
            default:
                return '/analyze'; // Fallback
        }
    }
    /**
     * Unisce array multipli di risposte in una sola risposta coerente
     */
    mergeResponses(results, originalRequest) {
        const allFindings = [];
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
    handleError(error) {
        if (error.name === 'AbortError') {
            throw new Error(`Timeout: Il server non ha risposto in tempo.`);
        }
        // ECONNREFUSED si manifesta come TypeError in fetch o con cause specifiche
        if (error.cause && (error.cause.code === 'ECONNREFUSED' || error.message.includes('fetch failed'))) {
            throw new Error(`Impossibile connettersi al server Pynt su ${this.serverUrl}. ` +
                'Assicurati che il server Python sia avviato e raggiungibile.');
        }
        // Se è già un errore formattato da noi, lo lasciamo passare, altrimenti lo wrappiamo
        if (!error.message.startsWith('Errore server') && !error.message.startsWith('Impossibile')) {
            // Loggare l'errore reale in console per debug
            console.error("Pynt Fetch Error:", error);
        }
    }
    // --- Health Check ---
    async healthCheck() {
        try {
            const controller = new AbortController();
            //const timeoutId = setTimeout(() => controller.abort(), 5000); 
            const response = await fetch(`${this.serverUrl}/health`, {
                method: 'GET',
                signal: controller.signal
            });
            //clearTimeout(timeoutId);
            return response.status === 200;
        }
        catch {
            return false;
        }
    }
    updateServerUrl(newUrl) {
        this.serverUrl = newUrl.replace(/\/$/, "");
    }
}
exports.CodeAnalyzer = CodeAnalyzer;
//# sourceMappingURL=analyzer.js.map