# Specialist Reports Complete Guide for Frontend UI

## Overview
This guide details exactly what each specialist report endpoint returns, with UI/UX suggestions to help create the perfect frontend interface.

## Common Structure (All Reports)

Every specialist report returns:
```json
{
  "report_id": "uuid",
  "report_type": "specialty_name",
  "specialty": "specialty_name",
  "generated_at": "ISO timestamp",
  "report_data": { ... },
  "status": "success"
}
```

### Executive Summary (All Reports Have This)
- **one_page_summary**: Long-form clinical overview (500-1000 chars)
  - 💡 UI Tip: Display as expandable card at top
- **key_findings**: Array of bullet points
  - 💡 UI Tip: Show as highlighted list with icons
- **chief_complaints**: Primary symptoms array
  - 💡 UI Tip: Tag-style display
- **action_items**: Immediate next steps
  - 💡 UI Tip: Checklist format with urgency colors
- **urgency_indicators**: Red flags (if present)
  - 💡 UI Tip: Alert banner if not empty

## Cardiology Report

### Unique Sections:
1. **cardiology_assessment**
   - chest_pain_characteristics: 
     - quality (sharp/dull/pressure)
     - triggers (exertion/rest/emotional)
     - duration & radiation
     - 💡 UI Tip: Visual pain diagram showing radiation patterns
   
   - cardiac_risk_factors: Array of risk factors with severity
     - 💡 UI Tip: Risk meter visualization
   
   - functional_capacity: METs calculation
     - 💡 UI Tip: Activity scale slider

2. **cardiologist_specific_findings**
   - ecg_interpretation_needed: boolean
   - rhythm_assessment: regular/irregular
   - murmur_characteristics: if detected
   - 💡 UI Tip: Heart diagram with clickable areas

3. **clinical_scales**
   - HEART_Score: 0-10 with breakdown
   - CHA2DS2_VASc: if AFib risk
   - 💡 UI Tip: Circular progress indicators with risk zones

### Diagnostic Recommendations
- Immediate tests (ECG, troponins)
- Imaging (echo, stress test)
- 💡 UI Tip: Timeline view showing test urgency

## Neurology Report

### Unique Sections:
1. **neurology_assessment**
   - headache_patterns:
     - frequency, triggers, character
     - 💡 UI Tip: Calendar heat map for frequency
   
   - neurological_symptoms:
     - motor (weakness patterns)
     - sensory (numbness/tingling)
     - cognitive (memory/confusion)
     - 💡 UI Tip: Body diagram for symptom mapping

2. **neurologist_specific_findings**
   - focal_deficits: Present/absent with details
   - gait_abnormalities: Description
   - reflexes: Hyperactive/normal/diminished
   - 💡 UI Tip: Neurological exam checklist view

3. **clinical_scales**
   - MIDAS_Score: Migraine disability
   - MoCA_Estimate: Cognitive assessment
   - 💡 UI Tip: Score cards with interpretation

## Dermatology Report

### Unique Sections:
1. **dermatology_assessment**
   - lesion_description:
     - morphology (macule/papule/plaque)
     - color, size, distribution
     - 💡 UI Tip: Visual glossary of terms
   
   - skin_symptoms:
     - pruritus level (0-10)
     - pain/burning
     - 💡 UI Tip: Severity sliders

2. **dermatologist_specific_findings**
   - photo_analysis: If photos provided
   - abcde_criteria: For concerning lesions
   - distribution_pattern: Localized/generalized
   - 💡 UI Tip: Body map with clickable regions

3. **lesion_analysis** (if photos)
   - identified_lesions: Array with locations
   - clinical_correlation: Match to symptoms
   - 💡 UI Tip: Photo gallery with annotations

## Psychiatry Report

### Unique Sections:
1. **psychiatry_assessment**
   - mood_symptoms:
     - depression_indicators
     - anxiety_features
     - 💡 UI Tip: Mood tracking graph
   
   - functional_impact:
     - work, social, self-care ratings
     - 💡 UI Tip: Life domain wheel chart

2. **safety_assessment**
   - risk_level: none/low/moderate/high
   - protective_factors: Array
   - 💡 UI Tip: Safety indicator with clear action steps

3. **clinical_scales**
   - PHQ9_Score: Depression (0-27)
   - GAD7_Score: Anxiety (0-21)
   - 💡 UI Tip: Score interpretation with severity zones

## Gastroenterology Report

