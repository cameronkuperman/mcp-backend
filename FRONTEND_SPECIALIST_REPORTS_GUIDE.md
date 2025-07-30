# Frontend Guide: Enhanced Specialist Reports Implementation

## Overview
This guide outlines the frontend changes needed to support the new enhanced specialist report system with detailed clinical information, specialty triage, and improved UI/UX for both patients and clinicians.

## 1. New API Endpoints

### Specialty Triage
```typescript
POST /api/report/specialty-triage
{
  "user_id": string,
  "quick_scan_ids": string[],  // Optional: IDs of quick scans to analyze
  "deep_dive_ids": string[],   // Optional: IDs of deep dives to analyze
  "primary_concern": string,   // Optional: Additional context
  "symptoms": string[],        // Optional: Additional symptoms
  "urgency": string           // Optional: "routine" | "urgent"
}

Response:
{
  "status": "success",
  "triage_result": {
    "primary_specialty": "cardiology",
    "confidence": 0.85,
    "reasoning": "Based on quick scan showing exertional chest pain and deep dive analysis",
    "secondary_specialties": [
      {
        "specialty": "pulmonology", 
        "confidence": 0.45,
        "reason": "Shortness of breath component noted in interactions"
      }
    ],
    "urgency": "urgent",
    "red_flags": ["Progressive symptoms", "Decreasing exercise tolerance"],
    "recommended_timing": "Within 1-2 weeks"
  }
}
```

### Primary Care Report
```typescript
POST /api/report/primary-care
// Same as other specialist reports
```

## 2. Enhanced Report Structure

All specialist reports now return this enhanced structure:

```typescript
interface SpecialistReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  status: "success" | "error";
  report_data: {
    clinical_summary: {
      chief_complaint: string;
      hpi: string;
      symptom_timeline: Array<{
        date: string;
        symptoms: string;
        severity: number;
        context: string;
        duration: string;
        resolution: string;
      }>;
      pattern_analysis: {
        frequency: string;
        triggers: string[];
        alleviating_factors: string[];
        progression: string;
      };
    };
    
    // Specialty-specific assessment (varies by specialty)
    [specialty]_assessment: {
      // See examples below
    };
    
    // Specialty-specific findings
    [specialty]_specific_findings: {
      // Detailed clinical findings
    };
    
    diagnostic_priorities: {
      immediate: Array<{
        test: string;
        rationale: string;
        timing: string;
      }>;
      short_term: Array<{...}>;
      contingent: Array<{
        test: string;
        condition: string;
        rationale: string;
      }>;
    };
    
    treatment_recommendations: {
      // Detailed treatment plans
    };
    
    follow_up_plan: {
      // Next steps and monitoring
    };
    
    data_quality_notes: {
      completeness: string;
      consistency: string;
      gaps: string[];
    };
  };
}
```

## 3. UI Components to Build

