// decorators.ts
import * as vscode from 'vscode';
import { Finding, SeverityLevel, AnalysisType } from './types';

export class DiagnosticDecorator {
  private errorDecorationType: vscode.TextEditorDecorationType;
  private warningDecorationType: vscode.TextEditorDecorationType;
  private infoDecorationType: vscode.TextEditorDecorationType;
  
  // Cache per salvare le decorazioni per ogni file aperto
  private currentDecorations: Map<string, vscode.DecorationOptions[]>;

  constructor() {
    this.currentDecorations = new Map();

    // --- 1. DEFINIZIONE STILI ---
    this.errorDecorationType = vscode.window.createTextEditorDecorationType({
      borderWidth: '0 0 2px 0',
      borderStyle: 'solid',
      borderColor: new vscode.ThemeColor('editorError.foreground'),
      backgroundColor: 'rgba(255, 0, 0, 0.1)',
      overviewRulerColor: new vscode.ThemeColor('editorError.foreground'),
      overviewRulerLane: vscode.OverviewRulerLane.Right
    });

    this.warningDecorationType = vscode.window.createTextEditorDecorationType({
      borderWidth: '0 0 2px 0',
      borderStyle: 'solid',
      borderColor: new vscode.ThemeColor('editorWarning.foreground'),
      backgroundColor: 'rgba(255, 165, 0, 0.08)',
      overviewRulerColor: new vscode.ThemeColor('editorWarning.foreground'),
      overviewRulerLane: vscode.OverviewRulerLane.Right
    });

    this.infoDecorationType = vscode.window.createTextEditorDecorationType({
      borderWidth: '0 0 1px 0',
      borderStyle: 'dotted',
      borderColor: new vscode.ThemeColor('editorInfo.foreground'),
      overviewRulerColor: new vscode.ThemeColor('editorInfo.foreground'),
      overviewRulerLane: vscode.OverviewRulerLane.Right
    });
  }

  // --- 2. APPLICAZIONE DECORAZIONI ---

  applyDecorations(editor: vscode.TextEditor, findings: Finding[]) {
    console.log(`[DECORATOR DEBUG] applyDecorations chiamato con ${findings.length} findings`);
    
    const errorDecorations: vscode.DecorationOptions[] = [];
    const warningDecorations: vscode.DecorationOptions[] = [];
    const infoDecorations: vscode.DecorationOptions[] = [];

    const findingsByLine = new Map<number, Finding[]>();

    for (const finding of findings) {
      console.log(`[DECORATOR DEBUG] Processing finding:`, {
        line: finding.line,
        message: finding.message.substring(0, 50) + '...',
        hasEducationalExplanation: !!finding.educationalExplanation,
        hasSuggestedFix: !!finding.suggestedFix,
        hasCodeExample: !!finding.codeExample
      });
      
      const lineKey = finding.line;
      if (!findingsByLine.has(lineKey)) {
        findingsByLine.set(lineKey, []);
      }
      findingsByLine.get(lineKey)!.push(finding);
    }

    for (const [lineNum, lineFindings] of findingsByLine.entries()) {
      
      const primaryFinding = lineFindings[0];

      const range = new vscode.Range(
        primaryFinding.line - 1,
        primaryFinding.column-1,
        primaryFinding.endLine - 1,
        Math.max(primaryFinding.endColumn, primaryFinding.column )
      );
      
      //const icon = this.getIconForType(primaryFinding.analysisType);
      
      const countLabel = lineFindings.length > 1 
        ? ` (${lineFindings.length} issues)` 
        : '';

      // Crea hover message che include TUTTI i findings di quella riga
      const hoverMessage = this.createCombinedHoverMessage(lineFindings);
    
      const decoration: vscode.DecorationOptions = {
        range,
        hoverMessage,
        renderOptions: {
          after: {//${icon}
            contentText: ` ${countLabel}`, 
            color: new vscode.ThemeColor('editorCodeLens.foreground'),
            fontWeight: 'italic',
            fontStyle: '0 0 0 1em'
          }
        }
      };

      switch (primaryFinding.severity) {
        case SeverityLevel.ERROR:
          errorDecorations.push(decoration);
          break;
        case SeverityLevel.WARNING:
          warningDecorations.push(decoration);
          break;
        case SeverityLevel.INFO:
        default:
          infoDecorations.push(decoration);
          break;
      }
    }

    editor.setDecorations(this.errorDecorationType, errorDecorations);
    editor.setDecorations(this.warningDecorationType, warningDecorations);
    editor.setDecorations(this.infoDecorationType, infoDecorations);

    this.currentDecorations.set(editor.document.uri.toString(), [
      ...errorDecorations,
      ...warningDecorations,
      ...infoDecorations
    ]);
  }

