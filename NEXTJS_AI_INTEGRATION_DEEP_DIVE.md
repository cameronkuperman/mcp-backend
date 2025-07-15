# Next.js AI Integration Deep Dive - Medical Report System

This guide explains in detail how the AI integration works in the medical report system, including the complete schema, data flow, and integration patterns.

## Core AI Integration Pattern

### The Two-Stage AI Process

The medical report system uses a sophisticated two-stage AI process:

```
User Request → AI Analysis → AI Generation → Medical Report
```

### Stage 1: AI Analysis (Intelligence Layer)

**Purpose**: The AI analyzes the user's context and available data to determine the best report type.

**AI Decision Process**:
```typescript
// The AI considers these factors:
1. User Context (purpose, symptoms, urgency)
2. Available Data (scans, deep dives, photos)
3. Target Audience (self, doctor, specialist)
4. Time Sensitivity (emergency vs routine)

// AI Output:
{
  recommended_type: "comprehensive" | "urgent_triage" | etc,
  confidence: 0.85,
  reasoning: "Based on emergency indicators...",
  report_config: { /* AI-determined configuration */ }
}
```

### Stage 2: AI Report Generation

**Purpose**: Based on the analysis, the AI generates the appropriate medical report using specialized prompts.

## Complete Schema Documentation

### 1. AI Analysis Request Schema

```typescript
interface ReportAnalyzeRequest {
  user_id?: string;
  
  // Context for AI decision-making
  context: {
    // Tells AI the purpose of the report
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    
    // Specific symptom the AI should focus on
    symptom_focus?: string; // e.g., "recurring headaches"
    
    // Time window for AI to consider
    time_frame?: {
      start?: string; // ISO date
      end?: string;   // ISO date
    };
    
    // Helps AI tailor language and detail level
    target_audience?: 'self' | 'primary_care' | 'specialist' | 'emergency';
  };
  
  // Available health data for AI to analyze
  available_data?: {
    quick_scan_ids?: string[];    // Previous AI health scans
    deep_dive_ids?: string[];     // Previous AI deep dive sessions
    photo_session_ids?: string[]; // AI photo analysis sessions
  };
}
```

### 2. AI Analysis Response Schema

```typescript
interface ReportAnalyzeResponse {
  // AI-determined best endpoint
  recommended_endpoint: string; // e.g., "/api/report/urgent-triage"
  
  // AI-determined report type
  recommended_type: ReportType;
  
  // AI's reasoning (human-readable)
  reasoning: string;
  
  // AI's confidence in this decision (0-1)
  confidence: number;
  
  // AI-generated configuration for report generation
  report_config: {
    time_range: {
      start: string;
      end: string;
    };
    primary_focus: string;
    include_sections: string[];
    data_sources: {
      quick_scans: string[];
      deep_dives: string[];
    };
    urgency_level: 'emergency' | 'urgent' | 'routine';
    // AI can add custom fields based on analysis
    [key: string]: any;
  };
  
  // Unique ID for this analysis
  analysis_id: string;
  
  status: 'success' | 'error';
}
```

### 3. AI-Generated Report Schema