### A. Specialty Triage Component
```jsx
// SpecialtyTriage.jsx
const SpecialtyTriage = ({ userId, onSpecialtySelected }) => {
  const [selectedQuickScans, setSelectedQuickScans] = useState([]);
  const [selectedDeepDives, setSelectedDeepDives] = useState([]);
  const [primaryConcern, setPrimaryConcern] = useState('');
  const [triageResult, setTriageResult] = useState(null);
  
  // Fetch user's quick scans and deep dives
  const { quickScans, deepDives } = useHealthData(userId);
  
  const runTriage = async () => {
    const response = await api.post('/api/report/specialty-triage', {
      user_id: userId,
      quick_scan_ids: selectedQuickScans,
      deep_dive_ids: selectedDeepDives,
      primary_concern: primaryConcern
    });
    setTriageResult(response.data.triage_result);
  };
  
  return (
    <div className="specialty-triage">
      <h2>Find the Right Specialist</h2>
      
      {/* Quick Scan Selection */}
      <div className="scan-selection">
        <h3>Select Quick Scans to Include</h3>
        <div className="scan-list">
          {quickScans.map(scan => (
            <label key={scan.id} className="scan-item">
              <input
                type="checkbox"
                value={scan.id}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedQuickScans([...selectedQuickScans, scan.id]);
                  } else {
                    setSelectedQuickScans(selectedQuickScans.filter(id => id !== scan.id));
                  }
                }}
              />
              <div className="scan-info">
                <span className="date">{new Date(scan.created_at).toLocaleDateString()}</span>
                <span className="body-part">{scan.body_part}</span>
                <span className="urgency">{scan.urgency_level}</span>
              </div>
            </label>
          ))}
        </div>
      </div>
      
      {/* Deep Dive Selection */}
      <div className="dive-selection">
        <h3>Select Deep Dives to Include</h3>
        <div className="dive-list">
          {deepDives.map(dive => (
            <label key={dive.id} className="dive-item">
              <input
                type="checkbox"
                value={dive.id}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedDeepDives([...selectedDeepDives, dive.id]);
                  } else {
                    setSelectedDeepDives(selectedDeepDives.filter(id => id !== dive.id));
                  }
                }}
              />
              <div className="dive-info">
                <span className="date">{new Date(dive.created_at).toLocaleDateString()}</span>
                <span className="body-part">{dive.body_part}</span>
                <span className="status">{dive.status}</span>
              </div>
            </label>
          ))}
        </div>
      </div>
      
      {/* Additional Context */}
      <div className="additional-context">
        <h3>Additional Information (Optional)</h3>
        <textarea
          placeholder="Any other details you'd like to add..."
          value={primaryConcern}
          onChange={(e) => setPrimaryConcern(e.target.value)}
        />
      </div>
      
      <button 
        onClick={runTriage}
        disabled={selectedQuickScans.length === 0 && selectedDeepDives.length === 0}
      >
        Get Specialist Recommendation
      </button>
      
      {triageResult && (
        <TriageResults 
          result={triageResult}
          onSelect={onSpecialtySelected}
        />
      )}
    </div>
  );
};

// TriageResults.jsx
const TriageResults = ({ result, onSelect }) => {
  const urgencyColors = {
    routine: 'green',
    urgent: 'yellow',
    emergent: 'red'
  };
  
  return (
    <div className="triage-results">
      <div className={`urgency-banner ${urgencyColors[result.urgency]}`}>
        {result.urgency === 'emergent' && 
          <strong>⚠️ Seek immediate medical attention</strong>
        }
      </div>
      
      <div className="primary-recommendation">
        <h3>Recommended Specialist</h3>
        <div className="specialty-card">
          <h4>{result.primary_specialty}</h4>
          <div className="confidence-meter">
            <div style={{width: `${result.confidence * 100}%`}} />
          </div>
          <p>{result.reasoning}</p>
          <button onClick={() => onSelect(result.primary_specialty)}>
            Generate {result.primary_specialty} Report
          </button>
        </div>
      </div>
      
      {result.secondary_specialties?.length > 0 && (
        <div className="other-options">
          <h4>Also Consider:</h4>
          {result.secondary_specialties.map(spec => (
            <div key={spec.specialty} className="secondary-specialty">
              <span>{spec.specialty}</span>
              <small>{spec.reason}</small>
            </div>
          ))}
        </div>
      )}
      
      {result.red_flags?.length > 0 && (
        <div className="red-flags">
          <h4>⚠️ Important Warning Signs:</h4>
          <ul>
            {result.red_flags.map(flag => <li key={flag}>{flag}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
};
```

