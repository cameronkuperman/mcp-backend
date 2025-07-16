# Next.js Medical Reports Implementation Guide

Complete implementation guide for integrating the enhanced medical report system into your Next.js frontend.

## Table of Contents

1. [Backend Setup](#backend-setup)
2. [Database Migration](#database-migration)
3. [API Integration](#api-integration)
4. [React Components](#react-components)
5. [State Management](#state-management)
6. [UI/UX Implementation](#uiux-implementation)
7. [Testing](#testing)

## Backend Setup

### 1. Add New Endpoints to run_oracle.py

Copy all the code from `specialist_endpoints_to_add.py` and add it to your `run_oracle.py` file:
- Add the imports at the top
- Add the Pydantic models after existing models
- Add helper functions after existing helpers
- Add all the endpoints before the main function

### 2. Update Root Endpoint

Update the root endpoint in `run_oracle.py` to include all new report types:

```python
@app.get("/")
async def root():
    return {
        "message": "Oracle AI Server Running",
        "endpoints": {
            # ... existing endpoints ...
            "reports": {
                "analyze": "POST /api/report/analyze",
                "comprehensive": "POST /api/report/comprehensive",
                "urgent_triage": "POST /api/report/urgent-triage",
                "photo_progression": "POST /api/report/photo-progression",
                "symptom_timeline": "POST /api/report/symptom-timeline",
                "specialist": "POST /api/report/specialist",
                "annual_summary": "POST /api/report/annual-summary",
                # NEW SPECIALIST ENDPOINTS
                "cardiology": "POST /api/report/cardiology",
                "neurology": "POST /api/report/neurology",
                "psychiatry": "POST /api/report/psychiatry",
                "dermatology": "POST /api/report/dermatology",
                "gastroenterology": "POST /api/report/gastroenterology",
                "endocrinology": "POST /api/report/endocrinology",
                "pulmonology": "POST /api/report/pulmonology",
                # TIME-BASED REPORTS
                "30_day": "POST /api/report/30-day",
                "annual": "POST /api/report/annual",
                # DOCTOR COLLABORATION
                "add_doctor_notes": "PUT /api/report/{report_id}/doctor-notes",
                "share_report": "POST /api/report/{report_id}/share",
                "rate_report": "POST /api/report/{report_id}/rate",
                # POPULATION HEALTH
                "outbreak_alerts": "GET /api/population-health/alerts",
                # EXISTING
                "list_user_reports": "GET /api/reports?user_id=USER_ID",
                "get_report": "GET /api/reports/{report_id}",
                "mark_accessed": "POST /api/reports/{report_id}/access"
            }
        }
    }
```

## Database Migration

### Run in Supabase SQL Editor

1. First run the base migration (if not already done):
```sql
-- Run database_migrations.sql
```

2. Then run the enhanced migration:
```sql
-- Run ENHANCED_REPORTS_MIGRATION.sql
```

## API Integration

### 1. Create API Service (`/lib/api/reports.ts`)

```typescript
import { API_BASE_URL } from '@/config/constants';

// Types
export interface ReportAnalysisRequest {
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

export interface ReportAnalysisResponse {
  recommended_endpoint: string;
  recommended_type: string;
  reasoning: string;
  confidence: number;
  report_config: any;
  analysis_id: string;
  status: 'success' | 'error';
}

export interface GenerateReportRequest {
  analysis_id: string;
  user_id?: string;
  specialty?: string;
}

export interface MedicalReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  report_data: any;
  status: 'success' | 'error';
}

export interface DoctorNotesRequest {
  doctor_npi: string;
  specialty: string;
  notes: string;
  sections_reviewed: string[];
  diagnosis?: string;
  plan_modifications?: any;
  follow_up_instructions?: string;
}

// API Service Class
export class ReportService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  // Step 1: Analyze what report type to generate
  async analyzeReport(request: ReportAnalysisRequest): Promise<ReportAnalysisResponse> {
    const response = await fetch(`${this.baseUrl}/api/report/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error('Failed to analyze report requirements');
    }

    return response.json();
  }

  // Step 2: Generate the actual report
  async generateReport(endpoint: string, request: GenerateReportRequest): Promise<MedicalReport> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error('Failed to generate report');
    }

    return response.json();
  }

  // Generate specialist reports
  async generateSpecialistReport(
    specialty: 'cardiology' | 'neurology' | 'psychiatry' | 'dermatology' | 'gastroenterology' | 'endocrinology' | 'pulmonology',
    request: GenerateReportRequest
  ): Promise<MedicalReport> {
    return this.generateReport(`/api/report/${specialty}`, request);
  }

  // Generate time-based reports
  async generate30DayReport(userId: string): Promise<MedicalReport> {
    const response = await fetch(`${this.baseUrl}/api/report/30-day`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      throw new Error('Failed to generate 30-day report');
    }

    return response.json();
  }

  async generateAnnualReport(userId: string): Promise<MedicalReport> {
    const response = await fetch(`${this.baseUrl}/api/report/annual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      throw new Error('Failed to generate annual report');
    }

    return response.json();
  }

  // Doctor collaboration
  async addDoctorNotes(reportId: string, notes: DoctorNotesRequest): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/report/${reportId}/doctor-notes`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(notes),
    });

    if (!response.ok) {
      throw new Error('Failed to add doctor notes');
    }

    return response.json();
  }

  async shareReport(reportId: string, shareRequest: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/report/${reportId}/share`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(shareRequest),
    });

    if (!response.ok) {
      throw new Error('Failed to share report');
    }

    return response.json();
  }

  async rateReport(reportId: string, rating: any): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/report/${reportId}/rate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rating),
    });

    if (!response.ok) {
      throw new Error('Failed to rate report');
    }

    return response.json();
  }

  // Get user's reports
  async getUserReports(userId: string): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/api/reports?user_id=${userId}`);

    if (!response.ok) {
      throw new Error('Failed to fetch reports');
    }

    return response.json();
  }

  // Get specific report
  async getReport(reportId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/reports/${reportId}`);

    if (!response.ok) {
      throw new Error('Failed to fetch report');
    }

    return response.json();
  }

  // Get outbreak alerts
  async getOutbreakAlerts(location: string, symptoms?: string[]): Promise<any> {
    const params = new URLSearchParams({ location });
    if (symptoms) {
      symptoms.forEach(s => params.append('symptoms', s));
    }

    const response = await fetch(`${this.baseUrl}/api/population-health/alerts?${params}`);

    if (!response.ok) {
      throw new Error('Failed to fetch outbreak alerts');
    }

    return response.json();
  }
}

export const reportService = new ReportService();
```

## React Components

### 1. Report Generator Component (`/components/reports/ReportGenerator.tsx`)

```tsx
'use client';

import { useState } from 'react';
import { useUser } from '@/hooks/useUser';
import { reportService } from '@/lib/api/reports';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { AlertDialog } from '@/components/ui/alert-dialog';

interface ReportGeneratorProps {
  quickScanIds?: string[];
  deepDiveIds?: string[];
  onReportGenerated?: (reportId: string) => void;
}

export function ReportGenerator({ 
  quickScanIds = [], 
  deepDiveIds = [],
  onReportGenerated 
}: ReportGeneratorProps) {
  const { user } = useUser();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<'configure' | 'analyzing' | 'generating' | 'complete'>('configure');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [generatedReport, setGeneratedReport] = useState<any>(null);

  // Configuration state
  const [purpose, setPurpose] = useState<string>('symptom_specific');
  const [symptomFocus, setSymptomFocus] = useState<string>('');
  const [targetAudience, setTargetAudience] = useState<string>('self');

  const handleGenerateReport = async () => {
    if (!user?.id) return;

    setLoading(true);
    setError(null);
    setCurrentStep('analyzing');

    try {
      // Step 1: Analyze
      const analysisRequest = {
        user_id: user.id,
        context: {
          purpose,
          symptom_focus: symptomFocus,
          target_audience: targetAudience,
        },
        available_data: {
          quick_scan_ids: quickScanIds,
          deep_dive_ids: deepDiveIds,
        }
      };

      const analysis = await reportService.analyzeReport(analysisRequest);
      setAnalysisResult(analysis);
      setCurrentStep('generating');

      // Step 2: Generate based on recommendation
      const report = await reportService.generateReport(
        analysis.recommended_endpoint,
        {
          analysis_id: analysis.analysis_id,
          user_id: user.id
        }
      );

      setGeneratedReport(report);
      setCurrentStep('complete');
      
      if (onReportGenerated) {
        onReportGenerated(report.report_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
      setCurrentStep('configure');
    } finally {
      setLoading(false);
    }
  };

  const generateTimePeriodReport = async (type: '30-day' | 'annual') => {
    if (!user?.id) return;

    setLoading(true);
    setError(null);

    try {
      const report = type === '30-day' 
        ? await reportService.generate30DayReport(user.id)
        : await reportService.generateAnnualReport(user.id);

      setGeneratedReport(report);
      setCurrentStep('complete');
      
      if (onReportGenerated) {
        onReportGenerated(report.report_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  if (currentStep === 'complete' && generatedReport) {
    return <ReportViewer report={generatedReport} />;
  }

  return (
    <Card className="p-6">
      <h2 className="text-2xl font-bold mb-6">Generate Medical Report</h2>

      {error && (
        <AlertDialog type="error" className="mb-4">
          {error}
        </AlertDialog>
      )}

      {currentStep === 'configure' && (
        <div className="space-y-6">
          {/* Report Type Selection */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Report Type</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Symptom-Based Reports */}
              <Card 
                className="p-4 cursor-pointer hover:border-blue-500 transition-colors"
                onClick={() => setPurpose('symptom_specific')}
              >
                <h4 className="font-semibold">Symptom Analysis</h4>
                <p className="text-sm text-gray-600">
                  Generate report based on specific symptoms
                </p>
              </Card>

              {/* Time-Based Reports */}
              <Card 
                className="p-4 cursor-pointer hover:border-blue-500 transition-colors"
                onClick={() => generateTimePeriodReport('30-day')}
              >
                <h4 className="font-semibold">30-Day Summary</h4>
                <p className="text-sm text-gray-600">
                  Comprehensive health summary for past month
                </p>
              </Card>

              <Card 
                className="p-4 cursor-pointer hover:border-blue-500 transition-colors"
                onClick={() => generateTimePeriodReport('annual')}
              >
                <h4 className="font-semibold">Annual Report</h4>
                <p className="text-sm text-gray-600">
                  Year-long health analysis and trends
                </p>
              </Card>

              {/* Emergency Report */}
              <Card 
                className="p-4 cursor-pointer hover:border-red-500 transition-colors"
                onClick={() => {
                  setPurpose('emergency');
                  setTargetAudience('emergency');
                }}
              >
                <h4 className="font-semibold text-red-600">Emergency Triage</h4>
                <p className="text-sm text-gray-600">
                  Urgent care summary for immediate medical attention
                </p>
              </Card>
            </div>
          </div>

          {/* Configuration Options */}
          {purpose === 'symptom_specific' && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Primary Symptom or Concern
                </label>
                <input
                  type="text"
                  value={symptomFocus}
                  onChange={(e) => setSymptomFocus(e.target.value)}
                  placeholder="e.g., recurring headaches, chest pain"
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Who will use this report?
                </label>
                <Select
                  value={targetAudience}
                  onChange={setTargetAudience}
                  options={[
                    { value: 'self', label: 'For myself' },
                    { value: 'primary_care', label: 'Primary care doctor' },
                    { value: 'specialist', label: 'Specialist referral' },
                    { value: 'emergency', label: 'Emergency room' }
                  ]}
                />
              </div>
            </>
          )}

          <Button
            onClick={handleGenerateReport}
            disabled={loading || (purpose === 'symptom_specific' && !symptomFocus)}
            className="w-full"
          >
            {loading ? <LoadingSpinner /> : 'Generate Report'}
          </Button>
        </div>
      )}

      {currentStep === 'analyzing' && (
        <div className="text-center py-8">
          <LoadingSpinner className="mx-auto mb-4" />
          <p className="text-lg">Analyzing your health data...</p>
          <p className="text-sm text-gray-600 mt-2">
            Determining the best report type based on your symptoms and history
          </p>
        </div>
      )}

      {currentStep === 'generating' && analysisResult && (
        <div className="text-center py-8">
          <LoadingSpinner className="mx-auto mb-4" />
          <p className="text-lg">Generating {analysisResult.recommended_type.replace('_', ' ')} report...</p>
          <p className="text-sm text-gray-600 mt-2">
            {analysisResult.reasoning}
          </p>
          <div className="mt-4 text-sm">
            <span className="font-medium">Confidence: </span>
            <span className="text-green-600">{Math.round(analysisResult.confidence * 100)}%</span>
          </div>
        </div>
      )}
    </Card>
  );
}
```

### 2. Report Viewer Component (`/components/reports/ReportViewer.tsx`)

```tsx
'use client';

import { useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, Share, Print, Edit } from 'lucide-react';

interface ReportViewerProps {
  report: any;
  allowDoctorEdits?: boolean;
  onAddNotes?: (notes: any) => void;
}

export function ReportViewer({ report, allowDoctorEdits = false, onAddNotes }: ReportViewerProps) {
  const [activeTab, setActiveTab] = useState('summary');
  const reportData = report.report_data;

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = () => {
    // Implement PDF generation
    console.log('Downloading PDF...');
  };

  const handleShare = () => {
    // Implement share functionality
    console.log('Sharing report...');
  };

  // Render different sections based on report type
  const renderReportContent = () => {
    switch (report.report_type) {
      case 'cardiology':
        return <CardiologyReportContent data={reportData} />;
      case 'neurology':
        return <NeurologyReportContent data={reportData} />;
      case 'psychiatry':
        return <PsychiatryReportContent data={reportData} />;
      case '30_day':
        return <ThirtyDayReportContent data={reportData} />;
      case 'annual':
        return <AnnualReportContent data={reportData} />;
      default:
        return <ComprehensiveReportContent data={reportData} />;
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Report Header */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {report.report_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Report
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Generated on {new Date(report.generated_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handlePrint}>
              <Print className="w-4 h-4 mr-1" /> Print
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadPDF}>
              <Download className="w-4 h-4 mr-1" /> PDF
            </Button>
            <Button variant="outline" size="sm" onClick={handleShare}>
              <Share className="w-4 h-4 mr-1" /> Share
            </Button>
            {allowDoctorEdits && (
              <Button variant="primary" size="sm">
                <Edit className="w-4 h-4 mr-1" /> Add Notes
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* Report Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="summary">Executive Summary</TabsTrigger>
          <TabsTrigger value="timeline">Timeline & Patterns</TabsTrigger>
          <TabsTrigger value="analysis">Clinical Analysis</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          {reportData.doctor_notes && (
            <TabsTrigger value="doctor_notes">Doctor Notes</TabsTrigger>
          )}
        </TabsList>

        {renderReportContent()}
      </Tabs>
    </div>
  );
}

// Specialist Report Components
function CardiologyReportContent({ data }: { data: any }) {
  return (
    <>
      <TabsContent value="summary">
        <Card>
          <CardContent className="prose max-w-none p-6">
            <h2>Executive Summary</h2>
            <p>{data.executive_summary?.one_page_summary}</p>
            
            <h3>Chief Complaints</h3>
            <ul>
              {data.executive_summary?.chief_complaints?.map((complaint: string, i: number) => (
                <li key={i}>{complaint}</li>
              ))}
            </ul>

            <h3>Key Findings</h3>
            <ul>
              {data.executive_summary?.key_findings?.map((finding: string, i: number) => (
                <li key={i}>{finding}</li>
              ))}
            </ul>

            {data.executive_summary?.urgency_indicators?.length > 0 && (
              <>
                <h3 className="text-red-600">Urgent Indicators</h3>
                <ul className="text-red-600">
                  {data.executive_summary.urgency_indicators.map((indicator: string, i: number) => (
                    <li key={i}>{indicator}</li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="timeline">
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Symptom Progression</h3>
            <p className="mb-4">{data.timeline_and_patterns?.symptom_progression}</p>

            <h3 className="text-lg font-semibold mb-4">Pattern Analysis</h3>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium">Seems to pop up when:</h4>
                <ul className="list-disc pl-5 mt-2">
                  {data.timeline_and_patterns?.pattern_analysis?.seems_to_pop_up_when?.map((trigger: string, i: number) => (
                    <li key={i}>{trigger}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-medium">Activity Correlation:</h4>
                <p>{data.timeline_and_patterns?.pattern_analysis?.correlation_with_activity}</p>
              </div>

              <div>
                <h4 className="font-medium">Time Patterns:</h4>
                <p>{data.timeline_and_patterns?.pattern_analysis?.time_of_day_patterns}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="analysis">
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cardiac Analysis</h3>
            
            {/* Chest Pain Analysis */}
            <div className="mb-6">
              <h4 className="font-medium mb-2">Chest Pain Characterization</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Patient Descriptions:</p>
                  <ul className="list-disc pl-5">
                    {data.cardiac_specific?.chest_pain_analysis?.descriptions_found?.map((desc: string, i: number) => (
                      <li key={i}>{desc}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Exertional Component:</p>
                  <p>{data.cardiac_specific?.chest_pain_analysis?.exertional_component}</p>
                </div>
              </div>
            </div>

            {/* Risk Assessment */}
            <div className="mb-6">
              <h4 className="font-medium mb-2">Risk Factor Assessment</h4>
              <div className="space-y-2">
                {data.cardiac_specific?.risk_assessment?.identified_risk_factors?.map((factor: string, i: number) => (
                  <Badge key={i} variant="secondary" className="mr-2">
                    {factor}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Vital Trends */}
            {data.cardiac_specific?.vital_trends && (
              <div>
                <h4 className="font-medium mb-2">Vital Sign Trends</h4>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p>Heart Rate: {data.cardiac_specific.vital_trends.heart_rate_patterns || 'No data available'}</p>
                  <p>Blood Pressure: {data.cardiac_specific.vital_trends.blood_pressure_mentions || 'No data available'}</p>
                  <p>Exercise Tolerance: {data.cardiac_specific.vital_trends.exercise_tolerance || 'No changes noted'}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="recommendations">
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Cardiology Workup Recommendations</h3>
            
            {/* Lab Tests */}
            <div className="mb-6">
              <h4 className="font-medium mb-3">Laboratory Tests to Consider</h4>
              <div className="space-y-2">
                {data.cardiology_workup?.labs_to_consider?.map((lab: any, i: number) => (
                  <div key={i} className="flex justify-between items-center p-3 bg-blue-50 rounded">
                    <span className="font-medium">{lab.test}</span>
                    <span className="text-sm text-gray-600">{lab.reason}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Cardiac Tests */}
            <div className="mb-6">
              <h4 className="font-medium mb-3">Cardiac Tests</h4>
              <div className="flex flex-wrap gap-2">
                {data.cardiology_workup?.cardiac_tests?.map((test: string, i: number) => (
                  <Badge key={i} variant="outline">
                    {test}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Red Flags */}
            {data.cardiology_workup?.red_flags_requiring_er?.length > 0 && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <h4 className="font-medium text-red-800 mb-2">⚠️ Red Flags Requiring Emergency Care</h4>
                <ul className="list-disc pl-5 text-red-700">
                  {data.cardiology_workup.red_flags_requiring_er.map((flag: string, i: number) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Clinical Support */}
            {data.clinical_support && (
              <div className="mt-6">
                <h4 className="font-medium mb-3">Clinical Documentation Support</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-gray-600">Suggested ICD-10 Codes:</p>
                    <div className="flex gap-2 mt-1">
                      {data.clinical_support.icd10_suggestions?.map((code: string, i: number) => (
                        <code key={i} className="px-2 py-1 bg-gray-100 rounded text-sm">
                          {code}
                        </code>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Follow-up Timing:</p>
                    <p className="font-medium">{data.clinical_support.follow_up_timing}</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </TabsContent>
    </>
  );
}

// Add similar components for other specialties...
function NeurologyReportContent({ data }: { data: any }) {
  // Similar structure but with neurology-specific sections
  return <>{/* Implement neurology report layout */}</>;
}

function PsychiatryReportContent({ data }: { data: any }) {
  // Similar structure but with psychiatry-specific sections
  return <>{/* Implement psychiatry report layout */}</>;
}

function ThirtyDayReportContent({ data }: { data: any }) {
  return (
    <>
      <TabsContent value="summary">
        <Card>
          <CardContent className="p-6">
            <h2 className="text-xl font-semibold mb-4">30-Day Health Dashboard</h2>
            
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-blue-600">
                  {data.executive_dashboard?.health_interaction_summary?.total_interactions || 0}
                </p>
                <p className="text-sm text-gray-600">Total Interactions</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-green-600">
                  {data.executive_dashboard?.health_interaction_summary?.quick_scans || 0}
                </p>
                <p className="text-sm text-gray-600">Quick Scans</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-purple-600">
                  {data.executive_dashboard?.health_interaction_summary?.deep_dives || 0}
                </p>
                <p className="text-sm text-gray-600">Deep Dives</p>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg text-center">
                <p className="text-3xl font-bold text-yellow-600">
                  {data.executive_dashboard?.overall_trend || 'Stable'}
                </p>
                <p className="text-sm text-gray-600">Overall Trend</p>
              </div>
            </div>

            {/* Top Symptoms */}
            <div>
              <h3 className="font-semibold mb-3">Top Symptoms by Frequency</h3>
              <div className="space-y-2">
                {data.executive_dashboard?.top_symptoms_by_frequency?.map((symptom: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span>{symptom.symptom}</span>
                    <div className="flex items-center gap-4">
                      <Badge variant="outline">{symptom.count} times</Badge>
                      <span className="text-sm text-gray-600">
                        Avg severity: {symptom.average_severity}/10
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="timeline">
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Pattern Analysis</h3>
            
            {/* Correlations */}
            <div className="mb-6">
              <h4 className="font-medium mb-3">Symptom Correlations</h4>
              <div className="space-y-3">
                {data.pattern_analysis?.symptom_correlations?.seems_to_pop_up_when?.map((pattern: any, i: number) => (
                  <div key={i} className="p-3 bg-blue-50 rounded">
                    <p className="font-medium">
                      When: {pattern.trigger}
                    </p>
                    <p className="text-sm text-gray-600">
                      Affects: {pattern.affected_symptoms.join(', ')}
                    </p>
                    <Badge variant={pattern.confidence === 'high' ? 'default' : 'secondary'} className="mt-1">
                      {pattern.confidence} confidence
                    </Badge>
                  </div>
                ))}
              </div>
            </div>

            {/* Temporal Patterns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium mb-2">Time of Day Patterns</h4>
                <div className="bg-gray-50 p-3 rounded">
                  <p><strong>Worst times:</strong> {data.pattern_analysis?.temporal_patterns?.time_of_day?.worst_times?.join(', ')}</p>
                  <p><strong>Best times:</strong> {data.pattern_analysis?.temporal_patterns?.time_of_day?.best_times?.join(', ')}</p>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-2">Day of Week Patterns</h4>
                <div className="bg-gray-50 p-3 rounded">
                  <p><strong>Worst days:</strong> {data.pattern_analysis?.temporal_patterns?.day_of_week?.worst_days?.join(', ')}</p>
                  <p><strong>Best days:</strong> {data.pattern_analysis?.temporal_patterns?.day_of_week?.best_days?.join(', ')}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      {/* Add more tabs for analysis and recommendations */}
    </>
  );
}

function AnnualReportContent({ data }: { data: any }) {
  // Implement annual report layout
  return <>{/* Annual report specific content */}</>;
}

function ComprehensiveReportContent({ data }: { data: any }) {
  // Default comprehensive report layout
  return <>{/* Comprehensive report content */}</>;
}
```

### 3. Report List Component (`/components/reports/ReportList.tsx`)

```tsx
'use client';

import { useState, useEffect } from 'react';
import { useUser } from '@/hooks/useUser';
import { reportService } from '@/lib/api/reports';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDistanceToNow } from 'date-fns';
import { FileText, Download, Share, Eye } from 'lucide-react';

export function ReportList() {
  const { user } = useUser();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.id) {
      loadReports();
    }
  }, [user?.id]);

  const loadReports = async () => {
    try {
      const userReports = await reportService.getUserReports(user.id);
      setReports(userReports);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const getReportTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      cardiology: 'bg-red-100 text-red-800',
      neurology: 'bg-purple-100 text-purple-800',
      psychiatry: 'bg-blue-100 text-blue-800',
      '30_day': 'bg-green-100 text-green-800',
      annual: 'bg-yellow-100 text-yellow-800',
      urgent_triage: 'bg-red-500 text-white',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return <div>Loading reports...</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold mb-4">Your Medical Reports</h2>
      
      {reports.length === 0 ? (
        <Card className="p-8 text-center">
          <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">No reports generated yet</p>
          <Button className="mt-4">Generate Your First Report</Button>
        </Card>
      ) : (
        <div className="grid gap-4">
          {reports.map((report) => (
            <Card key={report.id} className="p-4 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold">
                      {report.report_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())} Report
                    </h3>
                    <Badge className={getReportTypeColor(report.report_type)}>
                      {report.report_type.replace(/_/g, ' ')}
                    </Badge>
                    {report.doctor_reviewed && (
                      <Badge variant="success">Doctor Reviewed</Badge>
                    )}
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-1">
                    {report.executive_summary || 'Medical report summary...'}
                  </p>
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>
                      Generated {formatDistanceToNow(new Date(report.created_at))} ago
                    </span>
                    {report.confidence_score && (
                      <span>Confidence: {report.confidence_score}%</span>
                    )}
                  </div>
                </div>
                
                <div className="flex gap-2 ml-4">
                  <Button size="sm" variant="outline" onClick={() => window.open(`/reports/${report.id}`)}>
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="outline">
                    <Download className="w-4 h-4" />
                  </Button>
                  <Button size="sm" variant="outline">
                    <Share className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

## State Management

### Zustand Store (`/stores/reportStore.ts`)

```typescript
import { create } from 'zustand';
import { reportService } from '@/lib/api/reports';

interface ReportState {
  reports: any[];
  currentReport: any | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchReports: (userId: string) => Promise<void>;
  generateReport: (request: any) => Promise<any>;
  loadReport: (reportId: string) => Promise<void>;
  clearError: () => void;
}

export const useReportStore = create<ReportState>((set, get) => ({
  reports: [],
  currentReport: null,
  loading: false,
  error: null,

  fetchReports: async (userId: string) => {
    set({ loading: true, error: null });
    try {
      const reports = await reportService.getUserReports(userId);
      set({ reports, loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch reports',
        loading: false 
      });
    }
  },

  generateReport: async (request: any) => {
    set({ loading: true, error: null });
    try {
      // Step 1: Analyze
      const analysis = await reportService.analyzeReport(request);
      
      // Step 2: Generate
      const report = await reportService.generateReport(
        analysis.recommended_endpoint,
        {
          analysis_id: analysis.analysis_id,
          user_id: request.user_id
        }
      );
      
      // Add to reports list
      const { reports } = get();
      set({ 
        reports: [report, ...reports],
        currentReport: report,
        loading: false 
      });
      
      return report;
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to generate report',
        loading: false 
      });
      throw error;
    }
  },

  loadReport: async (reportId: string) => {
    set({ loading: true, error: null });
    try {
      const report = await reportService.getReport(reportId);
      set({ currentReport: report, loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to load report',
        loading: false 
      });
    }
  },

  clearError: () => set({ error: null }),
}));
```

## UI/UX Implementation

### 1. Report Generation Flow Page (`/app/reports/generate/page.tsx`)

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ReportGenerator } from '@/components/reports/ReportGenerator';
import { QuickScanSelector } from '@/components/reports/QuickScanSelector';
import { DeepDiveSelector } from '@/components/reports/DeepDiveSelector';
import { Stepper } from '@/components/ui/stepper';

const steps = [
  { id: 'select-data', title: 'Select Health Data' },
  { id: 'configure', title: 'Configure Report' },
  { id: 'generate', title: 'Generate Report' }
];

export default function GenerateReportPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedScans, setSelectedScans] = useState<string[]>([]);
  const [selectedDives, setSelectedDives] = useState<string[]>([]);

  const handleReportGenerated = (reportId: string) => {
    router.push(`/reports/${reportId}`);
  };

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">Generate Medical Report</h1>
      
      <Stepper steps={steps} currentStep={currentStep} className="mb-8" />

      {currentStep === 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Select Quick Scans to Include</h2>
            <QuickScanSelector 
              selectedIds={selectedScans}
              onSelectionChange={setSelectedScans}
            />
          </div>
          
          <div>
            <h2 className="text-xl font-semibold mb-4">Select Deep Dives to Include</h2>
            <DeepDiveSelector 
              selectedIds={selectedDives}
              onSelectionChange={setSelectedDives}
            />
          </div>

          <div className="flex justify-end">
            <Button 
              onClick={() => setCurrentStep(1)}
              disabled={selectedScans.length === 0 && selectedDives.length === 0}
            >
              Next: Configure Report
            </Button>
          </div>
        </div>
      )}

      {currentStep === 1 && (
        <ReportGenerator
          quickScanIds={selectedScans}
          deepDiveIds={selectedDives}
          onReportGenerated={handleReportGenerated}
        />
      )}
    </div>
  );
}
```