```typescript
interface MedicalReport {
  report_id: string;
  report_type: ReportType;
  generated_at: string;
  
  // The AI-generated content
  report_data: {
    // Always includes executive summary
    executive_summary: {
      one_page_summary: string; // AI-written comprehensive summary
      chief_complaints?: string[]; // AI-extracted main issues
      key_findings?: string[]; // AI-identified important findings
      urgency_indicators?: string[]; // AI-detected urgent issues
      action_items?: string[]; // AI-recommended next steps
    };
    
    // Additional sections based on report type
    patient_story?: {
      symptoms_timeline?: Array<{
        date: string;
        symptom: string;
        severity: number; // AI-assessed 1-10
        patient_description: string; // AI interpretation
      }>;
      pain_patterns?: {
        locations: string[]; // AI-identified areas
        triggers: string[]; // AI-detected triggers
        relievers: string[]; // AI-found relief methods
        progression: string; // AI analysis of progression
      };
    };
    
    medical_analysis?: {
      conditions_assessed?: Array<{
        condition: string; // AI medical terminology
        likelihood: string; // AI assessment
        supporting_evidence: string[]; // AI reasoning
        from_sessions: string[]; // Data sources AI used
      }>;
      symptom_correlations?: string[]; // AI-found patterns
      risk_factors?: string[]; // AI-identified risks
    };
    
    action_plan?: {
      immediate_actions?: string[]; // AI priorities
      diagnostic_tests?: string[]; // AI recommendations
      lifestyle_changes?: string[]; // AI suggestions
      monitoring_plan?: string[]; // AI tracking advice
      follow_up_timeline?: string; // AI-suggested timeline
    };
    
    // For urgent reports
    triage_summary?: {
      immediate_concerns?: string[];
      vital_symptoms?: Array<{
        symptom: string;
        severity: 'mild' | 'moderate' | 'severe'; // AI assessment
        duration: string;
        red_flags?: string[]; // AI-identified warnings
      }>;
      recommended_action?: string; // AI urgent advice
      what_to_tell_doctor?: string[]; // AI communication guide
      recent_progression?: string; // AI trend analysis
    };
  };
  
  // Metadata about AI generation
  confidence_score?: number; // Overall AI confidence
  model_used?: string; // Which AI model generated this
  status: 'success' | 'error';
}
```

## AI Integration Implementation

### 1. Frontend AI Service Layer

```typescript
// src/services/reportService.ts

export class ReportService {
  // Step 1: Send context to AI for analysis
  async analyzeReport(request: ReportAnalyzeRequest): Promise<ReportAnalyzeResponse> {
    // AI analyzes:
    // - User's symptoms and context
    // - Available health data
    // - Urgency indicators
    // - Best report type for the situation
    
    const response = await this.client.post<ReportAnalyzeResponse>(
      '/api/report/analyze', 
      request
    );
    
    // AI returns its analysis and recommendation
    return response;
  }

  // Step 2: Generate report based on AI analysis
  async generateReport(
    analysis: ReportAnalyzeResponse, 
    userId?: string
  ): Promise<MedicalReport> {
    // Use AI-recommended endpoint
    const { analysis_id, recommended_type, report_config } = analysis;
    
    // Call the specific AI generation endpoint
    switch (recommended_type) {
      case 'urgent_triage':
        // AI generates emergency-focused report
        return await this.generateUrgentTriage(analysis_id, userId);
        
      case 'comprehensive':
        // AI generates detailed medical report
        return await this.generateComprehensive(analysis_id, userId);
        
      // ... other AI report types
    }
  }
}
```

### 2. AI Decision Logic in Analysis

The AI analysis considers multiple factors:

```typescript
// Backend AI logic (conceptual)
function analyzeReportType(request: ReportAnalyzeRequest) {
  // AI checks for emergency indicators
  if (hasEmergencyIndicators(request)) {
    return {
      recommended_type: 'urgent_triage',
      reasoning: 'Emergency symptoms detected requiring immediate attention',
      confidence: 0.95,
      report_config: {
        urgency_level: 'emergency',
        time_range: { start: 'last_7_days', end: 'now' },
        include_sections: ['triage_summary', 'immediate_actions']
      }
    };
  }
  
  // AI checks data availability
  if (request.available_data?.photo_session_ids?.length >= 3) {
    return {
      recommended_type: 'photo_progression',
      reasoning: 'Multiple photos available for visual progression analysis',
      confidence: 0.88,
      report_config: {
        primary_focus: 'visual_changes',
        include_sections: ['photo_timeline', 'visual_analysis']
      }
    };
  }
  
  // AI checks purpose
  if (request.context.purpose === 'annual_checkup') {
    return {
      recommended_type: 'annual_summary',
      reasoning: 'Annual health review requested',
      confidence: 0.92,
      report_config: {
        time_range: { start: 'one_year_ago', end: 'now' },
        include_sections: ['yearly_trends', 'preventive_recommendations']
      }
    };
  }
  
  // Default to comprehensive
  return {
    recommended_type: 'comprehensive',
    reasoning: 'General health analysis with all available data',
    confidence: 0.85,
    report_config: {
      include_sections: ['executive_summary', 'patient_story', 'medical_analysis', 'action_plan']
    }
  };
}
```

