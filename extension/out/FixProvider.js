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
    provideCodeActions(document, range, context, token) {
        const actions = [];
        for (const diagnostic of context.diagnostics) {
            const fixCode = exports.diagnosticFixMap.get(diagnostic);
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
                    if (line.trim().length === 0)
                        return line;
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
                const rangeToReplace = new vscode.Range(new vscode.Position(startLineIndex, 0), // Inizio riga errore (colonna 0)
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
exports.PyntFixProvider = PyntFixProvider;
//# sourceMappingURL=FixProvider.js.map