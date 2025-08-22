# Assessment Follow-Up System - Complete Implementation Guide

## Overview

The Assessment Follow-Up System enables temporal tracking of medical conditions over time, allowing users to provide updates on their health status days, weeks, or even months after their initial assessment. Unlike the refinement system (which improves confidence immediately), follow-ups leverage time to better understand condition progression.

## System Architecture

### Key Design Principles
1. **Immutability**: Each follow-up creates a new assessment record (never modifies existing)
2. **Event Sourcing**: All interactions are tracked as events for complete audit trail
3. **Chain-Based**: Follow-ups are linked via `chain_id` for progression tracking
4. **Temporal Awareness**: System understands time gaps and adjusts questions accordingly
5. **Medical Integration**: Includes doctor visit tracking with jargon translation

## Database Schema

### Core Tables
- `assessment_follow_ups` - Main follow-up data with analysis
- `follow_up_events` - Event sourcing for all interactions
- `medical_visits` - Normalized medical visit information
- `follow_up_schedules` - Reminder scheduling (future feature)

### Key Relationships
```sql
assessment (any type) → chain_id → follow_ups (1:many)
follow_up → medical_visit (1:1 optional)
chain_id → events (1:many)
```

## API Endpoints

### 1. Get Follow-Up Questions
```
GET /api/follow-up/questions/{assessment_id}?assessment_type={type}&user_id={id}
```

**Response Structure:**
```json
{
  "base_questions": [
    // 5 standard questions (all optional)
    {
      "id": "q1",
      "question": "Have there been any changes since last time?",
      "type": "multiple_choice",
      "options": ["Much better", "Somewhat better", "No change", "Somewhat worse", "Much worse"],
      "required": false
    },
    // ... 4 more base questions
  ],
  "ai_questions": [
    // 3 AI-generated specific questions
    {
      "id": "ai_q1",
      "question": "You mentioned the pain moves from temple to jaw - is this still happening?",
      "type": "text",
      "category": "symptom_tracking",
      "rationale": "Track specific symptom progression"
    },
    // ... 2 more AI questions
  ],
  "context": {
    "chain_id": "uuid",
    "days_since_original": 7,
    "days_since_last": 3,
    "follow_up_number": 2,
    "has_active_tracking": true,
    "condition": "Migraine with stress triggers"
  },
  "validation": {
    "min_questions_required": 1,
    "message": "Please answer at least one question to continue"
  }
}
```

### 2. Submit Follow-Up
```
POST /api/follow-up/submit
```

**Request Body:**
```json
{
  "assessment_id": "uuid",
  "assessment_type": "general_assessment",
  "chain_id": "uuid",
  "responses": {
    "q1": "Somewhat better",
    "q2": "Less frequent headaches",
    "q3": "Somewhat better",
    "q4": "Yes",
    "q4_text": "Stress triggers identified",
    "q5": false,
    "ai_q1": "Response to AI question 1",
    "ai_q2": "Response to AI question 2",
    "ai_q3": "Response to AI question 3"
  },
  "medical_visit": null,  // Or medical visit object if q5 = true
  "user_id": "uuid"
}
```

**Medical Visit Object (if applicable):**
```json
{
  "provider_type": "specialist",
  "provider_specialty": "Neurology",
  "assessment": "Doctor's assessment text",
  "treatments": "Medications or procedures started",
  "follow_up_timing": "2 weeks"
}
```

