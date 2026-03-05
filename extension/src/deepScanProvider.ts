import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Gestisce la Webview e la comunicazione per il Deep Scan.
 * Invia ora l'intero oggetto JSON (incluso il codice sorgente) alla Webview.
 */
export class DeepScanProvider {
    public static async run(context: vscode.ExtensionContext) {
        console.log('[DEBUG] === Avvio Procedura Deep Scan ===');

        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            console.error('[ERROR] Nessun editor attivo trovato.');
            vscode.window.showErrorMessage("Apri un file per eseguire il Deep Scan.");
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'deepScanReport',
            'Pynt: Deep Scan Audit',
            vscode.ViewColumn.Two,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        const htmlPath = path.join(context.extensionPath, 'views', 'deep_scan_report.html');
        if (!fs.existsSync(htmlPath)) {
            console.error(`[ERROR] HTML non trovato in: ${htmlPath}`);
            return;
        }
        panel.webview.html = fs.readFileSync(htmlPath, 'utf8');

        const code = editor.document.getText();
        const filePath = editor.document.fileName;
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || null;
        const languageId = editor.document.languageId;

        try {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Pynt: Investigazione Profonda in corso...",
                cancellable: false
            }, async () => {
                console.log('[NETWORK] Invio richiesta al backend...');
                
                const response = await fetch('http://localhost:8000/analyze/deep-scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: code,
                        file_path: filePath,
                        project_path: projectPath,
                        language: languageId
                    })
                });

                if (!response.ok) {
                    const errBody = await response.text();
                    throw new Error(`Server Error: ${response.status}`);
                }

                const data: any = await response.json();
                
                // NOTA: Inviamo l'intero oggetto 'data' invece di solo 'data.report'
                // Questo permette alla Webview di accedere anche a 'data.code' e 'data.file'
                if (data && data.report) {
                    console.log(`[DEBUG] Vulnerabilità LLM trovate: ${data.report.vulnerabilities?.length || 0}`);
                    panel.webview.postMessage(data); 
                    console.log('[DEBUG] Dati completi inviati alla Webview.');
                }
            });
        } catch (error: any) {
            console.error(`[CRITICAL ERROR] ${error.message}`);
            panel.webview.postMessage({ error: error.message });
            vscode.window.showErrorMessage(`Errore Deep Scan: ${error.message}`);
        }
    }
}