### 3. AI Report Generation Process

```typescript
// Backend report generation (simplified)
async function generateComprehensiveReport(analysisId: string, userId: string) {
  // Load AI analysis results
  const analysis = await loadAnalysis(analysisId);
  
  // Gather all health data based on AI config
  const healthData = await gatherHealthData(userId, analysis.report_config);
  
  // Prepare context for AI
  const aiContext = {
    timeRange: analysis.report_config.time_range,
    primaryFocus: analysis.report_config.primary_focus,
    quickScans: healthData.quick_scans.map(scan => ({
      date: scan.created_at,
      bodyPart: scan.body_part,
      aiAnalysis: scan.analysis_result, // Previous AI analysis
      confidence: scan.confidence_score
    })),
    deepDives: healthData.deep_dives.map(dive => ({
      date: dive.created_at,
      questionsAsked: dive.questions, // AI-generated questions
      responses: dive.responses,
      finalAnalysis: dive.final_analysis // AI conclusions
    })),
    symptomTracking: healthData.symptom_tracking
  };
  
  // Call AI model to generate report
  const aiResponse = await callAI({
    model: 'medical-report-generator',
    systemPrompt: 'You are generating a comprehensive medical report...',
    context: aiContext,
    outputFormat: 'structured_json'
  });
  
  // Parse and validate AI response
  const reportData = parseAIResponse(aiResponse);
  
  // Save generated report
  return await saveReport({
    report_type: 'comprehensive',
    report_data: reportData,
    confidence_score: calculateConfidence(reportData),
    model_used: 'gpt-4-medical'
  });
}
```

## Frontend Integration Patterns

### 1. AI-Aware React Hook

```typescript
export const useReportGeneration = (userId?: string) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [analysis, setAnalysis] = useState<ReportAnalyzeResponse | null>(null);
  const [report, setReport] = useState<MedicalReport | null>(null);
  
  const generateReport = async (request: ReportAnalyzeRequest) => {
    try {
      // Phase 1: AI Analysis
      setIsAnalyzing(true);
      const aiAnalysis = await reportService.analyzeReport(request);
      setAnalysis(aiAnalysis);
      
      // Show user what AI decided
      console.log('AI recommends:', aiAnalysis.recommended_type);
      console.log('AI reasoning:', aiAnalysis.reasoning);
      
      // Phase 2: AI Generation
      setIsGenerating(true);
      const aiReport = await reportService.generateReport(
        aiAnalysis,
        request.user_id || userId
      );
      setReport(aiReport);
      
      return { analysis: aiAnalysis, report: aiReport };
      
    } catch (error) {
      // Handle AI errors
      console.error('AI generation failed:', error);
      throw error;
    }
  };
  
  return {
    isAnalyzing, // AI is analyzing context
    isGenerating, // AI is generating report
    analysis, // AI's analysis results
    report, // AI-generated report
    generateReport
  };
};
```

### 2. Displaying AI Analysis to User

```typescript
const ReportGenerator = () => {
  const { isAnalyzing, analysis, report } = useReportGeneration();
  
  return (
    <div>
      {/* Show AI analysis phase */}
      {isAnalyzing && (
        <div className="ai-analyzing">
          <h3>AI is analyzing your health data...</h3>
          <p>Determining the best report type for your needs</p>
        </div>
      )}
      
      {/* Show AI decision */}
      {analysis && !report && (
        <div className="ai-decision">
          <h3>AI Analysis Complete</h3>
          <p>Recommended: {analysis.recommended_type}</p>
          <p>Reason: {analysis.reasoning}</p>
          <p>Confidence: {Math.round(analysis.confidence * 100)}%</p>
        </div>
      )}
      
      {/* Show AI-generated report */}
      {report && (
        <ReportViewer report={report} />
      )}
    </div>
  );
};
```

