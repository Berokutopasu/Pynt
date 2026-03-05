// extension.ts
import * as vscode from 'vscode';
import { CodeAnalyzer } from './analyzer';
import { DiagnosticDecorator } from './decorators';
import { AnalysisType } from './types';
import { PyntFixProvider, diagnosticFixMap } from './FixProvider';
import * as path from 'path'
import { DeepScanProvider } from './deepScanProvider';
// Variabili Globali
let analyzer: CodeAnalyzer;
let decorator: DiagnosticDecorator;
let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;
//Mappa per ricordare i risultati di ogni file (URI string -> Lista Findings)
let globalFindingsMap = new Map<string, any[]>();

export function activate(context: vscode.ExtensionContext) {
    console.log('Pynt extension is now active!');

    // 1. Inizializzazione Componenti
    diagnosticCollection = vscode.languages.createDiagnosticCollection('pynt');
    analyzer = new CodeAnalyzer(getServerUrl());
    decorator = new DiagnosticDecorator();
    let lastAnalysisType = 'all'; //--- MEMORIA DI STATO ---
    const fixProvider = vscode.languages.registerCodeActionsProvider(
        'python', // <--- Solo stringa 'python' oppure array ['python']
        new PyntFixProvider(),
        {
            providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
        }
    );
    context.subscriptions.push(fixProvider);

    // Comando: Re-Scan automatico dopo il Quick Fix
    const analyzeAfterFixCommand = vscode.commands.registerCommand('pynt.analyzeAfterFix', async (document: vscode.TextDocument) => {
        console.log("Fix applicato. Avvio ri-scansione automatica...");
        
        // 1. Piccolo ritardo per assicurarsi che VS Code abbia finito di aggiornare il testo
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // 2. Lancia l'analisi completa (Security + Best + Fault)
        // Nota: Assicurati che analyzeDocument sia accessibile qui (fuori da activate o passata)
        // Se analyzeDocument è definita sotto, va bene.
        await analyzeDocument(document, lastAnalysisType as any);
    });

    context.subscriptions.push(analyzeAfterFixCommand);
     //DEEP SCAN COMMAND
    context.subscriptions.push(
        vscode.commands.registerCommand('pynt.runDeepScan', async () => {
            try {
                await DeepScanProvider.run(context);
            } catch (err) {
                vscode.window.showErrorMessage("Errore durante l'avvio del Deep Scan.");
            }
        })
    );
       context.subscriptions.push(diagnosticCollection);

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
                type: AnalysisType.SECURITY
            },
            {
                label: '$(sparkle) Best Practices',
                description: 'Clean Code & Stile',
                detail: 'Suggerimenti per migliorare la leggibilità e manutenibilità.',
                type: AnalysisType.BEST_PRACTICES
            },
            {
                label: '$(bug) Rilevamento Bug',
                description: 'Errori Logici & Runtime',
                detail: 'Trova potenziali crash, null pointer e loop infiniti.',
                type: AnalysisType.FAULT_DETECTION
            },
            {
                label: '$(checklist) Analisi Completa',
                description: 'Esegui tutti gli agenti',
                detail: 'Lancia Security + Best Practices + Fault Detection insieme.',
                type: 'all' as any // Cast necessario per gestire il tipo misto
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
        diagnosticCollection.clear();      // Rimuove linee rosse
        decorator.clearDecorations();      // Rimuove popup belli
        statusBarItem.text = '$(shield) Pynt';
        statusBarItem.tooltip = 'Click per analizzare codice';
        vscode.window.showInformationMessage('Pynt: Analisi pulita.');
    });

    // Comando: Toggle Auto-Analisi al salvataggio
    const toggleAutoSaveCommand = vscode.commands.registerCommand('pynt.toggleAutoAnalysis', async () => {
        const config = vscode.workspace.getConfiguration('pynt');
        const currentSetting = config.get<boolean>('autoAnalyzeOnSave', false);
        await config.update('autoAnalyzeOnSave', !currentSetting, vscode.ConfigurationTarget.Global);
        
        const status = !currentSetting ? 'ABILITATA' : 'DISABILITATA';
        vscode.window.showInformationMessage(`Pynt: Auto-analisi al salvataggio ${status}`);
    });
    // Comando: Copia testo negli appunti
    const copyCommand = vscode.commands.registerCommand('pynt.copyToClipboard', async (text: string) => {
        if (!text) return;
        try {
            await vscode.env.clipboard.writeText(text);
            vscode.window.showInformationMessage(' Analisi copiata negli appunti!');
        } catch (error) {
            vscode.window.showErrorMessage('Impossibile copiare il testo.');
        }
    });

    context.subscriptions.push(copyCommand); // Non dimenticare di aggiungerlo alle subscriptions!
    // 4. REGISTRAZIONE EVENTI (LISTENERS)

    // Al salvataggio del file
    const saveListener = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('pynt');
        if (config.get<boolean>('autoAnalyzeOnSave', false)) {
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
            } else {
                // Se non c'è nulla, pulisci (per evitare residui grafici)
                decorator.clearDecorations();
            }
        }
    });

    // Aggiungi tutto alla lista delle subscription per il cleanup automatico
    context.subscriptions.push(
        showMenuCommand,
        analyzeCommand,
        clearCommand,
        toggleAutoSaveCommand,
        saveListener,
        editorChangeListener,
        diagnosticCollection,
        statusBarItem,
        decorator // Importante: dispone anche il decorator
    );
}

