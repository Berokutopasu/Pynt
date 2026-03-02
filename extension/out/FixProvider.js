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
exports.PyntFixProvider = exports.diagnosticFixMap = void 0;
const vscode = __importStar(require("vscode"));
exports.diagnosticFixMap = new Map();
class PyntFixProvider {
    async provideCodeActions(document, range, context) {
        const actions = [];
        const diagnostic = context.diagnostics[0];
        if (!diagnostic)
            return [];
        const rawFix = exports.diagnosticFixMap.get(diagnostic);
        if (!rawFix)
            return [];
        const { imports, code } = this.manualParse(rawFix);
        if (!code && !imports)
            return [];
        const symbolRange = await this.findEnclosingSymbolRange(document, diagnostic.range);
        const isFunctionFix = code.trim().startsWith('def ');
        const action = new vscode.CodeAction(isFunctionFix ? `✨ Pynt: AST Mode` : `✨ Pynt: Line Mode`, vscode.CodeActionKind.QuickFix);
        const edit = new vscode.WorkspaceEdit();
        if (code) {
            if (isFunctionFix && symbolRange) {
                edit.replace(document.uri, symbolRange, code);
            }
            else {
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
                        if (!nextLineText)
                            continue;
                        // Se la riga nel file inizia con uno dei prefissi del fix, è ridondante
                        const isRedundant = fixPrefixes.some(prefix => nextLineText.startsWith(prefix));
                        if (isRedundant) {
                            linesToOverwrite = i;
                        }
                        else {
                            // Se troviamo una riga che NON c'entra nulla, ci fermiamo per non cancellare troppo
                            break;
                        }
                    }
                }
                // Range che "mangia" la riga corrente + quelle ridondanti identificate
                const replaceRange = new vscode.Range(lineObj.range.start, document.lineAt(lineIndex + linesToOverwrite).range.end);
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
    manualParse(raw) {
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
    async findEnclosingSymbolRange(document, range) {
        try {
            const symbols = await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider', document.uri);
            if (!symbols)
                return null;
            const search = (syms) => {
                for (const s of syms) {
                    if (s.range.contains(range)) {
                        if (s.kind === vscode.SymbolKind.Function || s.kind === vscode.SymbolKind.Method)
                            return s.range;
                        if (s.children) {
                            const res = search(s.children);
                            if (res)
                                return res;
                        }
                    }
                }
                return null;
            };
            return search(symbols);
        }
        catch (e) {
            return null;
        }
    }
}
exports.PyntFixProvider = PyntFixProvider;
//# sourceMappingURL=FixProvider.js.map