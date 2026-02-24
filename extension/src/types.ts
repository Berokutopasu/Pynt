// types.ts
export enum AnalysisType {
  SECURITY = 'security',
  BEST_PRACTICES = 'best_practices',
  FAULT_DETECTION = 'fault_detection'
}

export enum SeverityLevel {
  ERROR = 'ERROR',
  WARNING = 'WARNING',
  INFO = 'INFO'
}

export interface AnalysisRequest {
  code: string;
  language: string;
  filename: string;
  analysisTypes: AnalysisType[];
  projectPath?: string | null;
}

export interface Finding {
  line: number;
  column: number;
  endLine: number;
  endColumn: number;
  severity: SeverityLevel;
  message: string;
  educationalExplanation: string;
  suggestedFix?: string;
  codeExample?: string;
  references?: string[];
  analysisType: AnalysisType;
  ruleId: string;
  isFalsePositive?: boolean;
  executableFix?: string;
  file_path?: string; 
}


export interface AnalysisResponse {
  findings: Finding[];
  analysisTime: number;
  language: string;
  timestamp: string;
}

export interface AgentResponse {
  analysisType: AnalysisType;
  findings: Finding[];
  processingTime: number;
}

export interface ServerConfig {
  url: string;
  timeout: number;
}