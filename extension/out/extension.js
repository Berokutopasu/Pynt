"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
// extension.ts
const vscode = __importStar(require("vscode"));
const analyzer_1 = require("./analyzer");
const decorators_1 = require("./decorators");
const types_1 = require("./types");
const FixProvider_1 = require("./FixProvider");
const path = __importStar(require("path"));
// Variabili Globali
let analyzer;
let decorator;
let diagnosticCollection;
let statusBarItem;
//Mappa per ricordare i risultati di ogni file (URI string -> Lista Findings)
let globalFindingsMap = new Map();
function activate(context) {
    console.log('Pynt extension is now active!');
    // 1. Inizializzazione Componenti
    diagnosticCollection = vscode.languages.createDiagnosticCollection('pynt');
    analyzer = new analyzer_1.CodeAnalyzer(getServerUrl());
    decorator = new decorators_1.DiagnosticDecorator();
    let lastAnalysisType = 'all'; //--- MEMORIA DI STATO ---
    const fixProvider = vscode.languages.registerCodeActionsProvider('python', // <--- Solo stringa 'python' oppure array ['python']
    new FixProvider_1.PyntFixProvider(), {
        providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
    });
    context.subscriptions.push(fixProvider);
    // Comando: Re-Scan automatico dopo il Quick Fix
    const analyzeAfterFixCommand = vscode.commands.registerCommand('pynt.analyzeAfterFix', async (document) => {
        console.log("🔄 Fix applicato. Avvio ri-scansione automatica...");
        // 1. Piccolo ritardo per assicurarsi che VS Code abbia finito di aggiornare il testo
        await new Promise(resolve => setTimeout(resolve, 500));
        // 2. Lancia l'analisi completa (Security + Best + Fault)
        // Nota: Assicurati che analyzeDocument sia accessibile qui (fuori da activate o passata)
        // Se analyzeDocument è definita sotto, va bene.
        await analyzeDocument(document, lastAnalysisType);
    });
    context.subscriptions.push(analyzeAfterFixCommand);
    // 2. Status Bar Setup
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(shield) Pynt';
    statusBarItem.tooltip = 'Click per analizzare codice';
    statusBarItem.command = 'pynt.showAnalysisMenu';
    statusBarItem.show();
    // 3. REGISTRAZIONE COMANDI
    // Comando: Mostra Menu di Analisi
    const showMenuCommand = vscode.commands.registerCommand('pynt.showAnalysisMenu', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('Apri un file per avviare l\'analisi.');
            return;
        }
        // Menu di selezione
        const choice = await vscode.window.showQuickPick([
            {
                label: '$(shield) Analisi Sicurezza',
                description: 'Vulnerabilità (SQLi, XSS, Injection)',
                detail: 'Rileva problemi di sicurezza critici OWASP.',
                type: types_1.AnalysisType.SECURITY
            },
            {
                label: '$(sparkle) Best Practices',
                description: 'Clean Code & Stile',
                detail: 'Suggerimenti per migliorare la leggibilità e manutenibilità.',
                type: types_1.AnalysisType.BEST_PRACTICES
            },
            {
                label: '$(bug) Rilevamento Bug',
                description: 'Errori Logici & Runtime',
                detail: 'Trova potenziali crash, null pointer e loop infiniti.',
                type: types_1.AnalysisType.FAULT_DETECTION
            },
            {
                label: '$(checklist) Analisi Completa',
                description: 'Esegui tutti gli agenti',
                detail: 'Lancia Security + Best Practices + Fault Detection insieme.',
                type: 'all' // Cast necessario per gestire il tipo misto
            }
        ], {
            placeHolder: 'Seleziona il tipo di analisi Pynt da eseguire',
            matchOnDescription: true,
            matchOnDetail: true
        });
        if (choice) {
            lastAnalysisType = choice.type;
            await analyzeDocument(editor.document, choice.type);
        }
    });
    // Comando: Analizza file corrente (Scorciatoia)
    const analyzeCommand = vscode.commands.registerCommand('pynt.analyzeFile', async () => {
        vscode.commands.executeCommand('pynt.showAnalysisMenu');
    });
    // Comando: Pulisci tutto (Reset)
    const clearCommand = vscode.commands.registerCommand('pynt.clearDiagnostics', () => {
        diagnosticCollection.clear(); // Rimuove linee rosse
        decorator.clearDecorations(); // Rimuove popup belli
        statusBarItem.text = '$(shield) Pynt';
        statusBarItem.tooltip = 'Click per analizzare codice';
        vscode.window.showInformationMessage('Pynt: Analisi pulita.');
    });
    // Comando: Toggle Auto-Analisi al salvataggio
    const toggleAutoSaveCommand = vscode.commands.registerCommand('pynt.toggleAutoAnalysis', async () => {
        const config = vscode.workspace.getConfiguration('pynt');
        const currentSetting = config.get('autoAnalyzeOnSave', false);
        await config.update('autoAnalyzeOnSave', !currentSetting, vscode.ConfigurationTarget.Global);
        const status = !currentSetting ? 'ABILITATA' : 'DISABILITATA';
        vscode.window.showInformationMessage(`Pynt: Auto-analisi al salvataggio ${status}`);
    });
    // Comando: Copia testo negli appunti
    const copyCommand = vscode.commands.registerCommand('pynt.copyToClipboard', async (text) => {
        if (!text)
            return;
        try {
            await vscode.env.clipboard.writeText(text);
            vscode.window.showInformationMessage(' Analisi copiata negli appunti!');
        }
        catch (error) {
            vscode.window.showErrorMessage('Impossibile copiare il testo.');
        }
    });
    context.subscriptions.push(copyCommand); // Non dimenticare di aggiungerlo alle subscriptions!
    // 4. REGISTRAZIONE EVENTI (LISTENERS)
    // Al salvataggio del file
    const saveListener = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('pynt');
        if (config.get('autoAnalyzeOnSave', false)) {
            // Se attivo, lancia un'analisi completa o quella di default
            await analyzeDocument(document, 'all');
        }
    });
    // Al cambio di tab (Editor attivo)
    const editorChangeListener = vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
            // 1. Recupera l'URI del file appena aperto
            const uriString = editor.document.uri.toString();
            // 2. Controlla se abbiamo risultati in memoria per questo file
            const findingsForFile = globalFindingsMap.get(uriString.toLowerCase());
            if (findingsForFile) {
                console.log(`🔄 Ripristino decorazioni per: ${uriString}`);
                decorator.applyDecorations(editor, findingsForFile);
            }
            else {
                // Se non c'è nulla, pulisci (per evitare residui grafici)
                decorator.clearDecorations();
            }
        }
    });
    // Aggiungi tutto alla lista delle subscription per il cleanup automatico
    context.subscriptions.push(showMenuCommand, analyzeCommand, clearCommand, toggleAutoSaveCommand, saveListener, editorChangeListener, diagnosticCollection, statusBarItem, decorator // Importante: dispone anche il decorator
    );
}
// --- LOGICA DI ANALISI ---
async function analyzeDocument(document, analysisType) {
    // 1. Controllo supporto linguaggio
    if (!isSupported(document.languageId)) {
        vscode.window.showWarningMessage(`Pynt: Il linguaggio '${document.languageId}' non è supportato.`);
        return;
    }
    // 2. Feedback UI (Caricamento)
    const labels = {
        [types_1.AnalysisType.SECURITY]: 'Security',
        [types_1.AnalysisType.BEST_PRACTICES]: 'Best Practices',
        [types_1.AnalysisType.FAULT_DETECTION]: 'Fault Detection',
        'all': 'Completa'
    };
    const label = labels[analysisType] || 'Analisi';
    statusBarItem.text = `$(sync~spin) Pynt: ${label}...`;
    statusBarItem.tooltip = 'Analisi in corso, attendere...';
    // 3. Pulizia preventiva
    // Nota: globalFindingsMap è definita a livello globale in extension.ts
    globalFindingsMap.clear(); // <--- NUOVO: Pulisce memoria popup
    decorator.clearDecorations();
    diagnosticCollection.clear();
    FixProvider_1.diagnosticFixMap.clear();
    try {
        // 4. Preparazione Payload
        let typesToSend;
        if (analysisType === 'all') {
            typesToSend = [
                types_1.AnalysisType.SECURITY,
                types_1.AnalysisType.BEST_PRACTICES,
                types_1.AnalysisType.FAULT_DETECTION
            ];
        }
        else {
            typesToSend = [analysisType];
        }
        // Recupero Path Progetto
        let projectPath = null;
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
        if (workspaceFolder) {
            projectPath = workspaceFolder.uri.fsPath;
            console.log("Pynt: Project Path rilevato ->", projectPath);
        }
        // 5. CHIAMATA AL SERVER
        const response = await analyzer.analyze({
            code: document.getText(),
            language: document.languageId,
            filename: document.fileName,
            analysisTypes: typesToSend,
            projectPath: projectPath
        });
        // =========================================================
        // 6. SMISTAMENTO ERRORI MULTI-FILE (Logica Nuova)
        // =========================================================
        globalFindingsMap.clear();
        decorator.clearDecorations();
        diagnosticCollection.clear();
        FixProvider_1.diagnosticFixMap.clear();
        // Mappa temporanea per raggruppare i Diagnostic per file
        const diagMap = new Map();
        for (const finding of response.findings) {
            // A. Identifica il file giusto
            let targetUri;
            if (finding.file_path) {
                // Se è assoluto, usiamo l'helper per trovare l'URI aperto (gestisce C: vs c:)
                if (path.isAbsolute(finding.file_path)) {
                    targetUri = getCanonicalUri(finding.file_path);
                }
                // Se è relativo, uniamo e poi cerchiamo
                else if (projectPath) {
                    const fullPath = path.join(projectPath, finding.file_path);
                    targetUri = getCanonicalUri(fullPath);
                }
                else {
                    targetUri = document.uri;
                }
            }
            else {
                targetUri = document.uri;
            }
            const uriString = targetUri.toString();
            const lookupKey = uriString.toLowerCase();
            // B. Salva nella memoria globale per i Decorator (Popup)
            if (!globalFindingsMap.has(lookupKey)) {
                globalFindingsMap.set(lookupKey, []);
            }
            globalFindingsMap.get(lookupKey)?.push(finding);
            // C. Crea il Diagnostic (Linea Rossa)
            const range = new vscode.Range(Math.max(0, finding.line - 1), Math.max(0, finding.column), Math.max(0, finding.endLine - 1), Math.max(0, finding.endColumn));
            const severity = getSeverity(finding.severity);
            const diagnostic = new vscode.Diagnostic(range, finding.message, severity);
            diagnostic.code = finding.ruleId;
            diagnostic.source = `Pynt (${getShortLabel(finding.analysisType)})`;
            // Mappa Fix
            if (finding.executableFix) {
                FixProvider_1.diagnosticFixMap.set(diagnostic, finding.executableFix);
            }
            // Aggiungi alla mappa temporanea
            if (!diagMap.has(uriString)) {
                diagMap.set(uriString, []);
            }
            diagMap.get(uriString)?.push(diagnostic);
        }
        // D. Applica le linee rosse a tutti i file
        diagMap.forEach((diags, uriString) => {
            const uri = vscode.Uri.parse(uriString);
            diagnosticCollection.set(uri, diags);
        });
        // 7. APPLICAZIONE DECORATORS (Immediata per il file corrente)
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            const currentUri = activeEditor.document.uri.toString();
            // Prende dalla mappa globale solo i popup di QUESTO file
            const relevantFindings = globalFindingsMap.get(currentUri.toLowerCase());
            if (relevantFindings) {
                decorator.applyDecorations(activeEditor, relevantFindings);
            }
        }
        // 8. Aggiornamento UI Finale
        // Nota: response.findings esiste ancora, quindi questo codice funziona!
        const count = response.findings.length;
        if (count > 0) {
            statusBarItem.text = `$(warning) Pynt: ${count} issue${count > 1 ? 's' : ''}`;
            statusBarItem.tooltip = `Trovati ${count} problemi in tutto il progetto.`;
        }
        else {
            statusBarItem.text = `$(check) Pynt: Clean`;
            statusBarItem.tooltip = `Nessun problema trovato.`;
            vscode.window.setStatusBarMessage(` Pynt: Analisi completata. Clean!`, 4000);
        }
    }
    catch (error) {
        console.error("Pynt Analysis Error:", error);
        statusBarItem.text = '$(error) Pynt: Error';
        statusBarItem.tooltip = 'Errore analisi.';
        const errorMsg = error instanceof Error ? error.message : 'Unknown';
        vscode.window.showErrorMessage(`Errore Pynt: ${errorMsg}`);
    }
}
// --- UTILITIES ---
function isSupported(languageId) {
    // Lista linguaggi supportati da Semgrep/Pynt
    const supported = ['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'go', 'php', 'ruby', 'csharp'];
    return supported.includes(languageId);
}
function getSeverity(severityStr) {
    switch (severityStr?.toUpperCase()) {
        case 'ERROR': return vscode.DiagnosticSeverity.Error;
        case 'WARNING': return vscode.DiagnosticSeverity.Warning;
        case 'INFO': return vscode.DiagnosticSeverity.Information;
        default: return vscode.DiagnosticSeverity.Hint;
    }
}
function getShortLabel(type) {
    switch (type) {
        case types_1.AnalysisType.SECURITY: return 'Sec';
        case types_1.AnalysisType.BEST_PRACTICES: return 'Best';
        case types_1.AnalysisType.FAULT_DETECTION: return 'Fault';
        default: return 'Gen';
    }
}
function getServerUrl() {
    const config = vscode.workspace.getConfiguration('pynt');
    // Default a localhost se non configurato
    return config.get('serverUrl', 'http://localhost:8000');
}
function deactivate() {
    if (diagnosticCollection)
        diagnosticCollection.dispose();
    if (statusBarItem)
        statusBarItem.dispose();
    if (decorator)
        decorator.dispose();
}
// Helper per trovare l'URI "canonico" se il file è già aperto
function getCanonicalUri(filePath) {
    // Normalizziamo il path in ingresso (minuscolo e slash standard)
    const normalizedPath = path.resolve(filePath).toLowerCase();
    // Controlliamo tra i documenti di testo aperti
    for (const doc of vscode.workspace.textDocuments) {
        const docPath = path.resolve(doc.uri.fsPath).toLowerCase();
        if (docPath === normalizedPath) {
            return doc.uri; // Ritorniamo l'URI esatto usato da VS Code
        }
    }
    // Se non è aperto, creiamo un nuovo URI dal path
    return vscode.Uri.file(filePath);
}
//# sourceMappingURL=extension.js.map