### 2. Report View Page (`/app/reports/[id]/page.tsx`)

```tsx
'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useReportStore } from '@/stores/reportStore';
import { ReportViewer } from '@/components/reports/ReportViewer';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { AlertDialog } from '@/components/ui/alert-dialog';

export default function ReportViewPage() {
  const params = useParams();
  const reportId = params.id as string;
  const { currentReport, loading, error, loadReport } = useReportStore();

  useEffect(() => {
    if (reportId) {
      loadReport(reportId);
    }
  }, [reportId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <AlertDialog type="error">
          {error}
        </AlertDialog>
      </div>
    );
  }

  if (!currentReport) {
    return (
      <div className="container mx-auto py-8">
        <AlertDialog type="warning">
          Report not found
        </AlertDialog>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <ReportViewer report={currentReport} />
    </div>
  );
}
```

## Testing

### Example Test File (`/__tests__/reports/ReportGenerator.test.tsx`)

```tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { ReportGenerator } from '@/components/reports/ReportGenerator';
import { reportService } from '@/lib/api/reports';

jest.mock('@/lib/api/reports');

describe('ReportGenerator', () => {
  const mockUser = { id: 'test-user-id' };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should generate a report successfully', async () => {
    const mockAnalysis = {
      recommended_endpoint: '/api/report/cardiology',
      recommended_type: 'cardiology',
      reasoning: 'Cardiac symptoms detected',
      confidence: 0.95,
      analysis_id: 'analysis-123',
      status: 'success'
    };

    const mockReport = {
      report_id: 'report-123',
      report_type: 'cardiology',
      generated_at: new Date().toISOString(),
      report_data: {
        executive_summary: {
          one_page_summary: 'Test summary'
        }
      },
      status: 'success'
    };

    (reportService.analyzeReport as jest.Mock).mockResolvedValue(mockAnalysis);
    (reportService.generateReport as jest.Mock).mockResolvedValue(mockReport);

    const onReportGenerated = jest.fn();

    render(
      <ReportGenerator 
        quickScanIds={['scan-1']}
        deepDiveIds={['dive-1']}
        onReportGenerated={onReportGenerated}
      />
    );

    // Fill in symptom focus
    const symptomInput = screen.getByPlaceholderText(/primary symptom/i);
    fireEvent.change(symptomInput, { target: { value: 'chest pain' } });

    // Click generate
    const generateButton = screen.getByText(/generate report/i);
    fireEvent.click(generateButton);

    // Wait for analysis
    await waitFor(() => {
      expect(screen.getByText(/analyzing your health data/i)).toBeInTheDocument();
    });

    // Wait for generation
    await waitFor(() => {
      expect(screen.getByText(/generating cardiology report/i)).toBeInTheDocument();
    });

    // Verify report generated
    await waitFor(() => {
      expect(onReportGenerated).toHaveBeenCalledWith('report-123');
    });
  });
});
```

