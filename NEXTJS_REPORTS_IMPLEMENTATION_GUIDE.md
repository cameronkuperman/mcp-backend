# Next.js Medical Reports Implementation Guide

A practical guide to implement the comprehensive medical report system in your Next.js frontend.

## Overview

The medical report system uses a two-stage process:
1. **Analyze** - Determines what type of report to generate based on context
2. **Generate** - Creates the actual report (specialist, time-based, or comprehensive)

## 1. TypeScript Types

Create `types/reports.ts`:

```typescript
export interface ReportAnalysisRequest {
  user_id?: string;
  context: {
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    symptom_focus?: string;
    time_frame?: { start: string; end: string };
    target_audience?: 'self' | 'primary_care' | 'specialist' | 'emergency';
  };
  available_data?: {
    quick_scan_ids?: string[];
    deep_dive_ids?: string[];
    photo_session_ids?: string[];
  };
}

export interface SpecialistReportRequest {
  analysis_id: string;
  user_id?: string;
  specialty?: string;
}

export interface TimePeriodReportRequest {
  user_id: string;
  include_wearables?: boolean;
}

export interface MedicalReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  report_data: any;
  confidence_score?: number;
  status: 'success' | 'error';
}

export interface ReportAnalysisResponse {
  recommended_endpoint: string;
  recommended_type: string;
  reasoning: string;
  confidence: number;
  report_config: any;
  analysis_id: string;
  status: 'success' | 'error';
}
```

## 2. API Service