### B. Enhanced Report Display Component
```jsx
// SpecialistReportView.jsx
const SpecialistReportView = ({ report }) => {
  const [activeSection, setActiveSection] = useState('summary');
  
  return (
    <div className="specialist-report">
      {/* Header with key info */}
      <ReportHeader report={report} />
      
      {/* Navigation tabs */}
      <div className="report-tabs">
        <button 
          className={activeSection === 'summary' ? 'active' : ''}
          onClick={() => setActiveSection('summary')}
        >
          Summary
        </button>
        <button 
          className={activeSection === 'clinical' ? 'active' : ''}
          onClick={() => setActiveSection('clinical')}
        >
          Clinical Details
        </button>
        <button 
          className={activeSection === 'tests' ? 'active' : ''}
          onClick={() => setActiveSection('tests')}
        >
          Tests & Workup
        </button>
        <button 
          className={activeSection === 'treatment' ? 'active' : ''}
          onClick={() => setActiveSection('treatment')}
        >
          Treatment Plan
        </button>
      </div>
      
      {/* Section content */}
      <div className="report-content">
        {activeSection === 'summary' && 
          <SummarySection data={report.report_data} />
        }
        {activeSection === 'clinical' && 
          <ClinicalSection 
            data={report.report_data} 
            specialty={report.report_type}
          />
        }
        {activeSection === 'tests' && 
          <TestsSection data={report.report_data.diagnostic_priorities} />
        }
        {activeSection === 'treatment' && 
          <TreatmentSection data={report.report_data.treatment_recommendations} />
        }
      </div>
    </div>
  );
};
```

### C. Clinical Scales Visualization
```jsx
// ClinicalScales.jsx - Example for Neurology
const NeurologyScales = ({ assessmentData }) => {
  const midasGrade = {
    'I': { label: 'Minimal disability', color: 'green' },
    'II': { label: 'Mild disability', color: 'yellow' },
    'III': { label: 'Moderate disability', color: 'orange' },
    'IV': { label: 'Severe disability', color: 'red' }
  };
  
  return (
    <div className="clinical-scales">
      <div className="scale-card">
        <h4>MIDAS Score</h4>
        <div className="score-display">
          <span className="score-number">
            {assessmentData.clinical_scales.midas_score.calculated}
          </span>
          <span 
            className="grade" 
            style={{color: midasGrade[assessmentData.clinical_scales.midas_score.grade].color}}
          >
            Grade {assessmentData.clinical_scales.midas_score.grade}
          </span>
        </div>
        <p>{midasGrade[assessmentData.clinical_scales.midas_score.grade].label}</p>
        
        <div className="score-breakdown">
          <div className="breakdown-item">
            <span>Missed work:</span>
            <strong>{assessmentData.clinical_scales.midas_score.breakdown.missed_work} days</strong>
          </div>
          <div className="breakdown-item">
            <span>Reduced productivity:</span>
            <strong>{assessmentData.clinical_scales.midas_score.breakdown.reduced_productivity} days</strong>
          </div>
          {/* Add other breakdown items */}
        </div>
      </div>
    </div>
  );
};
```

