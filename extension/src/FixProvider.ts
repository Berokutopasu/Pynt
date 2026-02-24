import * as vscode from 'vscode';

export const diagnosticFixMap = new Map<vscode.Diagnostic, string>();

export class PyntFixProvider implements vscode.CodeActionProvider {

    provideCodeActions(
        document: vscode.TextDocument, 
        range: vscode.Range | vscode.Selection, 
        context: vscode.CodeActionContext, 
        token: vscode.CancellationToken
    ): vscode.CodeAction[] {
        
        const actions: vscode.CodeAction[] = [];

        for (const diagnostic of context.diagnostics) {
            const fixCode = diagnosticFixMap.get(diagnostic);
            
            if (fixCode) {
                const action = new vscode.CodeAction('✨ Pynt: Applica Fix IA', vscode.CodeActionKind.QuickFix);
                const edit = new vscode.WorkspaceEdit();

                // --- LOGICA DI SOSTITUZIONE PULITA ---

                const startLineIndex = diagnostic.range.start.line;
                const startLineObj = document.lineAt(startLineIndex);
                
                // 1. Recupera l'indentazione originale (spazi a sinistra)
                const indentation = startLineObj.text.substring(0, startLineObj.firstNonWhitespaceCharacterIndex);

                // 2. Prepara il codice del fix
                // Dividiamo il fix in righe per analizzarlo
                const fixLines = fixCode.split('\n');
                const numberOfLinesInFix = fixLines.length;

                // Applichiamo l'indentazione a ogni riga del fix (se non ce l'ha già)
                const cleanFix = fixLines.map((line, index) => {
                    // Non indentare righe vuote
                    if (line.trim().length === 0) return line;
                    // Se la riga inizia già con spazi, assumiamo sia corretta, altrimenti indentiamo
                    if (!line.startsWith(' ') && !line.startsWith('\t')) {
                        return indentation + line;
                    }
                    return line;
                }).join('\n');

                // 3. CALCOLO RANGE ESTESO (Il segreto della pulizia)
                // Se il fix è di 2 righe, sovrascriviamo la riga dell'errore + la successiva.
                // Questo elimina la vecchia riga 'cursor.execute' che rimaneva appesa.
                
                // Calcoliamo l'indice della riga finale da sovrascrivere
                let endLineIndex = startLineIndex + numberOfLinesInFix - 1;
                
                // Safety check: non andare oltre la fine del file
                if (endLineIndex >= document.lineCount) {
                    endLineIndex = document.lineCount - 1;
                }

                // Creiamo il range che copre dall'inizio della prima riga alla fine dell'ultima riga coinvolta
                const rangeToReplace = new vscode.Range(
                    new vscode.Position(startLineIndex, 0), // Inizio riga errore (colonna 0)
                    document.lineAt(endLineIndex).range.end // Fine riga finale
                );

                // 4. APPLICAZIONE
                edit.replace(document.uri, rangeToReplace, cleanFix);

                // -------------------------------------------

                action.edit = edit;
                action.isPreferred = true; 

                // Trigger per ri-scansionare automaticamente
                action.command = {
                    command: 'pynt.analyzeAfterFix',
                    title: 'Rianalizza codice',
                    arguments: [document] 
                };
                
                actions.push(action);
            }
        }

        return actions;
    }
}