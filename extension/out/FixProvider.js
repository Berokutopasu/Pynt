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
        for (const diagnostic of context.diagnostics) {
            let rawFix = exports.diagnosticFixMap.get(diagnostic);
            if (!rawFix)
                continue;
            const action = new vscode.CodeAction('✨ Pynt: Applica Fix IA', vscode.CodeActionKind.QuickFix);
            const edit = new vscode.WorkspaceEdit();
            // 1. PULIZIA TOTALE (Via backticks e spazi inutili)
            rawFix = rawFix.replace(/```python|```py|```/gi, '').trim();
            // 2. ESTRAZIONE LOGICA (Indipendente dai tag se necessario)
            let importLines = [];
            let fixLines = [];
            // Proviamo a estrarre con i tag
            const importMatch = rawFix.match(/\[IMPORTS\]\s*([\s\S]*?)(?=\[FIX\]|$)/i);
            const fixMatch = rawFix.match(/\[FIX\]\s*([\s\S]*?)$/i);
            if (importMatch || fixMatch) {
                importLines = importMatch ? importMatch[1].split('\n') : [];
                fixLines = fixMatch ? fixMatch[1].split('\n') : [];
            }
            else {
                // FALLBACK GENERICO: Se l'LLM ignora i tag, separiamo noi le righe che iniziano con import
                const allLines = rawFix.split('\n');
                importLines = allLines.filter(l => l.trim().startsWith('import') || l.trim().startsWith('from'));
                fixLines = allLines.filter(l => !l.trim().startsWith('import') && !l.trim().startsWith('from') && !l.trim().startsWith('['));
            }
            // 3. APPLICAZIONE IMPORT IN CIMA (RIGA 0)
            const fullText = document.getText();
            importLines.forEach(line => {
                const trimmed = line.trim();
                if (trimmed && !fullText.includes(trimmed)) {
                    edit.insert(document.uri, new vscode.Position(0, 0), trimmed + '\n');
                }
            });
            // 4. SOSTITUZIONE CHIRURGICA (SOLO LA RIGA DEL DIAGNOSTIC)
            const lineObj = document.lineAt(diagnostic.range.start.line);
            const indentation = lineObj.text.substring(0, lineObj.firstNonWhitespaceCharacterIndex);
            const finalFix = fixLines
                .map(l => l.trim())
                .filter(l => l.length > 0 && !l.startsWith('#') && !l.startsWith('['))
                .map(l => indentation + l)
                .join('\n');
            if (finalFix) {
                edit.replace(document.uri, lineObj.range, finalFix);
            }
            action.edit = edit;
            action.isPreferred = true;
            action.command = { command: 'pynt.analyzeAfterFix', title: 'Re-scan', arguments: [document] };
            actions.push(action);
        }
        return actions;
    }
}
exports.PyntFixProvider = PyntFixProvider;
//# sourceMappingURL=FixProvider.js.map