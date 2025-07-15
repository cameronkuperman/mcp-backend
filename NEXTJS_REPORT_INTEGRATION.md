# Next.js Medical Report Integration Guide

Complete implementation for medical report generation in Next.js applications.

## 1. Report Service

Create `services/reportService.ts`:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_ORACLE_API_URL || 'http://localhost:8000';

// Types
export interface ReportAnalyzeRequest {
  user_id?: string;
  context: {
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    symptom_focus?: string;
    time_frame?: {
      start?: string;
      end?: string;
    };
    target_audience?: 'self' | 'primary_care' | 'specialist' | 'emergency';
  };
  available_data?: {
    quick_scan_ids?: string[];
    deep_dive_ids?: string[];
    photo_session_ids?: string[];
  };
}

export interface ReportAnalyzeResponse {
  recommended_endpoint: string;
  recommended_type: string;
  reasoning: string;
  confidence: number;
  report_config: any;
  analysis_id: string;
  status: 'success' | 'error';
}

export const reportService = {
  // Step 1: Analyze what type of report to generate
  async analyzeReport(request: ReportAnalyzeRequest): Promise<ReportAnalyzeResponse> {
    const response = await fetch(`${API_BASE_URL}/api/report/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) throw new Error('Failed to analyze report type');
    return response.json();
  },

  // Step 2: Generate specific report types
  async generateComprehensive(analysisId: string, userId?: string) {
    const response = await fetch(`${API_BASE_URL}/api/report/comprehensive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId, user_id: userId }),
    });

    if (!response.ok) throw new Error('Failed to generate comprehensive report');
    return response.json();
  },

  async generateUrgentTriage(analysisId: string, userId?: string) {
    const response = await fetch(`${API_BASE_URL}/api/report/urgent-triage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId, user_id: userId }),
    });

    if (!response.ok) throw new Error('Failed to generate urgent triage report');
    return response.json();
  },

  async generateSymptomTimeline(analysisId: string, userId?: string, symptomFocus?: string) {
    const response = await fetch(`${API_BASE_URL}/api/report/symptom-timeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        analysis_id: analysisId, 
        user_id: userId,
        symptom_focus: symptomFocus 
      }),
    });

    if (!response.ok) throw new Error('Failed to generate symptom timeline');
    return response.json();
  },

  async generatePhotoProgression(analysisId: string, userId?: string) {
    const response = await fetch(`${API_BASE_URL}/api/report/photo-progression`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId, user_id: userId }),
    });

    if (!response.ok) throw new Error('Failed to generate photo progression report');
    return response.json();
  },

  async generateSpecialist(analysisId: string, userId?: string, specialty?: string) {
    const response = await fetch(`${API_BASE_URL}/api/report/specialist`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        analysis_id: analysisId, 
        user_id: userId,
        specialty 
      }),
    });

    if (!response.ok) throw new Error('Failed to generate specialist report');
    return response.json();
  },

  async generateAnnualSummary(analysisId: string, userId: string, year?: number) {
    const response = await fetch(`${API_BASE_URL}/api/report/annual-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        analysis_id: analysisId, 
        user_id: userId,
        year 
      }),
    });

    if (!response.ok) throw new Error('Failed to generate annual summary');
    return response.json();
  },

  // Helper to generate any report type based on analysis
  async generateReport(analysis: ReportAnalyzeResponse, userId?: string) {
    const endpoint = analysis.recommended_endpoint;
    
    // Call the appropriate endpoint based on recommendation
    switch (analysis.recommended_type) {
      case 'comprehensive':
        return this.generateComprehensive(analysis.analysis_id, userId);
      case 'urgent_triage':
        return this.generateUrgentTriage(analysis.analysis_id, userId);
      case 'symptom_timeline':
        return this.generateSymptomTimeline(
          analysis.analysis_id, 
          userId,
          analysis.report_config.primary_focus
        );
      case 'photo_progression':
        return this.generatePhotoProgression(analysis.analysis_id, userId);
      case 'specialist_focused':
        return this.generateSpecialist(analysis.analysis_id, userId);
      case 'annual_summary':
        return this.generateAnnualSummary(analysis.analysis_id, userId!);
      default:
        return this.generateComprehensive(analysis.analysis_id, userId);
    }
  }
};
```

## 2. Report Generation Hook

Create `hooks/useReportGeneration.ts`:

```typescript
import { useState, useCallback } from 'react';
import { reportService, ReportAnalyzeRequest } from '@/services/reportService';
import { useAuth } from '@/hooks/useAuth';

interface ReportGenerationState {
  isAnalyzing: boolean;
  isGenerating: boolean;
  analysis: any | null;
  report: any | null;
  error: string | null;
}

export const useReportGeneration = () => {
  const { user } = useAuth();
  const [state, setState] = useState<ReportGenerationState>({
    isAnalyzing: false,
    isGenerating: false,
    analysis: null,
    report: null,
    error: null,
  });

  const generateReport = useCallback(async (request: ReportAnalyzeRequest) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }));

    try {
      // Step 1: Analyze what type of report to generate
      const analysis = await reportService.analyzeReport({
        ...request,
        user_id: request.user_id || user?.id,
      });

      setState(prev => ({ 
        ...prev, 
        analysis, 
        isAnalyzing: false,
        isGenerating: true 
      }));

      // Step 2: Generate the recommended report
      const report = await reportService.generateReport(
        analysis, 
        request.user_id || user?.id
      );

      setState(prev => ({ 
        ...prev, 
        report, 
        isGenerating: false 
      }));

      return { analysis, report };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate report';
      setState(prev => ({ 
        ...prev, 
        error: errorMessage,
        isAnalyzing: false,
        isGenerating: false 
      }));
      throw error;
    }
  }, [user]);

  const reset = useCallback(() => {
    setState({
      isAnalyzing: false,
      isGenerating: false,
      analysis: null,
      report: null,
      error: null,
    });
  }, []);

  return {
    ...state,
    generateReport,
    reset,
  };
};
```

## 3. Report Generation UI Component

Create `components/ReportGenerator.tsx`:

```typescript
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, AlertCircle, Calendar, Camera, Brain, Stethoscope, Clock } from 'lucide-react';
import { useReportGeneration } from '@/hooks/useReportGeneration';
import { ReportViewer } from './ReportViewer';

interface ReportGeneratorProps {
  symptomFocus?: string;
  quickScanIds?: string[];
  deepDiveIds?: string[];
  onComplete?: (report: any) => void;
}

export const ReportGenerator: React.FC<ReportGeneratorProps> = ({
  symptomFocus,
  quickScanIds = [],
  deepDiveIds = [],
  onComplete,
}) => {
  const { isAnalyzing, isGenerating, analysis, report, error, generateReport } = useReportGeneration();
  const [purpose, setPurpose] = useState<string>('symptom_specific');
  const [targetAudience, setTargetAudience] = useState<string>('self');

  const reportTypeIcons = {
    comprehensive: <FileText className="w-6 h-6" />,
    urgent_triage: <AlertCircle className="w-6 h-6 text-red-500" />,
    symptom_timeline: <Clock className="w-6 h-6" />,
    photo_progression: <Camera className="w-6 h-6" />,
    specialist_focused: <Stethoscope className="w-6 h-6" />,
    annual_summary: <Calendar className="w-6 h-6" />,
  };

  const handleGenerateReport = async () => {
    try {
      const result = await generateReport({
        context: {
          purpose: purpose as any,
          symptom_focus: symptomFocus,
          target_audience: targetAudience as any,
        },
        available_data: {
          quick_scan_ids: quickScanIds,
          deep_dive_ids: deepDiveIds,
        },
      });

      if (onComplete && result.report) {
        onComplete(result.report);
      }
    } catch (err) {
      // Error handled by hook
    }
  };

  if (report) {
    return <ReportViewer report={report} onBack={() => window.location.reload()} />;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Generate Medical Report</h2>
        <p className="text-gray-600">
          Create a comprehensive medical report from your health data
        </p>
      </div>

      {/* Report Configuration */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Report Configuration</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Purpose
            </label>
            <select
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 
                focus:ring-purple-500 focus:border-transparent"
            >
              <option value="symptom_specific">Specific Symptom Analysis</option>
              <option value="annual_checkup">Annual Health Summary</option>
              <option value="specialist_referral">Specialist Referral</option>
              <option value="emergency">Urgent/Emergency</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Audience
            </label>
            <select
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 
                focus:ring-purple-500 focus:border-transparent"
            >
              <option value="self">Personal Use</option>
              <option value="primary_care">Primary Care Doctor</option>
              <option value="specialist">Specialist</option>
              <option value="emergency">Emergency Department</option>
            </select>
          </div>

          {symptomFocus && (
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-purple-700">
                <strong>Symptom Focus:</strong> {symptomFocus}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Available Data Summary */}
      <div className="bg-gray-50 rounded-xl p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Available Data</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <Brain className="w-5 h-5 text-purple-500" />
            <div>
              <p className="font-medium">{quickScanIds.length} Quick Scans</p>
              <p className="text-sm text-gray-600">Symptom assessments</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-500" />
            <div>
              <p className="font-medium">{deepDiveIds.length} Deep Dives</p>
              <p className="text-sm text-gray-600">Detailed analyses</p>
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Result */}
      {analysis && !isGenerating && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl shadow-sm p-6 mb-6"
        >
          <div className="flex items-center gap-3 mb-4">
            {reportTypeIcons[analysis.recommended_type as keyof typeof reportTypeIcons]}
            <div>
              <h3 className="text-lg font-semibold">
                Recommended: {analysis.recommended_type.replace('_', ' ').toUpperCase()}
              </h3>
              <p className="text-sm text-gray-600">{analysis.reasoning}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span>Confidence: {Math.round(analysis.confidence * 100)}%</span>
          </div>
        </motion.div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerateReport}
        disabled={isAnalyzing || isGenerating}
        className="w-full py-4 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 
          hover:from-purple-700 hover:to-blue-700 disabled:from-gray-400 
          disabled:to-gray-500 text-white font-medium transition-all duration-200
          flex items-center justify-center gap-3"
      >
        {isAnalyzing ? (
          <>
            <Spinner className="w-5 h-5 animate-spin" />
            Analyzing your data...
          </>
        ) : isGenerating ? (
          <>
            <Spinner className="w-5 h-5 animate-spin" />
            Generating {analysis?.recommended_type.replace('_', ' ')} report...
          </>
        ) : (
          <>
            <FileText className="w-5 h-5" />
            Generate Medical Report
          </>
        )}
      </button>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
        >
          <p className="text-red-700">{error}</p>
        </motion.div>
      )}
    </div>
  );
};
```

## 4. Report Viewer Component

Create `components/ReportViewer.tsx`:

```typescript
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Share2, Mail, FileText, AlertCircle } from 'lucide-react';
import { generatePDF } from '@/utils/pdfGenerator';

interface ReportViewerProps {
  report: any;
  onBack?: () => void;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({ report, onBack }) => {
  const [activeSection, setActiveSection] = useState('summary');

  const exportPDF = async () => {
    const pdf = await generatePDF(report);
    pdf.save(`medical-report-${report.report_id}.pdf`);
  };

  const shareReport = async () => {
    if (navigator.share) {
      await navigator.share({
        title: 'Medical Report',
        text: report.report_data.executive_summary.one_page_summary,
      });
    }
  };

  const emailReport = () => {
    const subject = `Medical Report - ${new Date().toLocaleDateString()}`;
    const body = encodeURIComponent(report.report_data.executive_summary.one_page_summary);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  // Render different report types
  if (report.report_type === 'urgent_triage') {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-red-50 border-2 border-red-300 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle className="w-8 h-8 text-red-600" />
            <h1 className="text-2xl font-bold text-red-900">Urgent Medical Summary</h1>
          </div>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-red-800 mb-2">Immediate Action Required:</h3>
              <p className="text-xl font-bold text-red-900">
                {report.triage_summary.recommended_action}
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-red-800 mb-2">Critical Symptoms:</h3>
              <ul className="space-y-2">
                {report.triage_summary.vital_symptoms?.map((symptom: any, idx: number) => (
                  <li key={idx} className="bg-white p-3 rounded-lg">
                    <p className="font-medium">{symptom.symptom} - {symptom.severity}</p>
                    <p className="text-sm text-gray-700">Duration: {symptom.duration}</p>
                    {symptom.red_flags?.length > 0 && (
                      <p className="text-sm text-red-600 mt-1">
                        ⚠️ {symptom.red_flags.join(', ')}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-red-800 mb-2">Tell the Doctor:</h3>
              <ul className="list-disc list-inside space-y-1">
                {report.triage_summary.what_to_tell_doctor?.map((point: string, idx: number) => (
                  <li key={idx} className="text-gray-800">{point}</li>
                ))}
              </ul>
            </div>

            <div className="pt-4 border-t border-red-200">
              <button
                onClick={exportPDF}
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white 
                  font-medium rounded-lg transition-colors"
              >
                Download Emergency Summary
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Standard report viewer for other types
  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold text-gray-900">
            Medical Report
          </h1>
          <div className="flex items-center gap-3">
            <button
              onClick={exportPDF}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white 
                rounded-lg transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export PDF
            </button>
            <button
              onClick={shareReport}
              className="px-4 py-2 border border-gray-300 hover:bg-gray-50 
                rounded-lg transition-colors flex items-center gap-2"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
            <button
              onClick={emailReport}
              className="px-4 py-2 border border-gray-300 hover:bg-gray-50 
                rounded-lg transition-colors flex items-center gap-2"
            >
              <Mail className="w-4 h-4" />
              Email
            </button>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>Report Type: {report.report_type.replace('_', ' ')}</span>
          <span>•</span>
          <span>Generated: {new Date(report.generated_at).toLocaleString()}</span>
          <span>•</span>
          <span>ID: {report.report_id}</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6">
          {Object.keys(report.report_data).map((section) => (
            <button
              key={section}
              onClick={() => setActiveSection(section)}
              className={`pb-3 px-1 border-b-2 transition-colors ${
                activeSection === section
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <motion.div
        key={activeSection}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-xl shadow-sm p-6"
      >
        <ReportSection 
          sectionName={activeSection} 
          sectionData={report.report_data[activeSection]} 
        />
      </motion.div>

      {/* Back Button */}
      {onBack && (
        <div className="mt-8">
          <button
            onClick={onBack}
            className="text-gray-600 hover:text-gray-900 transition-colors"
          >
            ← Back to health data
          </button>
        </div>
      )}
    </div>
  );
};

// Component to render different section types
const ReportSection: React.FC<{ sectionName: string; sectionData: any }> = ({ 
  sectionName, 
  sectionData 
}) => {
  // Render executive summary
  if (sectionName === 'executive_summary') {
    return (
      <div className="prose max-w-none">
        <div className="bg-purple-50 p-6 rounded-lg mb-6">
          <h3 className="text-lg font-semibold mb-3">One Page Summary</h3>
          <p className="whitespace-pre-wrap">{sectionData.one_page_summary}</p>
        </div>
        
        {sectionData.chief_complaints?.length > 0 && (
          <div className="mb-6">
            <h4 className="font-semibold mb-2">Chief Complaints</h4>
            <ul className="list-disc list-inside space-y-1">
              {sectionData.chief_complaints.map((item: string, idx: number) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        
        {sectionData.key_findings?.length > 0 && (
          <div className="mb-6">
            <h4 className="font-semibold mb-2">Key Findings</h4>
            <ul className="list-disc list-inside space-y-1">
              {sectionData.key_findings.map((item: string, idx: number) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  // Generic renderer for other sections
  return (
    <div className="prose max-w-none">
      {Object.entries(sectionData).map(([key, value]) => (
        <div key={key} className="mb-6">
          <h4 className="font-semibold mb-2">
            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </h4>
          {Array.isArray(value) ? (
            <ul className="list-disc list-inside space-y-1">
              {value.map((item: any, idx: number) => (
                <li key={idx}>
                  {typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
                </li>
              ))}
            </ul>
          ) : typeof value === 'object' ? (
            <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto">
              {JSON.stringify(value, null, 2)}
            </pre>
          ) : (
            <p>{value}</p>
          )}
        </div>
      ))}
    </div>
  );
};
```

## 5. Integration Examples

### From Quick Scan Results

```typescript
// In QuickScanResults component
const handleGenerateReport = () => {
  // Navigate to report generation with context
  router.push({
    pathname: '/report/generate',
    query: {
      symptom: analysis.primaryCondition,
      scanId: scan_id,
    },
  });
};

// Add button to results
<button
  onClick={handleGenerateReport}
  className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 
    to-blue-600 hover:from-purple-700 hover:to-blue-700 
    text-white font-medium transition-all"
>
  <FileText className="w-5 h-5 mr-2" />
  Generate Medical Report
</button>
```

### Report Generation Page

```typescript
// pages/report/generate.tsx
import { useRouter } from 'next/router';
import { ReportGenerator } from '@/components/ReportGenerator';

export default function GenerateReportPage() {
  const router = useRouter();
  const { symptom, scanId, diveId } = router.query;

  const quickScanIds = scanId ? [scanId as string] : [];
  const deepDiveIds = diveId ? [diveId as string] : [];

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <ReportGenerator
          symptomFocus={symptom as string}
          quickScanIds={quickScanIds}
          deepDiveIds={deepDiveIds}
          onComplete={(report) => {
            // Could navigate to a dedicated report view
            console.log('Report generated:', report);
          }}
        />
      </div>
    </div>
  );
}
```

## 6. PDF Generation Utility

Create `utils/pdfGenerator.ts`:

```typescript
import jsPDF from 'jspdf';

export const generatePDF = async (report: any) => {
  const pdf = new jsPDF();
  const pageWidth = pdf.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - (margin * 2);
  let yPosition = margin;

  // Header
  pdf.setFontSize(20);
  pdf.text('Medical Report', margin, yPosition);
  yPosition += 10;

  pdf.setFontSize(10);
  pdf.setTextColor(100);
  pdf.text(`Generated: ${new Date(report.generated_at).toLocaleString()}`, margin, yPosition);
  pdf.text(`Report ID: ${report.report_id}`, margin, yPosition + 5);
  yPosition += 15;

  // Executive Summary
  pdf.setFontSize(16);
  pdf.setTextColor(0);
  pdf.text('Executive Summary', margin, yPosition);
  yPosition += 10;

  pdf.setFontSize(11);
  const summaryLines = pdf.splitTextToSize(
    report.report_data.executive_summary.one_page_summary, 
    contentWidth
  );
  pdf.text(summaryLines, margin, yPosition);
  yPosition += summaryLines.length * 5 + 10;

  // Add more sections as needed...

  return pdf;
};
```

## Testing

```typescript
// Test report generation flow
const testReportGeneration = async () => {
  // 1. Analyze
  const analysis = await reportService.analyzeReport({
    context: {
      purpose: 'symptom_specific',
      symptom_focus: 'recurring headaches',
    },
    user_id: 'test-user-123',
  });
  
  console.log('Recommended:', analysis.recommended_type);
  
  // 2. Generate
  const report = await reportService.generateReport(analysis, 'test-user-123');
  console.log('Report generated:', report.report_id);
};
```

This implementation provides a complete medical report generation system for Next.js with proper TypeScript support, error handling, and user-friendly UI components.