### D. Timeline Visualization
```jsx
// SymptomTimeline.jsx
const SymptomTimeline = ({ timeline }) => {
  return (
    <div className="symptom-timeline">
      <h3>Symptom Progression</h3>
      <div className="timeline-container">
        {timeline.map((event, idx) => (
          <div key={idx} className="timeline-event">
            <div className="timeline-date">
              {new Date(event.date).toLocaleDateString()}
            </div>
            <div className="timeline-content">
              <h4>{event.symptoms}</h4>
              <div className="severity-badge">
                Severity: {event.severity}/10
              </div>
              <p>Context: {event.context}</p>
              <p>Duration: {event.duration}</p>
              {event.resolution && 
                <p className="resolution">Resolved by: {event.resolution}</p>
              }
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### E. Treatment Plan Display
```jsx
// TreatmentPlan.jsx
const TreatmentPlan = ({ specialty, recommendations }) => {
  return (
    <div className="treatment-plan">
      {/* Medications */}
      {recommendations.immediate_medical_therapy && (
        <div className="medication-section">
          <h3>Recommended Medications</h3>
          {recommendations.immediate_medical_therapy.map((med, idx) => (
            <div key={idx} className="medication-card">
              <h4>{med.medication}</h4>
              <p className="rationale">{med.rationale}</p>
              {med.instructions && 
                <p className="instructions">📋 {med.instructions}</p>
              }
              {med.monitoring && 
                <p className="monitoring">⚠️ Monitor: {med.monitoring}</p>
              }
            </div>
          ))}
        </div>
      )}
      
      {/* Lifestyle modifications */}
      {recommendations.lifestyle_interventions && (
        <div className="lifestyle-section">
          <h3>Lifestyle Changes</h3>
          <div className="lifestyle-grid">
            {Object.entries(recommendations.lifestyle_interventions).map(([key, value]) => (
              <div key={key} className="lifestyle-card">
                <h4>{key.charAt(0).toUpperCase() + key.slice(1)}</h4>
                <p>{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

## 4. Key UI/UX Improvements

### A. Progressive Disclosure
```jsx
// Don't show everything at once
const ReportSection = ({ title, summary, details, priority }) => {
  const [expanded, setExpanded] = useState(priority === 'high');
  
  return (
    <div className="report-section">
      <div className="section-header" onClick={() => setExpanded(!expanded)}>
        <h3>{title}</h3>
        <p className="summary">{summary}</p>
        <button className="expand-btn">
          {expanded ? 'Show less' : 'Show more'}
        </button>
      </div>
      
      {expanded && (
        <div className="section-details">
          {details}
        </div>
      )}
    </div>
  );
};
```

### B. Visual Priority Indicators
```jsx
// Color-code by urgency
const TestRecommendation = ({ test }) => {
  const timingColors = {
    'same day': 'red',
    'within 1 week': 'orange',
    'within 2 weeks': 'yellow',
    'routine': 'green'
  };
  
  return (
    <div className="test-recommendation">
      <div 
        className="timing-indicator" 
        style={{backgroundColor: timingColors[test.timing] || 'gray'}}
      />
      <div className="test-info">
        <h4>{test.test}</h4>
        <p>{test.rationale}</p>
        <span className="timing">{test.timing}</span>
      </div>
    </div>
  );
};
```

### C. Actionable Summary Cards
```jsx
const ActionableSummary = ({ reportData, specialty }) => {
  return (
    <div className="actionable-summary">
      <div className="action-cards">
        {/* Immediate Actions */}
        <div className="action-card urgent">
          <h4>Do This First</h4>
          <ul>
            {reportData.diagnostic_priorities.immediate.map(item => (
              <li key={item.test}>
                <strong>{item.test}</strong>
                <small>{item.timing}</small>
              </li>
            ))}
          </ul>
        </div>
        
        {/* Key Findings */}
        <div className="action-card findings">
          <h4>Key Findings</h4>
          <ul>
            {/* Extract key findings based on specialty */}
          </ul>
        </div>
        
        {/* Next Steps */}
        <div className="action-card next-steps">
          <h4>Next Steps</h4>
          <p>{reportData.follow_up_plan.timing}</p>
          <button className="schedule-btn">
            Schedule {specialty} Appointment
          </button>
        </div>
      </div>
    </div>
  );
};
```

## 5. Mobile Responsive Design

```css
/* Mobile-first approach */
.specialist-report {
  padding: 1rem;
}

.report-tabs {
  display: flex;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-bottom: 1rem;
}

.report-tabs button {
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  white-space: nowrap;
}

.clinical-scales {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 768px) {
  .clinical-scales {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .action-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
}

/* Timeline on mobile */
.timeline-container {
  position: relative;
  padding-left: 2rem;
}

.timeline-event::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ddd;
}
```

## 6. State Management

```typescript
// ReportStore.ts
interface ReportState {
  triageResult: TriageResult | null;
  currentReport: SpecialistReport | null;
  reportHistory: SpecialistReport[];
  loading: boolean;
  error: string | null;
}

const useReportStore = create<ReportState>((set) => ({
  triageResult: null,
  currentReport: null,
  reportHistory: [],
  loading: false,
  error: null,
  
  runTriage: async (params) => {
    set({ loading: true, error: null });
    try {
      const result = await api.post('/api/report/specialty-triage', params);
      set({ triageResult: result.data.triage_result, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },
  
  generateReport: async (specialty, analysisId) => {
    set({ loading: true, error: null });
    try {
      const endpoint = `/api/report/${specialty}`;
      const result = await api.post(endpoint, { analysis_id: analysisId });
      set({ 
        currentReport: result.data,
        reportHistory: [...get().reportHistory, result.data],
        loading: false 
      });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  }
}));
```

## 7. Data Visualization Components

```jsx
// For Cardiology - Functional Capacity Chart
const FunctionalCapacityChart = ({ data }) => {
  const metsScale = [
    { mets: 1, activity: 'Self-care' },
    { mets: 2, activity: 'Walking slowly' },
    { mets: 4, activity: 'Light housework' },
    { mets: 6, activity: 'Brisk walking' },
    { mets: 8, activity: 'Jogging' },
    { mets: 10, activity: 'Competitive sports' }
  ];
  
  return (
    <div className="capacity-chart">
      <h4>Functional Capacity</h4>
      <div className="mets-scale">
        {metsScale.map(level => (
          <div 
            key={level.mets}
            className={`mets-level ${
              data.current <= level.mets ? 'limited' : 'capable'
            }`}
          >
            <span className="mets">{level.mets} METs</span>
            <span className="activity">{level.activity}</span>
          </div>
        ))}
      </div>
      <div className="capacity-summary">
        <p>Current: {data.current} METs</p>
        <p>Baseline: {data.baseline} METs</p>
      </div>
    </div>
  );
};
```

## 8. Integration with Existing Features

```jsx
// Connect to existing report generation flow
const ReportGenerationFlow = () => {
  const [step, setStep] = useState('triage');
  const [selectedSpecialty, setSelectedSpecialty] = useState(null);
  
  return (
    <div className="report-flow">
      {step === 'triage' && (
        <SpecialtyTriage 
          onSpecialtySelected={(specialty) => {
            setSelectedSpecialty(specialty);
            setStep('generate');
          }}
        />
      )}
      
      {step === 'generate' && (
        <div>
          <h2>Generate {selectedSpecialty} Report</h2>
          {/* Your existing report generation UI */}
          <button onClick={generateSpecialistReport}>
            Create {selectedSpecialty} Report
          </button>
        </div>
      )}
      
      {step === 'view' && (
        <SpecialistReportView report={currentReport} />
      )}
    </div>
  );
};
```

## 9. Error Handling & Loading States

```jsx
const ReportContainer = () => {
  const { currentReport, loading, error } = useReportStore();
  
  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner" />
        <p>Analyzing your health data...</p>
        <p className="loading-tip">
          This may take a moment as we compile comprehensive insights
        </p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="error-state">
        <h3>Unable to generate report</h3>
        <p>{error}</p>
        <button onClick={retry}>Try Again</button>
      </div>
    );
  }
  
  return <SpecialistReportView report={currentReport} />;
};
```

## 10. Print-Friendly View

```jsx
const PrintableReport = ({ report }) => {
  return (
    <div className="printable-report">
      <style>
        {`
          @media print {
            .no-print { display: none; }
            .printable-report { 
              font-size: 12pt; 
              color: black;
              background: white;
            }
            .page-break { page-break-after: always; }
          }
        `}
      </style>
      
      <div className="report-header">
        <h1>{report.report_type} Specialist Report</h1>
        <p>Generated: {new Date(report.generated_at).toLocaleDateString()}</p>
      </div>
      
      {/* All sections formatted for print */}
      <button className="no-print" onClick={() => window.print()}>
        Print Report
      </button>
    </div>
  );
};
```

## Implementation Checklist

- [ ] Add specialty triage UI component
- [ ] Update report display for new structure
- [ ] Create specialty-specific visualizations
- [ ] Add clinical scales displays
- [ ] Implement timeline visualization
- [ ] Create treatment plan components
- [ ] Add progressive disclosure
- [ ] Implement visual priority indicators
- [ ] Ensure mobile responsiveness
- [ ] Add print functionality
- [ ] Update state management
- [ ] Add error handling
- [ ] Create loading states
- [ ] Test with sample data
- [ ] Add accessibility features