Create `lib/api/reports.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const reportApi = {
  // Step 1: Analyze what report to generate
  async analyzeReport(request: ReportAnalysisRequest): Promise<ReportAnalysisResponse> {
    const res = await fetch(`${API_BASE}/api/report/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error('Failed to analyze report');
    return res.json();
  },

  // Step 2: Generate the actual report
  async generateReport(endpoint: string, request: any): Promise<MedicalReport> {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error('Failed to generate report');
    return res.json();
  },

  // Direct specialist report generation
  async generateSpecialistReport(
    specialty: 'cardiology' | 'neurology' | 'psychiatry' | 'dermatology' | 
    'gastroenterology' | 'endocrinology' | 'pulmonology',
    analysisId: string,
    userId?: string
  ): Promise<MedicalReport> {
    return this.generateReport(`/api/report/${specialty}`, {
      analysis_id: analysisId,
      user_id: userId,
      specialty
    });
  },

  // Time-based reports
  async generate30DayReport(userId: string): Promise<MedicalReport> {
    const res = await fetch(`${API_BASE}/api/report/30-day`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) throw new Error('Failed to generate 30-day report');
    return res.json();
  },

  async generateAnnualReport(userId: string): Promise<MedicalReport> {
    const res = await fetch(`${API_BASE}/api/report/annual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) throw new Error('Failed to generate annual report');
    return res.json();
  },

  // Get user's reports
  async getUserReports(userId: string): Promise<any[]> {
    const res = await fetch(`${API_BASE}/api/reports?user_id=${userId}`);
    if (!res.ok) throw new Error('Failed to fetch reports');
    return res.json();
  },

  // Get specific report
  async getReport(reportId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
    if (!res.ok) throw new Error('Failed to fetch report');
    return res.json();
  }
};
```

## 3. Report Generator Component

Create `components/ReportGenerator.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { reportApi } from '@/lib/api/reports';

interface ReportGeneratorProps {
  userId: string;
  quickScanIds?: string[];
  deepDiveIds?: string[];
  onComplete?: (report: any) => void;
}

export function ReportGenerator({ userId, quickScanIds = [], deepDiveIds = [], onComplete }: ReportGeneratorProps) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'select' | 'analyzing' | 'generating' | 'complete'>('select');
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [generatedReport, setGeneratedReport] = useState<any>(null);

  // Configuration
  const [reportType, setReportType] = useState<'symptom' | 'time' | 'specialist'>('symptom');
  const [symptomFocus, setSymptomFocus] = useState('');
  const [selectedSpecialty, setSelectedSpecialty] = useState('cardiology');

  const handleGenerateSymptomReport = async () => {
    setLoading(true);
    setError(null);
    setStep('analyzing');

    try {
      // Step 1: Analyze
      const analysis = await reportApi.analyzeReport({
        user_id: userId,
        context: {
          purpose: 'symptom_specific',
          symptom_focus: symptomFocus,
        },
        available_data: {
          quick_scan_ids: quickScanIds,
          deep_dive_ids: deepDiveIds,
        }
      });

      setAnalysisResult(analysis);
      setStep('generating');

      // Step 2: Generate based on AI recommendation
      const report = await reportApi.generateReport(
        analysis.recommended_endpoint,
        { analysis_id: analysis.analysis_id, user_id: userId }
      );

      setGeneratedReport(report);
      setStep('complete');
      onComplete?.(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
      setStep('select');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateTimeReport = async (period: '30-day' | 'annual') => {
    setLoading(true);
    setError(null);
    setStep('generating');

    try {
      const report = period === '30-day' 
        ? await reportApi.generate30DayReport(userId)
        : await reportApi.generateAnnualReport(userId);

      setGeneratedReport(report);
      setStep('complete');
      onComplete?.(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
      setStep('select');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSpecialistReport = async () => {
    setLoading(true);
    setError(null);
    setStep('analyzing');

    try {
      // First analyze to get analysis_id
      const analysis = await reportApi.analyzeReport({
        user_id: userId,
        context: {
          purpose: 'specialist_referral',
          target_audience: 'specialist',
        },
        available_data: {
          quick_scan_ids: quickScanIds,
          deep_dive_ids: deepDiveIds,
        }
      });

      setStep('generating');

      // Generate specialist report
      const report = await reportApi.generateSpecialistReport(
        selectedSpecialty as any,
        analysis.analysis_id,
        userId
      );

      setGeneratedReport(report);
      setStep('complete');
      onComplete?.(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
      setStep('select');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'complete' && generatedReport) {
    return (
      <div className="p-6 bg-green-50 rounded-lg">
        <h3 className="text-lg font-semibold text-green-800 mb-2">Report Generated Successfully!</h3>
        <p className="text-green-700">Report ID: {generatedReport.report_id}</p>
        <p className="text-green-700">Type: {generatedReport.report_type}</p>
        <button 
          onClick={() => window.location.href = `/reports/${generatedReport.report_id}`}
          className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          View Report
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>
      )}

      {step === 'select' && (
        <>
          <h2 className="text-2xl font-bold">Generate Medical Report</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setReportType('symptom')}
              className={`p-4 border rounded-lg hover:border-blue-500 ${
                reportType === 'symptom' ? 'border-blue-500 bg-blue-50' : ''
              }`}
            >
              <h3 className="font-semibold">Symptom-Based Report</h3>
              <p className="text-sm text-gray-600 mt-1">Analyze specific symptoms and conditions</p>
            </button>

            <button
              onClick={() => setReportType('time')}
              className={`p-4 border rounded-lg hover:border-blue-500 ${
                reportType === 'time' ? 'border-blue-500 bg-blue-50' : ''
              }`}
            >
              <h3 className="font-semibold">Time Period Report</h3>
              <p className="text-sm text-gray-600 mt-1">30-day or annual health summary</p>
            </button>

            <button
              onClick={() => setReportType('specialist')}
              className={`p-4 border rounded-lg hover:border-blue-500 ${
                reportType === 'specialist' ? 'border-blue-500 bg-blue-50' : ''
              }`}
            >
              <h3 className="font-semibold">Specialist Report</h3>
              <p className="text-sm text-gray-600 mt-1">Detailed report for specific specialty</p>
            </button>
          </div>

          {reportType === 'symptom' && (
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Describe your primary symptom or concern"
                value={symptomFocus}
                onChange={(e) => setSymptomFocus(e.target.value)}
                className="w-full p-3 border rounded-lg"
              />
              <button
                onClick={handleGenerateSymptomReport}
                disabled={!symptomFocus || loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Generate Report
              </button>
            </div>
          )}

          {reportType === 'time' && (
            <div className="flex gap-4">
              <button
                onClick={() => handleGenerateTimeReport('30-day')}
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Generate 30-Day Report
              </button>
              <button
                onClick={() => handleGenerateTimeReport('annual')}
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Generate Annual Report
              </button>
            </div>
          )}

          {reportType === 'specialist' && (
            <div className="space-y-4">
              <select
                value={selectedSpecialty}
                onChange={(e) => setSelectedSpecialty(e.target.value)}
                className="w-full p-3 border rounded-lg"
              >
                <option value="cardiology">Cardiology</option>
                <option value="neurology">Neurology</option>
                <option value="psychiatry">Psychiatry</option>
                <option value="dermatology">Dermatology</option>
                <option value="gastroenterology">Gastroenterology</option>
                <option value="endocrinology">Endocrinology</option>
                <option value="pulmonology">Pulmonology</option>
              </select>
              <button
                onClick={handleGenerateSpecialistReport}
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Generate {selectedSpecialty} Report
              </button>
            </div>
          )}
        </>
      )}

      {step === 'analyzing' && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-lg">Analyzing your health data...</p>
          <p className="text-sm text-gray-600">Determining the best report type for your needs</p>
        </div>
      )}

      {step === 'generating' && analysisResult && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-lg">Generating {analysisResult.recommended_type} report...</p>
          <p className="text-sm text-gray-600">{analysisResult.reasoning}</p>
          <p className="text-sm text-gray-600 mt-2">Confidence: {Math.round(analysisResult.confidence * 100)}%</p>
        </div>
      )}
    </div>
  );
}
```

## 4. Report Viewer Component

Create `components/ReportViewer.tsx`:

```tsx
'use client';

import { useState, useEffect } from 'react';
import { reportApi } from '@/lib/api/reports';

interface ReportViewerProps {
  reportId: string;
}

export function ReportViewer({ reportId }: ReportViewerProps) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('summary');

  useEffect(() => {
    loadReport();
  }, [reportId]);

  const loadReport = async () => {
    try {
      const data = await reportApi.getReport(reportId);
      setReport(data);
    } catch (error) {
      console.error('Failed to load report:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading report...</div>;
  if (!report) return <div>Report not found</div>;

  const reportData = report.report_data;

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          {report.report_type.replace(/_/g, ' ').toUpperCase()} Report
        </h1>
        <p className="text-gray-600">
          Generated on {new Date(report.generated_at).toLocaleDateString()}
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex gap-6">
          {['summary', 'analysis', 'recommendations'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 px-1 capitalize ${
                activeTab === tab 
                  ? 'border-b-2 border-blue-600 text-blue-600' 
                  : 'text-gray-600'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'summary' && (
          <div className="prose max-w-none">
            <h2>Executive Summary</h2>
            <p>{reportData.executive_summary?.one_page_summary}</p>
            
            {reportData.executive_summary?.key_findings && (
              <>
                <h3>Key Findings</h3>
                <ul>
                  {reportData.executive_summary.key_findings.map((finding: string, i: number) => (
                    <li key={i}>{finding}</li>
                  ))}
                </ul>
              </>
            )}

            {reportData.executive_summary?.patterns_identified && (
              <>
                <h3>Patterns Identified</h3>
                <ul>
                  {reportData.executive_summary.patterns_identified.map((pattern: string, i: number) => (
                    <li key={i}>{pattern}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="space-y-6">
            {/* Pattern Analysis for 30-day/annual reports */}
            {reportData.pattern_analysis && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Pattern Analysis</h3>
                
                {reportData.pattern_analysis.correlation_patterns?.symptom_triggers && (
                  <div className="mb-4">
                    <h4 className="font-medium mb-2">Symptom Triggers (Seems to pop up when...)</h4>
                    <ul className="list-disc pl-5 space-y-1">
                      {reportData.pattern_analysis.correlation_patterns.symptom_triggers.map((trigger: string, i: number) => (
                        <li key={i}>{trigger}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Specialist-specific analysis */}
            {report.report_type.includes('cardiology') && reportData.cardiology_specific && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Cardiac Analysis</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 rounded">
                    <h4 className="font-medium mb-2">Risk Stratification</h4>
                    <p>ASCVD Risk: {reportData.cardiology_specific.risk_stratification?.ascvd_risk}</p>
                    <p>Heart Failure Risk: {reportData.cardiology_specific.risk_stratification?.heart_failure_risk}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded">
                    <h4 className="font-medium mb-2">Recommended Tests</h4>
                    <ul className="list-disc pl-5">
                      {reportData.cardiology_specific.recommended_tests?.immediate?.map((test: string, i: number) => (
                        <li key={i}>{test}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className="space-y-6">
            {reportData.recommendations && (
              <>
                {reportData.recommendations.immediate_actions?.length > 0 && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded">
                    <h3 className="font-semibold text-red-800 mb-2">Immediate Actions</h3>
                    <ul className="list-disc pl-5">
                      {reportData.recommendations.immediate_actions.map((action: string, i: number) => (
                        <li key={i}>{action}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {reportData.recommendations.lifestyle_modifications && (
                  <div>
                    <h3 className="font-semibold mb-2">Lifestyle Modifications</h3>
                    <ul className="list-disc pl-5">
                      {reportData.recommendations.lifestyle_modifications.map((mod: string, i: number) => (
                        <li key={i}>{mod}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {reportData.recommendations.monitoring_priorities && (
                  <div>
                    <h3 className="font-semibold mb-2">Monitoring Priorities</h3>
                    <ul className="list-disc pl-5">
                      {reportData.recommendations.monitoring_priorities.map((priority: string, i: number) => (
                        <li key={i}>{priority}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}

            {/* Billing optimization */}
            {reportData.billing_optimization && (
              <div className="mt-6 p-4 bg-blue-50 rounded">
                <h3 className="font-semibold mb-2">Billing & Insurance</h3>
                <div className="space-y-2">
                  {reportData.billing_optimization.suggested_codes?.icd10 && (
                    <div>
                      <span className="text-sm font-medium">ICD-10 Codes: </span>
                      {reportData.billing_optimization.suggested_codes.icd10.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

## 5. Report List Component

Create `components/ReportList.tsx`:

```tsx
'use client';

import { useState, useEffect } from 'react';
import { reportApi } from '@/lib/api/reports';

interface ReportListProps {
  userId: string;
}

export function ReportList({ userId }: ReportListProps) {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, [userId]);

  const loadReports = async () => {
    try {
      const data = await reportApi.getUserReports(userId);
      setReports(data);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading reports...</div>;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Your Medical Reports</h2>
      
      {reports.length === 0 ? (
        <p className="text-gray-600">No reports generated yet</p>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <div key={report.id} className="border rounded-lg p-4 hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">
                    {report.type.replace(/_/g, ' ').toUpperCase()} Report
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {report.summary?.substring(0, 100)}...
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    {new Date(report.created_at).toLocaleDateString()}
                    {report.confidence && ` • Confidence: ${report.confidence}%`}
                  </p>
                </div>
                <button
                  onClick={() => window.location.href = `/reports/${report.id}`}
                  className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded"
                >
                  View
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

## 6. Implementation Example

Example page at `app/reports/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { ReportGenerator } from '@/components/ReportGenerator';
import { ReportList } from '@/components/ReportList';
import { useUser } from '@/hooks/useUser'; // Your auth hook

export default function ReportsPage() {
  const { user } = useUser();
  const [showGenerator, setShowGenerator] = useState(false);
  const [refreshList, setRefreshList] = useState(0);

  if (!user) return <div>Please login to view reports</div>;

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Medical Reports</h1>
        <button
          onClick={() => setShowGenerator(!showGenerator)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {showGenerator ? 'View Reports' : 'Generate New Report'}
        </button>
      </div>

      {showGenerator ? (
        <ReportGenerator 
          userId={user.id}
          onComplete={() => {
            setShowGenerator(false);
            setRefreshList(prev => prev + 1); // Trigger list refresh
          }}
        />
      ) : (
        <ReportList key={refreshList} userId={user.id} />
      )}
    </div>
  );
}
```

## 7. Environment Setup

Add to `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Features Implemented

1. **Two-Stage Process**: Analyze → Generate
2. **Multiple Report Types**: 
   - 7 Specialist reports (cardiology, neurology, etc.)
   - Time-based reports (30-day, annual)
   - Symptom-focused reports
3. **Pattern Detection**: "Seems to pop up when" analysis
4. **Billing Codes**: ICD-10 suggestions
5. **Comprehensive Analysis**: 4-7 pages of detailed health insights
6. **Doctor Collaboration**: Ready for doctor notes, sharing, and ratings

## Usage Flow

1. User selects report type (symptom-based, time-based, or specialist)
2. System analyzes available data to determine best report type
3. AI generates comprehensive report with patterns and recommendations
4. User can view, download, or share the report
5. Doctors can add notes and collaborate on reports

The system automatically selects the most appropriate report type based on available data and user context, ensuring users get the most relevant and useful health insights.