// --- LOGICA DI ANALISI ---


async function analyzeDocument(document: vscode.TextDocument, analysisType: AnalysisType | 'all') {
    // 1. Controllo supporto linguaggio
    if (!isSupported(document.languageId)) {
        vscode.window.showWarningMessage(`Pynt: Il linguaggio '${document.languageId}' non è supportato.`);
        return;
    }

    // 2. Feedback UI (Caricamento)
    const labels: Record<string, string> = {
        [AnalysisType.SECURITY]: 'Security',
        [AnalysisType.BEST_PRACTICES]: 'Best Practices',
        [AnalysisType.FAULT_DETECTION]: 'Fault Detection',
        'all': 'Completa'
    };
    const label = labels[analysisType] || 'Analisi';
    
    statusBarItem.text = `$(sync~spin) Pynt: ${label}...`;
    statusBarItem.tooltip = 'Analisi in corso, attendere...';

    // 3. Pulizia preventiva
    // Nota: globalFindingsMap è definita a livello globale in extension.ts
    globalFindingsMap.clear();      // <--- NUOVO: Pulisce memoria popup
    decorator.clearDecorations();
    diagnosticCollection.clear();
    diagnosticFixMap.clear();

    try {
        // 4. Preparazione Payload
        let typesToSend: AnalysisType[];
        if (analysisType === 'all') {
            typesToSend = [
                AnalysisType.SECURITY,
                AnalysisType.BEST_PRACTICES,
                AnalysisType.FAULT_DETECTION
            ];
        } else {
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
        diagnosticFixMap.clear();
        // Mappa temporanea per raggruppare i Diagnostic per file
        const diagMap = new Map<string, vscode.Diagnostic[]>();

        for (const finding of response.findings) {

            // Salta finding esplicitamente marcati come falsi positivi dall'LLM
            if (finding.isFalsePositive) continue;

            // A. Identifica il file giusto
            let targetUri: vscode.Uri;
            
           if (finding.file_path) {
                // Pulisci il file_path dal prefisso /app/ se presente
                let cleanPath = finding.file_path;
                if (cleanPath.startsWith('/app/')) {
                    cleanPath = cleanPath.substring(5); // Rimuovi "/app/"
                    console.log(`[PYNT DEBUG] Cleaned file_path: ${finding.file_path} → ${cleanPath}`);
                }
                
                // Se è assoluto, usiamo l'helper per trovare l'URI aperto (gestisce C: vs c:)
                if (path.isAbsolute(cleanPath)) {
                    targetUri = getCanonicalUri(cleanPath);
                } 
                // Se è relativo, uniamo e poi cerchiamo
                else if (projectPath) {
                    const fullPath = path.join(projectPath, cleanPath);
                    targetUri = getCanonicalUri(fullPath);
                } 
                else {
                    targetUri = document.uri;
                }
            } else {
                targetUri = document.uri;
            }
            
            const originalUriString = targetUri.toString();
            const uriString = cleanBackendUri(originalUriString);
            
            // Se l'URI è stato pulito, ricreiamo il targetUri 
            if (uriString !== originalUriString) {
                try {
                    targetUri = vscode.Uri.parse(uriString);
                    console.log(`[PYNT DEBUG] Using cleaned URI: ${targetUri.toString()}`);
                } catch (error) {
                    console.error(`[PYNT DEBUG] Failed to parse cleaned URI: ${uriString}, error: ${error}`);
                    // Fallback all'URI originale
                    targetUri = vscode.Uri.parse(originalUriString);
                }
            }
            
            const lookupKey = uriString.toLowerCase();
            // B. Salva nella memoria globale per i Decorator (Popup)
            if (!globalFindingsMap.has(lookupKey)) {
                globalFindingsMap.set(lookupKey, []);
            }
            globalFindingsMap.get(lookupKey)?.push(finding);

            // C. Crea il Diagnostic (Linea Rossa)
            const range = new vscode.Range(
                Math.max(0, finding.line - 1),
                Math.max(0, finding.column),
                Math.max(0, finding.endLine - 1),
                Math.max(0, finding.endColumn)
            );

            const severity = getSeverity(finding.severity);
            const diagnostic = new vscode.Diagnostic(range, finding.message, severity);
            
            diagnostic.code = finding.ruleId;
            diagnostic.source = `Pynt (${getShortLabel(finding.analysisType)})`;

            // Mappa Fix
            if (finding.executableFix) {
                diagnosticFixMap.set(diagnostic, finding.executableFix);
            }

            // Aggiungi alla mappa temporanea
            const finalUriString = targetUri.toString(); // Usa l'URI finale (eventualmente pulito)
            if (!diagMap.has(finalUriString)) {
                diagMap.set(finalUriString, []);
            }
            diagMap.get(finalUriString)?.push(diagnostic);
            console.log(`[PYNT DEBUG] Added diagnostic for ${finalUriString}: ${finding.message}`);
        }

        console.log(`[PYNT DEBUG] Total diagnostics created: ${Array.from(diagMap.values()).reduce((sum, arr) => sum + arr.length, 0)}`);
        console.log(`[PYNT DEBUG] Files with diagnostics: ${Array.from(diagMap.keys())}`);

        // D. Applica le linee rosse a tutti i file
        diagMap.forEach((diags, uriString) => {
            const uri = vscode.Uri.parse(uriString);
            console.log(`[PYNT DEBUG] Setting diagnostics for ${uriString}, count: ${diags.length}`);
            console.log(`[PYNT DEBUG] Diagnostics:`, diags.map(d => ({message: d.message, range: d.range})));
            diagnosticCollection.set(uri, diags);
            console.log(`[PYNT DEBUG] Diagnostics set successfully for ${uriString}`);
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
        } else {
            statusBarItem.text = `$(check) Pynt: Clean`;
            statusBarItem.tooltip = `Nessun problema trovato.`;
            vscode.window.setStatusBarMessage(` Pynt: Analisi completata. Clean!`, 4000);
        }

    } catch (error) {
        console.error("Pynt Analysis Error:", error);
        statusBarItem.text = '$(error) Pynt: Error';
        statusBarItem.tooltip = 'Errore analisi.';
        
        const errorMsg = error instanceof Error ? error.message : 'Unknown';
        vscode.window.showErrorMessage(`Errore Pynt: ${errorMsg}`);
    }
}

// --- UTILITIES ---

function isSupported(languageId: string): boolean {
    // Lista linguaggi supportati da Semgrep/Pynt
    const supported = ['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'go', 'php', 'ruby', 'csharp'];
    return supported.includes(languageId);
}

function getSeverity(severityStr: string): vscode.DiagnosticSeverity {
    switch (severityStr?.toUpperCase()) {
        case 'ERROR': return vscode.DiagnosticSeverity.Error;
        case 'WARNING': return vscode.DiagnosticSeverity.Warning;
        case 'INFO': return vscode.DiagnosticSeverity.Information;
        default: return vscode.DiagnosticSeverity.Hint;
    }
}

// Funzione per pulire URI problematici dal backend  
function cleanBackendUri(uriString: string): string {
    console.log(`[PYNT DEBUG] Original URI: ${uriString}`);
    
    let cleanString = uriString;
    
    // Rimuovi prefisso /app/ se presente
    if (cleanString.includes('/app/')) {
        cleanString = cleanString.replace('/app/', '');
        console.log(`[PYNT DEBUG] Removed /app/: ${cleanString}`);
    }
    
    // Decodifica URL encoding (es: c%3A -> c:)
    try {
        cleanString = decodeURIComponent(cleanString);
        console.log(`[PYNT DEBUG] Decoded URI: ${cleanString}`);
    } catch (e) {
        console.log(`[PYNT DEBUG] URI decode failed:`, e);
    }
    
    return cleanString;
}

function getShortLabel(type: AnalysisType): string {
    switch (type) {
        case AnalysisType.SECURITY: return 'Sec';
        case AnalysisType.BEST_PRACTICES: return 'Best';
        case AnalysisType.FAULT_DETECTION: return 'Fault';
        default: return 'Gen';
    }
}

function getServerUrl(): string {
    const config = vscode.workspace.getConfiguration('pynt');
    // Default a localhost se non configurato
    return config.get<string>('serverUrl', 'http://localhost:8000');
}

export function deactivate() {
    if (diagnosticCollection) diagnosticCollection.dispose();
    if (statusBarItem) statusBarItem.dispose();
    if (decorator) decorator.dispose();
}

// Helper per trovare l'URI "canonico" se il file è già aperto
function getCanonicalUri(filePath: string): vscode.Uri {
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