### 3. AI-Enhanced Report Display

```typescript
const ReportViewer = ({ report }: { report: MedicalReport }) => {
  // Display AI-generated content with confidence indicators
  return (
    <div>
      {/* AI Confidence Badge */}
      {report.confidence_score && (
        <div className="ai-confidence">
          AI Confidence: {report.confidence_score}%
        </div>
      )}
      
      {/* AI-Generated Summary */}
      <section className="executive-summary">
        <h2>AI-Generated Summary</h2>
        <p>{report.report_data.executive_summary.one_page_summary}</p>
        
        {/* AI-Identified Key Points */}
        {report.report_data.executive_summary.key_findings?.map(finding => (
          <div key={finding} className="ai-finding">
            <span className="ai-badge">AI Finding</span>
            <p>{finding}</p>
          </div>
        ))}
      </section>
      
      {/* AI Medical Analysis */}
      {report.report_data.medical_analysis && (
        <section className="ai-analysis">
          <h2>AI Medical Analysis</h2>
          {report.report_data.medical_analysis.conditions_assessed?.map(condition => (
            <div key={condition.condition} className="ai-condition">
              <h3>{condition.condition}</h3>
              <p>AI Assessment: {condition.likelihood}</p>
              <ul>
                {condition.supporting_evidence.map(evidence => (
                  <li key={evidence}>{evidence}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
    </div>
  );
};
```

## AI Model Integration Details

### 1. Model Selection Based on Report Type

```typescript
// Backend model selection
const AI_MODELS = {
  'urgent_triage': {
    model: 'gpt-4-medical-emergency',
    temperature: 0.2, // Lower for critical accuracy
    maxTokens: 1000,
    systemPrompt: 'You are an emergency medical triage AI...'
  },
  'comprehensive': {
    model: 'gpt-4-medical-detailed',
    temperature: 0.3,
    maxTokens: 3000,
    systemPrompt: 'You are generating a comprehensive medical report...'
  },
  'symptom_timeline': {
    model: 'gpt-4-medical-temporal',
    temperature: 0.4,
    maxTokens: 2000,
    systemPrompt: 'You are analyzing symptom progression over time...'
  }
};
```

### 2. AI Prompt Engineering

```typescript
// Example prompt structure for comprehensive report
const buildComprehensivePrompt = (healthData: any) => {
  return `
You are generating a comprehensive medical report. Structure your response as valid JSON.

PATIENT DATA:
- Quick Scans: ${JSON.stringify(healthData.quickScans)}
- Deep Dives: ${JSON.stringify(healthData.deepDives)}
- Symptom Tracking: ${JSON.stringify(healthData.symptoms)}

REQUIRED OUTPUT STRUCTURE:
{
  "executive_summary": {
    "one_page_summary": "Complete overview of health status and findings",
    "chief_complaints": ["main health concerns"],
    "key_findings": ["important discoveries"],
    "urgency_indicators": ["any concerning findings"],
    "action_items": ["recommended next steps"]
  },
  "patient_story": {
    // Patient's health journey
  },
  "medical_analysis": {
    // Your medical assessment
  },
  "action_plan": {
    // Recommendations
  }
}

INSTRUCTIONS:
1. Analyze all available health data
2. Identify patterns and correlations
3. Assess potential conditions with confidence levels
4. Provide actionable recommendations
5. Flag any urgent concerns
`;
};
```

### 3. AI Response Validation