### Unique Sections:
1. **gastroenterology_assessment**
   - gi_symptoms:
     - pain_location: Epigastric/RLQ/etc
     - bowel_patterns: Frequency/consistency
     - 💡 UI Tip: Abdomen quadrant diagram
   
   - dietary_triggers: Identified foods
   - weight_changes: Timeline
   - 💡 UI Tip: Symptom-food correlation chart

2. **alarm_symptoms**
   - bleeding, weight_loss, dysphagia
   - 💡 UI Tip: Red flag alerts if present

## Orthopedics Report

### Unique Sections:
1. **orthopedic_assessment**
   - affected_joints: Array with severity
   - mechanical_symptoms:
     - locking, catching, instability
     - 💡 UI Tip: Joint diagram with problem indicators
   
   - functional_limitations:
     - ambulation distance
     - stair climbing ability
     - 💡 UI Tip: Activity limitation scale

2. **orthopedist_specific_findings**
   - injury_mechanism: Traumatic/overuse/degenerative
   - red_flags: Fracture/infection signs
   - 💡 UI Tip: Timeline of injury progression

3. **clinical_scales**
   - Oswestry_Disability_Index: Back pain disability
   - KOOS: Knee-specific scores
   - 💡 UI Tip: Functional score dashboard

## Primary Care Report (Different Structure!)

### Unique Sections:
1. **preventive_care_gaps**
   - screening_due: Array of overdue screenings
   - immunizations_needed: Vaccines due
   - 💡 UI Tip: Preventive care checklist

2. **chronic_disease_assessment**
   - identified_conditions: With control status
   - risk_factors: Categorized by system
   - 💡 UI Tip: Chronic disease dashboard

3. **health_optimization**
   - lifestyle_counseling: Specific recommendations
   - behavioral_health: Mood/substance screening
   - 💡 UI Tip: Wellness wheel visualization

## Specialist-Extended Reports

### Nephrology
- **CKD_Staging**: eGFR and stage (G1-G5)
- **Volume_Assessment**: Fluid status
- 💡 UI Tip: Kidney function graph

### Urology
- **IPSS**: Prostate symptom score with subscales
- **Bladder_Diary**: Frequency/urgency metrics
- 💡 UI Tip: Symptom severity meter

### Gynecology
- **Menstrual_Pattern**: Classification and abnormalities
- **PCOS_Criteria**: Rotterdam criteria checklist
- 💡 UI Tip: Cycle tracking visualization

### Oncology & Physical Therapy
- Use general structure without specialty-specific assessments
- Focus on functional status and symptom burden

## UI/UX Recommendations

### 1. Progressive Disclosure
- Show executive summary first
- Expand to detailed sections on click
- Use accordions for subspecialty findings

### 2. Visual Elements
- Body diagrams for symptom mapping
- Severity scales with color coding
- Timeline views for symptom progression

### 3. Urgency Indicators
- Color-coded alerts (red/yellow/green)
- Sort action items by urgency
- Highlight red flags prominently

### 4. Clinical Scales Display
- Show score with interpretation
- Use progress bars/gauges
- Include confidence levels

### 5. Responsive Design Considerations
- Mobile: Stack sections vertically
- Tablet: 2-column layout
- Desktop: Dashboard view with widgets

### 6. Print View
- One-page summary format
- Include all critical findings
- QR code for full digital report

### 7. Interactivity
- Clickable body diagrams
- Hover tooltips for medical terms
- Expandable educational content

### 8. Data Visualization Priority
1. Executive summary - Card layout
2. Chief complaints - Tag cloud
3. Clinical scales - Gauge charts
4. Timeline data - Line graphs
5. Risk factors - Bar charts
6. Body systems - Anatomical diagrams

## Frontend Implementation Tips

1. **Create a Report Component Factory**
   - Base component with common sections
   - Specialty-specific components extending base
   - Dynamic field mapping for inconsistent naming

2. **Handle Missing Data Gracefully**
   - Show "Not assessed" vs hiding sections
   - Indicate confidence levels
   - Explain why data might be missing

3. **Optimize for Clinician Workflow**
   - Quick scan summary at top
   - Actionable items prominent
   - Easy export/share options

4. **Accessibility**
   - High contrast for critical alerts
   - Screen reader friendly structure
   - Keyboard navigation support

5. **State Management**
   - Cache reports locally
   - Allow offline viewing
   - Track viewed/unviewed sections