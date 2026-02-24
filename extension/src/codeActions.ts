// codeActions.ts
import * as vscode from 'vscode';
import { Finding } from './types';

export class PyntCodeActionProvider implements vscode.CodeActionProvider {
    private findingsMap: Map<string, Finding[]>;

    constructor(findingsMap: Map<string, Finding[]>) {
        this.findingsMap = findingsMap;
    }

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<(vscode.Command | vscode.CodeAction)[]> {
        
        // 1. Filtra solo le diagnostiche di Pynt
        const pyntDiagnostics = context.diagnostics.filter(diag => diag.source && diag.source.startsWith('Pynt'));
        if (pyntDiagnostics.length === 0) {
            return [];
        }

        const actions: vscode.CodeAction[] = [];

        // 2. Recupera i finding salvati per questo file
        const fileFindings = this.findingsMap.get(document.uri.toString()) || [];

        // 3. Per ogni errore trovato sotto il cursore...
        for (const diagnostic of pyntDiagnostics) {
            // Cerca il finding originale che corrisponde alla riga dell'errore
            const finding = fileFindings.find(f => 
                (f.line - 1) === diagnostic.range.start.line
            );

            if (finding) {
                // Crea l'azione "Apri Spiegazione Completa"
                const action = new vscode.CodeAction(
                    `📝 Pynt: Leggi spiegazione completa`, 
                    vscode.CodeActionKind.QuickFix
                );
                
                // Collega l'azione al comando che apre il pannello
                action.command = {
                    command: 'pynt.openDetailsPanel',
                    title: 'Apri Dettagli',
                    arguments: [finding] // Passiamo tutto l'oggetto finding al pannello
                };
                
                action.isPreferred = true; // La mette in cima alla lista (blu)
                actions.push(action);
            }
        }

        return actions;
    }
}