import * as vscode from 'vscode';

export const diagnosticFixMap = new Map<vscode.Diagnostic, string>();

export class PyntFixProvider implements vscode.CodeActionProvider {
    async provideCodeActions(document: vscode.TextDocument, range: vscode.Range | vscode.Selection, context: vscode.CodeActionContext): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        const diagnostic = context.diagnostics[0];
        if (!diagnostic) return [];

        const rawFix = diagnosticFixMap.get(diagnostic);
        if (!rawFix) return [];

        const { imports, code } = this.manualParse(rawFix);
        if (!code && !imports) return [];

        const symbolRange = await this.findEnclosingSymbolRange(document, diagnostic.range);
        const isFunctionFix = code.trim().startsWith('def ');

        const action = new vscode.CodeAction(
            isFunctionFix ? `✨ Pynt: AST Mode` : `✨ Pynt: Line Mode`,
            vscode.CodeActionKind.QuickFix
        );
        const edit = new vscode.WorkspaceEdit();

        if (code) {
            if (isFunctionFix && symbolRange) {
                edit.replace(document.uri, symbolRange, code);
            } else {
                const lineIndex = diagnostic.range.start.line;
                const lineObj = document.lineAt(lineIndex);
                const indentation = lineObj.text.substring(0, lineObj.firstNonWhitespaceCharacterIndex);

                // --- LOGICA DI RIDONDANZA GENERICA ---
                const fixLines = code.split('\n').map(l => l.trim()).filter(l => l.length > 0);
                
                // Estraggono i prefissi del fix (es. "query =" o "cursor.execute")
                const fixPrefixes = fixLines.map(line => {
                    const firstPart = line.split(/[(\s=]/)[0]; // Prende la parola prima di '(', '=' o spazio
                    return firstPart.length > 2 ? firstPart : line.substring(0, 10); // Evita parole troppo corte
                });

                let linesToOverwrite = 0;
                // Controlla le 3 righe successive per vedere se sono "sovrascritte" dal fix
                for (let i = 1; i <= 3; i++) {
                    const nextIdx = lineIndex + i;
                    if (nextIdx < document.lineCount) {
                        const nextLineText = document.lineAt(nextIdx).text.trim();
                        if (!nextLineText) continue;

                        // Se la riga nel file inizia con uno dei prefissi del fix, è ridondante
                        const isRedundant = fixPrefixes.some(prefix => nextLineText.startsWith(prefix));
                        
                        if (isRedundant) {
                            linesToOverwrite = i;
                        } else {
                            // Se troviamo una riga che NON c'entra nulla, ci fermiamo per non cancellare troppo
                            break; 
                        }
                    }
                }

                // Range che "mangia" la riga corrente + quelle ridondanti identificate
                const replaceRange = new vscode.Range(
                    lineObj.range.start,
                    document.lineAt(lineIndex + linesToOverwrite).range.end
                );

                const indentedCode = fixLines.map(l => indentation + l).join('\n');
                edit.replace(document.uri, replaceRange, indentedCode);
            }
        }

        // Gestione Import (Riga 0)
        if (imports) {
            const fullText = document.getText();
            const importLines = imports.split('\n').map(l => l.trim()).filter(l => l.length > 0);
            let importBlock = "";
            for (const line of importLines) {
                const moduleName = line.split(' ').pop() || "";
                if (!fullText.includes(moduleName)) {
                    importBlock += (line.startsWith('import') || line.startsWith('from') ? line : `import ${line}`) + '\n';
                }
            }
            if (importBlock) {
                edit.insert(document.uri, new vscode.Position(0, 0), importBlock);
            }
        }

        action.edit = edit;
        action.diagnostics = [diagnostic];
        action.isPreferred = true;
        action.command = { command: 'pynt.analyzeAfterFix', title: 'Re-scan', arguments: [document] };
        actions.push(action);

        return actions;
    }

    private manualParse(raw: string) {
        const cleanRaw = raw.replace(/```python|```py|```/gi, '').trim();
        const impMatch = cleanRaw.match(/IMPORTS:([\s\S]*?)(?=FIX:|$)/i);
        const fixMatch = cleanRaw.match(/FIX:([\s\S]*?)(?=CODE_EXAMPLE:|REFERENCES:|$)/i);
        let imports = impMatch ? impMatch[1].trim() : "";
        let code = fixMatch ? fixMatch[1].trim() : "";
        
        if (!code && !imports && cleanRaw.length > 0) {
            const lines = cleanRaw.split('\n');
            imports = lines.filter(l => l.trim().startsWith('import') || l.trim().startsWith('from')).join('\n');
            code = lines.filter(l => l.trim().length > 0 && !l.trim().startsWith('import') && !l.trim().startsWith('from')).join('\n');
        }
        return { imports, code };
    }

    private async findEnclosingSymbolRange(document: vscode.TextDocument, range: vscode.Range): Promise<vscode.Range | null> {
        try {
            const symbols = await vscode.commands.executeCommand<vscode.DocumentSymbol[]>('vscode.executeDocumentSymbolProvider', document.uri);
            if (!symbols) return null;
            const search = (syms: vscode.DocumentSymbol[]): vscode.Range | null => {
                for (const s of syms) {
                    if (s.range.contains(range)) {
                        if (s.kind === vscode.SymbolKind.Function || s.kind === vscode.SymbolKind.Method) return s.range;
                        if (s.children) {
                            const res = search(s.children);
                            if (res) return res;
                        }
                    }
                }
                return null;
            };
            return search(symbols);
        } catch (e) { return null; }
    }
}