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
                // Controlla le 3 righe PRECEDENTI per rimuovere righe ridondanti sopra la diagnostica
                let startOffset = 0;
                for (let i = 1; i <= 3; i++) {
                    const prevIdx = lineIndex - i;
                    if (prevIdx < 0)
                        break;
                    const prevLineText = document.lineAt(prevIdx).text.trim();
                    if (!prevLineText || prevLineText.startsWith('#'))
                        break;
                    const isRedundant = fixPrefixes.some(prefix => prevLineText.startsWith(prefix));
                    if (isRedundant) {
                        startOffset = i;
                    }
                    else {
                        break;
                    }
                }
                // Range che "mangia" le righe ridondanti sopra + la riga corrente + quelle ridondanti sotto
                const replaceRange = new vscode.Range(document.lineAt(lineIndex - startOffset).range.start, document.lineAt(lineIndex + linesToOverwrite).range.end);
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
        "Questo è un parser manuale per estrarre le sezioni IMPORTS e FIX dal testo grezzo, senza usare regex complesse. Si basa su keyword e delimitatori semplici.";
        const cleanRaw = raw.replace(/```python|```py|```/gi, '').trim();
        const impMatch = cleanRaw.match(/IMPORTS:([\s\S]*?)(?=FIX:|$)/i);
        const fixMatch = cleanRaw.match(/FIX:([\s\S]*?)(?=CODE_EXAMPLE:|REFERENCES:|$)/i);
        let imports = impMatch ? impMatch[1].trim() : ""; // Sezione "IMPORTS" è opzionale, quindi potrebbe non esserci
        let code = fixMatch ? fixMatch[1].trim() : ""; //Idem per FIX, trim per rimuovere spazi vuoti indesiderati
        if (!code && !imports && cleanRaw.length > 0) {
            const lines = cleanRaw.split('\n');
            imports = lines.filter(l => l.trim().startsWith('import') || l.trim().startsWith('from')).join('\n');
            code = lines.filter(l => l.trim().length > 0 && !l.trim().startsWith('import') && !l.trim().startsWith('from')).join('\n');
        }
        // Hoisting: estrae import annidati nel corpo del codice e li porta a livello modulo
        if (code) {
            const hoisted = [];
            const remaining = [];
            for (const line of code.split('\n')) {
                const trimmed = line.trim();
                if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
                    hoisted.push(trimmed);
                }
                else {
                    remaining.push(line);
                }
            }
            if (hoisted.length > 0) {
                imports = [imports, ...hoisted].filter(s => s.trim()).join('\n');
                code = remaining.join('\n').trim();
            }
        }
        return { imports, code };
    }
    // Questa funzione cerca il simbolo più interno (funzione o metodo) che contiene l'errore, per sostituirlo completamente con il fix. 
    // Se non trova nulla, ritorna null e il fix verrà applicato in modalità "lineare".
    async findEnclosingSymbolRange(document, range) {
        try {
            // Ottiene la lista dei simboli (funzioni, classi, ecc.) nel documento
            const symbols = await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider', document.uri);
            if (!symbols)
                return null;
            // Funzione ricorsiva per cercare il simbolo più interno che contiene l'errore
            const search = (syms) => {
                for (const s of syms) { // Controlla se l'errore è dentro il range del simbolo
                    if (s.range.contains(range)) { // Se è una funzione o un metodo, ritorna il suo range per sovrascriverlo completamente
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