**Response:**
```json
{
  "follow_up_id": "uuid",
  "chain_id": "uuid",
  "assessment": {
    "condition": "Migraine with stress triggers",
    "confidence": 85,
    "severity": "moderate",
    "progression": "improving"
  },
  "assessment_evolution": {
    "original_assessment": "Tension headache",
    "current_assessment": "Migraine with stress triggers",
    "confidence_change": "60% → 85%",
    "diagnosis_refined": true,
    "key_discoveries": [
      "Weather changes are a trigger",
      "Coffee makes it worse"
    ]
  },
  "progression_narrative": {
    "summary": "You're following a typical recovery pattern",
    "details": "The reduction in frequency from daily to 3x/week...",
    "milestone": "Next milestone: pain-free days by day 10"
  },
  "pattern_insights": {
    "discovered_patterns": [
      "Symptoms worse before weather changes",
      "Morning symptoms improved with medication"
    ],
    "concerning_patterns": []
  },
  "treatment_efficacy": {
    "working": ["Ibuprofen", "Dark room"],
    "not_working": ["Meditation"],
    "should_try": ["Magnesium supplement"]
  },
  "recommendations": {
    "immediate": ["Continue ibuprofen"],
    "this_week": ["Start trigger journal"],
    "consider": ["Neurologist if no improvement"],
    "next_follow_up": "4 days"
  },
  "confidence_indicator": {
    "level": "high",
    "explanation": "Confidence improved from 60% to 85%",
    "visual": "⚫⚫⚫⚫⚪"
  },
  "medical_visit_explained": "Plain English explanation of doctor's assessment"
}
```

### 3. Get Follow-Up Chain
```
GET /api/follow-up/chain/{assessment_id}?include_events=true
```

**Response:**
```json
{
  "chain_id": "uuid",
  "follow_ups": [/* Array of all follow-ups in chain */],
  "events": [/* Array of all events if requested */],
  "total_follow_ups": 3,
  "confidence_progression": [60, 75, 85],
  "assessment_progression": ["Tension headache", "Migraine", "Migraine with triggers"],
  "has_medical_visits": true,
  "peak_confidence": 85,
  "latest_assessment": "Migraine with stress triggers",
  "total_days_tracked": 21
}
```

### 4. Translate Medical Jargon
```
POST /api/follow-up/medical-visit/explain
```

**Request:**
```json
{
  "medical_terms": "Prescribed amitriptyline 10mg qHS for prophylaxis",
  "context": "Headache treatment"
}
```

**Response:**
```json
{
  "original": "Prescribed amitriptyline 10mg qHS for prophylaxis",
  "explanation": "Your doctor prescribed a medication called amitriptyline...",
  "key_takeaways": [
    "Take 10mg every night at bedtime",
    "This helps prevent headaches from occurring"
  ],
  "action_items": [
    "Start medication tonight",
    "Track any side effects"
  ]
}
```

## Frontend Integration Guide

### 1. Follow-Up Flow

```javascript
// Step 1: Check if follow-up is available
const canFollowUp = (assessmentDate, minDays = 1) => {
  const daysSince = Math.floor((Date.now() - new Date(assessmentDate)) / (1000 * 60 * 60 * 24));
  return daysSince >= minDays;
};

// Step 2: Get follow-up questions
const getFollowUpQuestions = async (assessmentId, assessmentType) => {
  const response = await fetch(
    `/api/follow-up/questions/${assessmentId}?assessment_type=${assessmentType}&user_id=${userId}`
  );
  return response.json();
};

// Step 3: Display questions with proper UI
const FollowUpQuestions = ({ questions }) => {
  const [responses, setResponses] = useState({});
  const [showMedicalModal, setShowMedicalModal] = useState(false);
  
  return (
    <div>
      {/* Base Questions */}
      {questions.base_questions.map(q => (
        <QuestionComponent key={q.id} question={q} onChange={handleResponse} />
      ))}
      
      {/* AI Questions */}
      <h3>Specific Questions About Your Condition:</h3>
      {questions.ai_questions.map(q => (
        <AIQuestionComponent key={q.id} question={q} onChange={handleResponse} />
      ))}
      
      {/* Medical Visit Modal */}
      {showMedicalModal && <MedicalVisitModal onComplete={handleMedicalVisit} />}
    </div>
  );
};

// Step 4: Submit follow-up
const submitFollowUp = async (assessmentId, responses, medicalVisit = null) => {
  const response = await fetch('/api/follow-up/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assessment_id: assessmentId,
      assessment_type: 'general_assessment',
      chain_id: chainId,
      responses,
      medical_visit: medicalVisit,
      user_id: userId
    })
  });
  return response.json();
};
```