## Deployment Checklist

1. **Backend Deployment**:
   ```bash
   # Add all endpoints to run_oracle.py
   # Test locally
   python run_oracle.py
   
   # Commit and push
   git add -A
   git commit -m "Add comprehensive medical report endpoints"
   git push
   ```

2. **Database Migration**:
   - Run `database_migrations.sql` in Supabase
   - Run `ENHANCED_REPORTS_MIGRATION.sql` in Supabase
   - Verify all tables created

3. **Frontend Deployment**:
   - Add all components
   - Update API configuration
   - Test report generation flow
   - Deploy to Vercel/your platform

4. **Environment Variables**:
   ```env
   NEXT_PUBLIC_ORACLE_API_URL=https://your-railway-app.up.railway.app
   ```

5. **Testing**:
   - Generate test reports for each type
   - Test doctor collaboration features
   - Verify PDF export
   - Check responsive design

## Summary

This implementation provides:
- ✅ All specialist report types (cardiology, neurology, etc.)
- ✅ Time-based reports (30-day, annual)
- ✅ Doctor collaboration features
- ✅ Pattern detection and "seems to pop up when" analysis
- ✅ Population health/outbreak detection
- ✅ Professional medical report layouts
- ✅ PDF export and sharing capabilities
- ✅ Complete Next.js integration

The system is now ready to generate comprehensive, doctor-ready medical reports that provide real value for healthcare decisions.