  updateDecorations(editor: vscode.TextEditor) {
    const decorations = this.currentDecorations.get(editor.document.uri.toString());
    if (!decorations) { return; }
  }

  // --- 3. HELPER PRIVATI ---

  // Pulisce il codice dai backtick che l'LLM potrebbe aver inserito
  private cleanCodeBlock(code: string): string {
    if (!code) return "";
    return code
        .replace(/```python/gi, '') // Rimuove ```python
        .replace(/```/g, '')        // Rimuove ``` generici
        .trim();                    // Rimuove spazi vuoti inizio/fine
  }

  private createCopyLink(finding: Finding): string {
    const lines = [
        `[Pynt Analysis] ${this.formatAnalysisType(finding.analysisType)}`,
        `Severity: ${finding.severity}`,
        `Message: ${finding.message}`,
        ``,
        `--- EXPLANATION ---`,
        finding.educationalExplanation || "N/A",
        ``,
        `--- SUGGESTED FIX ---`,
        finding.suggestedFix || "N/A",
        ``,
        `--- CODE EXAMPLE ---`,
        this.cleanCodeBlock(finding.codeExample || "N/A")
    ];

    if (finding.references && finding.references.length > 0) {
        lines.push(``, `--- REFERENCES ---`, ...finding.references);
    }

    const fullText = lines.join('\n');

    // 1. Convertiamo in stringa JSON l'array di argomenti
    const jsonString = JSON.stringify([fullText]);

    // 2. Codifichiamo per URL standard
    let encodedArgs = encodeURIComponent(jsonString);

    // 3. Le parentesi tonde non vengono codificate da encodeURIComponent, 
    // ma rompono i link Markdown [text](command:...). Dobbiamo forzarle.
    encodedArgs = encodedArgs
        .replace(/\(/g, '%28')
        .replace(/\)/g, '%29');

    return `[$(copy) Copia Analisi](command:pynt.copyToClipboard?${encodedArgs})`;
  }

  // --- 4. GENERAZIONE DEL POPUP (HOVER) ---

  private createCombinedHoverMessage(findings: Finding[]): vscode.MarkdownString {
    const md = new vscode.MarkdownString();
    md.supportHtml = true;
    md.isTrusted = true;
    md.supportThemeIcons = true;

    // Caso singolo: delega al metodo singolo
    if (findings.length === 1) {
      return this.createSingleHoverMessage(findings[0]);
    }

    // Caso Multiplo: Intestazione Globale
    md.appendMarkdown(`### ⚠️ ${findings.length} Issues Trovati su Questa Riga\n\n`);
    md.appendMarkdown(`---\n\n`);

    findings.forEach((finding, index) => {
      const copyLink = this.createCopyLink(finding);
      //const icon = this.getIconForType(finding.analysisType);
      
      // Header Numerato per ogni finding - ${icon}
      md.appendMarkdown(`### ${index + 1}.  ${this.formatAnalysisType(finding.analysisType)} &nbsp;&nbsp; ${copyLink}\n\n`);
      
      md.appendMarkdown(`**${finding.message}**\n\n`);

      md.appendMarkdown(`📚 **Spiegazione:** `);
      if (finding.educationalExplanation && finding.educationalExplanation !== 'Nessun contenuto disponibile.') {
        md.appendMarkdown(`${finding.educationalExplanation}\n\n`);
      } else {
        md.appendMarkdown(`*Nessun contenuto disponibile.*\n\n`);
      }

      md.appendMarkdown(`💡 **Fix:** `);
      if (finding.suggestedFix && finding.suggestedFix !== 'Nessun contenuto disponibile.') {
        md.appendMarkdown(`${finding.suggestedFix}\n\n`);
      } else {
        md.appendMarkdown(`*Nessuna soluzione disponibile.*\n\n`);
      }

      // --- FIX CRITICO: Uso di cleanCodeBlock e appendCodeblock ---
      if (finding.codeExample && finding.codeExample !== 'Nessun contenuto disponibile.') {
        md.appendMarkdown(`💻 **Esempio:**\n`);
        const safeCode = this.cleanCodeBlock(finding.codeExample);
        // appendCodeblock gestisce i backtick automaticamente, prevenendo rotture del markdown
        md.appendCodeblock(safeCode, 'python'); 
        md.appendMarkdown(`\n`); // Spaziatura dopo il codice
      } else {
        md.appendMarkdown(`💻 **Esempio:** *Nessun esempio disponibile.*\n\n`);
      }
      // -----------------------------------------------------------

      md.appendMarkdown(`*Rule: ${finding.ruleId}*\n\n`);
      
      // Separatore tra i findings (tranne l'ultimo)
      if (index < findings.length - 1) {
        md.appendMarkdown(`---\n\n`);
      }
    });

    return md;
  }

  private createSingleHoverMessage(finding: Finding): vscode.MarkdownString {
    const md = new vscode.MarkdownString();
    md.supportHtml = true;
    md.isTrusted = true;
    md.supportThemeIcons = true;

    const copyLink = this.createCopyLink(finding);
    //const icon = this.getIconForType(finding.analysisType); 
    //${icon}
    md.appendMarkdown(`###  ${this.formatAnalysisType(finding.analysisType)} &nbsp;&nbsp; ${copyLink}\n\n`);

    md.appendMarkdown(`**Semgrep Message:** ${finding.message}\n\n`);
    md.appendMarkdown(`---\n\n`);

    md.appendMarkdown(`### 📚 Spiegazione LLM\n\n`);
    if (finding.educationalExplanation && finding.educationalExplanation !== 'Nessun contenuto disponibile.') {
      md.appendMarkdown(`${finding.educationalExplanation}\n\n`);
    } else {
      md.appendMarkdown(`*Nessun contenuto disponibile.*\n\n`);
    }

    md.appendMarkdown(`### 🛠️ Soluzione\n\n`);
    if (finding.suggestedFix && finding.suggestedFix !== 'Nessun contenuto disponibile.') {
      md.appendMarkdown(`${finding.suggestedFix}\n\n`);
    } else {
      md.appendMarkdown(`*Nessuna soluzione disponibile.*\n\n`);
    }

    md.appendMarkdown(`### 💻 Esempio\n\n`);
    if (finding.codeExample && finding.codeExample !== 'Nessun contenuto disponibile.') {
      const safeCode = this.cleanCodeBlock(finding.codeExample);
      md.appendCodeblock(safeCode, 'python');
      md.appendMarkdown(`\n`);
    } else {
      md.appendMarkdown(`*Nessun esempio disponibile.*\n\n`);
    }
    // -----------------------------

    if (finding.references && finding.references.length > 0) {
      md.appendMarkdown(`### 📖 Riferimenti\n\n`);
      finding.references.forEach(ref => {
        const cleanRef = ref.replace(/\)+$/, '');
        md.appendMarkdown(`- [${cleanRef}](${cleanRef})\n`);
      });
      md.appendMarkdown(`\n`);
    }

    md.appendMarkdown(`---\n`);
    md.appendMarkdown(`*Rule ID: ${finding.ruleId}*`);

    return md;
  }

  // --- 5. UTILITY ---

  private formatAnalysisType(type: AnalysisType): string {
    switch (type) {
      case AnalysisType.SECURITY: return 'Sicurezza';
      case AnalysisType.BEST_PRACTICES: return 'Best Practices';
      case AnalysisType.FAULT_DETECTION: return 'Rilevamento Bug';
      default: return 'Analisi';
    }
  }


  clearDecorations() {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      editor.setDecorations(this.errorDecorationType, []);
      editor.setDecorations(this.warningDecorationType, []);
      editor.setDecorations(this.infoDecorationType, []);
    }
    this.currentDecorations.clear();
  }

  dispose() {
    this.errorDecorationType.dispose();
    this.warningDecorationType.dispose();
    this.infoDecorationType.dispose();
  }
}