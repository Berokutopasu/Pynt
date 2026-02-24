"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SeverityLevel = exports.AnalysisType = void 0;
// types.ts
var AnalysisType;
(function (AnalysisType) {
    AnalysisType["SECURITY"] = "security";
    AnalysisType["BEST_PRACTICES"] = "best_practices";
    AnalysisType["FAULT_DETECTION"] = "fault_detection";
})(AnalysisType || (exports.AnalysisType = AnalysisType = {}));
var SeverityLevel;
(function (SeverityLevel) {
    SeverityLevel["ERROR"] = "ERROR";
    SeverityLevel["WARNING"] = "WARNING";
    SeverityLevel["INFO"] = "INFO";
})(SeverityLevel || (exports.SeverityLevel = SeverityLevel = {}));
//# sourceMappingURL=types.js.map