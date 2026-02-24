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
exports.PyntCodeActionProvider = void 0;
// codeActions.ts
const vscode = __importStar(require("vscode"));
class PyntCodeActionProvider {
    constructor(findingsMap) {
        this.findingsMap = findingsMap;
    }
    provideCodeActions(document, range, context, token) {
        // 1. Filtra solo le diagnostiche di Pynt
        const pyntDiagnostics = context.diagnostics.filter(diag => diag.source && diag.source.startsWith('Pynt'));
        if (pyntDiagnostics.length === 0) {
            return [];
        }
        const actions = [];
        // 2. Recupera i finding salvati per questo file
        const fileFindings = this.findingsMap.get(document.uri.toString()) || [];
        // 3. Per ogni errore trovato sotto il cursore...
        for (const diagnostic of pyntDiagnostics) {
            // Cerca il finding originale che corrisponde alla riga dell'errore
            const finding = fileFindings.find(f => (f.line - 1) === diagnostic.range.start.line);
            if (finding) {
                // Crea l'azione "Apri Spiegazione Completa"
                const action = new vscode.CodeAction(`📝 Pynt: Leggi spiegazione completa`, vscode.CodeActionKind.QuickFix);
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
exports.PyntCodeActionProvider = PyntCodeActionProvider;
//# sourceMappingURL=codeActions.js.map