### 2. Medical Visit Modal

```javascript
const MedicalVisitModal = ({ onComplete }) => {
  const [visitData, setVisitData] = useState({
    provider_type: '',
    assessment: '',
    treatments: '',
    follow_up_timing: ''
  });
  
  return (
    <Modal>
      <h2>📋 Medical Visit Update</h2>
      
      <RadioGroup
        label="Who did you see?"
        options={['primary', 'specialist', 'urgent_care', 'er', 'telehealth']}
        onChange={type => setVisitData({...visitData, provider_type: type})}
      />
      
      {visitData.provider_type === 'specialist' && (
        <Input
          label="Specialty"
          placeholder="e.g., Neurology, Cardiology"
          onChange={spec => setVisitData({...visitData, provider_specialty: spec})}
        />
      )}
      
      <TextArea
        label="What was their assessment?"
        placeholder="What the doctor said about your condition"
        onChange={assessment => setVisitData({...visitData, assessment})}
      />
      
      <TextArea
        label="Did they start any treatments?"
        placeholder="Medications, procedures, therapy, etc."
        onChange={treatments => setVisitData({...visitData, treatments})}
      />
      
      <Input
        label="When do you need to follow up?"
        placeholder="e.g., 2 weeks, as needed"
        onChange={timing => setVisitData({...visitData, follow_up_timing: timing})}
      />
      
      <Button onClick={() => onComplete(visitData)}>Save Medical Visit</Button>
    </Modal>
  );
};
```

### 3. Displaying Results

```javascript
const FollowUpResults = ({ results }) => {
  const { 
    assessment_evolution,
    progression_narrative,
    pattern_insights,
    treatment_efficacy,
    confidence_indicator,
    medical_visit_explained
  } = results;
  
  return (
    <div>
      {/* Evolution Summary */}
      <Card>
        <h3>How Your Condition Has Evolved</h3>
        <ProgressBar 
          from={assessment_evolution.original_assessment}
          to={assessment_evolution.current_assessment}
          confidence={confidence_indicator.level}
        />
        <p>{assessment_evolution.confidence_change}</p>
        
        {assessment_evolution.key_discoveries.length > 0 && (
          <div>
            <h4>Key Discoveries:</h4>
            <ul>
              {assessment_evolution.key_discoveries.map(d => <li>{d}</li>)}
            </ul>
          </div>
        )}
      </Card>
      
      {/* Progression Story */}
      <Card>
        <h3>Your Progress</h3>
        <p>{progression_narrative.summary}</p>
        <details>
          <summary>More details</summary>
          <p>{progression_narrative.details}</p>
        </details>
        <Alert>{progression_narrative.milestone}</Alert>
      </Card>
      
      {/* Treatment Tracking */}
      <Card>
        <h3>Treatment Effectiveness</h3>
        <div className="treatment-grid">
          <div className="working">
            <h4>✅ What's Working</h4>
            {treatment_efficacy.working.map(t => <Chip>{t}</Chip>)}
          </div>
          <div className="not-working">
            <h4>❌ Not Working</h4>
            {treatment_efficacy.not_working.map(t => <Chip>{t}</Chip>)}
          </div>
          <div className="should-try">
            <h4>💡 Consider Trying</h4>
            {treatment_efficacy.should_try.map(t => <Chip>{t}</Chip>)}
          </div>
        </div>
      </Card>
      
      {/* Medical Visit Translation */}
      {medical_visit_explained && (
        <Card className="medical-explanation">
          <h3>🩺 What Your Doctor Meant</h3>
          <p>{medical_visit_explained}</p>
        </Card>
      )}
    </div>
  );
};
```

### 4. Chain Visualization