```typescript
// Validate AI-generated content
function validateAIResponse(response: any): boolean {
  // Check required fields
  if (!response.executive_summary?.one_page_summary) {
    throw new Error('AI failed to generate executive summary');
  }
  
  // Validate medical terminology
  if (response.medical_analysis?.conditions_assessed) {
    for (const condition of response.medical_analysis.conditions_assessed) {
      if (!isValidMedicalTerm(condition.condition)) {
        console.warn('AI used non-standard medical term:', condition.condition);
      }
    }
  }
  
  // Check confidence scores
  if (response.confidence_score && (response.confidence_score < 0 || response.confidence_score > 100)) {
    throw new Error('AI confidence score out of range');
  }
  
  return true;
}
```

## Advanced AI Features

### 1. Multi-Modal AI Analysis

```typescript
// For photo progression reports
async function analyzePhotoProgression(photoSessions: PhotoSession[]) {
  const aiAnalysis = await callMultiModalAI({
    model: 'gpt-4-vision',
    images: photoSessions.map(session => session.imageUrl),
    prompt: 'Analyze the visual progression of this medical condition...',
    outputFormat: {
      visual_changes: 'detailed description',
      progression_rate: 'slow|moderate|rapid',
      improvement_areas: ['list of improvements'],
      concern_areas: ['list of concerns'],
      recommendations: ['next steps']
    }
  });
  
  return aiAnalysis;
}
```

### 2. AI Contextual Memory

```typescript
// AI remembers previous interactions
interface AIContext {
  userId: string;
  previousReports: MedicalReport[];
  previousQuestions: string[];
  medicalHistory: any;
}

async function generateWithContext(request: any, context: AIContext) {
  const prompt = `
Previous Reports: ${context.previousReports.map(r => r.report_type).join(', ')}
Known Conditions: ${context.medicalHistory.conditions}

Generate a report that:
1. References previous findings appropriately
2. Tracks progression from last report
3. Highlights new developments
`;
  
  return await callAI({ prompt, context });
}
```

### 3. AI Confidence Calibration

```typescript
// Calculate overall confidence based on data quality
function calculateAIConfidence(reportData: any, sourceData: any): number {
  let confidence = 0.5; // Base confidence
  
  // More data sources increase confidence
  confidence += sourceData.quickScans.length * 0.05;
  confidence += sourceData.deepDives.length * 0.1;
  
  // Recent data increases confidence
  const recentData = sourceData.quickScans.filter(
    scan => isWithinDays(scan.created_at, 30)
  );
  confidence += recentData.length * 0.05;
  
  // Consistent findings increase confidence
  if (hasConsistentFindings(reportData)) {
    confidence += 0.1;
  }
  
  return Math.min(confidence, 0.95); // Cap at 95%
}
```

## Error Handling for AI Integration

```typescript
// Graceful AI failure handling
async function generateReportWithFallback(request: any) {
  try {
    // Try primary AI model
    return await generateWithPrimaryAI(request);
  } catch (error) {
    console.error('Primary AI failed:', error);
    
    try {
      // Fallback to secondary model
      return await generateWithFallbackAI(request);
    } catch (fallbackError) {
      // Return basic report structure
      return {
        report_type: 'basic',
        report_data: {
          executive_summary: {
            one_page_summary: 'AI generation temporarily unavailable. Please try again later.',
            error_details: error.message
          }
        },
        status: 'partial'
      };
    }
  }
}
```

## Summary

This AI integration pattern provides:

1. **Two-Stage Intelligence**: AI first analyzes context, then generates appropriate content
2. **Flexible Schema**: Supports multiple report types with AI-adapted structures
3. **Confidence Tracking**: AI confidence scores throughout the process
4. **Error Recovery**: Graceful fallbacks when AI fails
5. **Context Awareness**: AI uses historical data and previous reports
6. **Model Optimization**: Different AI models for different report types
7. **Validation Layer**: Ensures AI output meets medical standards

The system treats AI as an intelligent partner that:
- Understands medical context
- Makes informed decisions about report types
- Generates medically accurate content
- Provides confidence levels for its assessments
- Adapts to different audiences and urgencies