```javascript
const FollowUpChain = ({ chainData }) => {
  const { 
    confidence_progression,
    assessment_progression,
    total_days_tracked
  } = chainData;
  
  return (
    <div>
      <h3>Your Journey Over {total_days_tracked} Days</h3>
      
      {/* Confidence Graph */}
      <LineChart
        data={confidence_progression}
        label="Diagnostic Confidence"
        yAxis="Confidence %"
      />
      
      {/* Assessment Timeline */}
      <Timeline>
        {assessment_progression.map((assessment, i) => (
          <TimelineItem
            key={i}
            title={assessment}
            subtitle={`Follow-up ${i + 1}`}
            confidence={confidence_progression[i]}
          />
        ))}
      </Timeline>
    </div>
  );
};
```

## Assessment Type Support

The follow-up system supports these assessment types:
- ✅ `general_assessment` - All categories (energy, mental, sick, etc.)
- ✅ `quick_scan` - Body-specific quick scans
- ✅ `deep_dive` - Body-specific deep dives
- ✅ `general_deepdive` - General deep dive sessions
- ❌ `photo_analysis` - Has its own follow-up system (don't modify)

## Best Practices

### 1. Timing Guidelines
- Minimum 1 day between follow-ups (configurable)
- No maximum limit - supports year+ old assessments
- AI adjusts questions based on time gaps

### 2. Question Requirements
- At least 1 question must be answered (validation)
- All questions are optional individually
- Medical modal only appears if Q5 = "Yes"

### 3. State Management
```javascript
// Track follow-up state
const [followUpState, setFollowUpState] = useState({
  chainId: null,
  followUpNumber: 1,
  daysSinceOriginal: 0,
  responses: {},
  medicalVisit: null,
  isSubmitting: false
});

// Persist partially completed follow-ups
useEffect(() => {
  localStorage.setItem(`followup_${assessmentId}`, JSON.stringify(followUpState));
}, [followUpState]);
```

### 4. Error Handling
```javascript
try {
  const result = await submitFollowUp(assessmentId, responses);
  if (result.error) {
    showError("At least one question must be answered");
  } else {
    showSuccess("Follow-up completed!");
    navigateToResults(result);
  }
} catch (error) {
  showError("Failed to submit follow-up. Please try again.");
  console.error('Follow-up submission error:', error);
}
```

## Testing

Run the comprehensive test suite:
```bash
python test_follow_up_system.py
```

This tests:
1. Getting follow-up questions with AI generation
2. Submitting follow-up responses
3. Medical visit integration
4. Chain retrieval and visualization
5. Medical jargon translation
6. Validation rules

## Migration

Run the database migration:
```bash
psql -U your_user -d your_database -f migrations/create_assessment_follow_ups.sql
```

## Monitoring & Analytics

### Key Metrics to Track
- Average confidence improvement per follow-up
- Follow-up completion rates
- Time between follow-ups
- Medical visit correlation with outcomes
- Pattern discovery rate

### Event Types Tracked
- `follow_up_scheduled` - Questions generated
- `follow_up_started` - User began answering
- `follow_up_completed` - Successfully submitted
- `follow_up_abandoned` - Started but not finished
- `pattern_discovered` - New pattern identified
- `confidence_milestone` - Reached 90%+ confidence
- `diagnosis_changed` - Assessment evolved
- `medical_visit_added` - Doctor visit recorded

## Future Enhancements

1. **Automated Reminders**: Integration with notification system
2. **Predictive Scheduling**: AI suggests optimal follow-up timing
3. **Cross-Condition Intelligence**: Pattern detection across conditions
4. **Provider Integration**: Direct import of medical records
5. **Outcome Tracking**: Long-term health outcome correlation

## Support

For issues or questions:
- Check test output: `python test_follow_up_system.py`
- Review logs for AI question generation failures
- Ensure database migrations are applied
- Verify assessment exists before creating follow-up

---

Last Updated: 2025-01-22
Version: 1.0.0