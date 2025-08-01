# Backend Implementation Guide: General Assessment System (UPDATED)

## Overview

This guide provides complete implementation details for the General Assessment endpoints in the MCP backend. The system supports three assessment types:
- **Flash Assessment**: Quick triage from free text using Gemini Flash Lite
- **General Assessment**: Structured category-based analysis  
- **General Deep Dive**: Multi-step conversational diagnosis

## System Architecture

```
Frontend → API Endpoints → System Prompts (with user medical data) → LLM → Response Processing → Database → Timeline Events
```

## Database Setup

Run the migration file `/migrations/create_general_assessment_tables.sql` to create:
- `flash_assessments`
- `general_assessments`
- `general_deepdive_sessions`
- `timeline_events` (with auto-population triggers)

## API Implementation Status

✅ **COMPLETED**: All three endpoints have been implemented in `/api/general_assessment.py`:
- `/api/flash-assessment` - Quick triage using Gemini Flash Lite
- `/api/general-assessment` - Structured 7-category assessment
- `/api/general-deepdive/start` - Start conversational diagnosis
- `/api/general-deepdive/continue` - Continue with next question
- `/api/general-deepdive/complete` - Generate final analysis

## Seven Categories with System Prompts

### 1. Energy & Fatigue
```python
ENERGY_PROMPT = """You are analyzing energy and fatigue concerns. Consider:
- Circadian rhythm disruptions
- Sleep quality vs quantity  
- Nutritional deficiencies (B12, iron, vitamin D)
- Thyroid and hormonal issues
- Chronic fatigue syndrome patterns
- Post-viral fatigue
- Medication side effects from user's current meds: {medications}
- Physical activity levels and deconditioning"""
```

### 2. Mental Health
```python
MENTAL_PROMPT = """You are analyzing mental health concerns. Consider:
- Mood disorders (depression, bipolar)
- Anxiety disorders
- Stress-related conditions
- Trauma responses
- Medication interactions from: {medications}
- Sleep-mood connections
- Cognitive symptoms vs emotional symptoms
- Social and environmental factors
Note: Be supportive and non-judgmental in all responses."""
```

### 3. Feeling Sick
```python
SICK_PROMPT = """You are analyzing acute illness symptoms. Consider:
- Infectious vs non-infectious causes
- Symptom progression timeline
- Contagion risk
- Dehydration signs
- When to seek immediate care
- User's chronic conditions that may complicate: {conditions}
- Recent exposures or travel
- Seasonal patterns"""
```

### 4. Medication Side Effects
```python
MEDICATION_PROMPT = """You are analyzing potential medication side effects. Consider:
- User's current medications: {medications}
- Drug interactions
- Timing of symptoms vs medication schedule
- Dose-dependent effects
- Alternative medications
- When to contact prescriber
- Distinguishing side effects from underlying conditions"""
```

### 5. Multiple Issues
```python
MULTIPLE_PROMPT = """You are analyzing multiple concurrent health issues. Consider:
- Systemic conditions that cause multiple symptoms
- Medication cascades
- Stress/anxiety manifesting physically
- Autoimmune conditions
- Whether symptoms are related or separate
- Priority of addressing each issue
- Potential common underlying causes"""
```

### 6. Unsure
```python
UNSURE_PROMPT = """You are helping someone who isn't sure what's wrong. Consider:
- Vague or non-specific symptoms
- Somatization of stress/anxiety
- Early-stage conditions
- Need for basic health screening
- Importance of validation and support
- Gentle guidance toward appropriate care
- Pattern recognition from symptom clusters"""
```

### 7. Physical/Body (NEW)
```python
PHYSICAL_PROMPT = """You are analyzing physical pain and injuries. Consider:
- Musculoskeletal vs neurological causes
- Injury patterns and mechanisms
- Red flags requiring immediate care
- Movement patterns and compensations
- Referred pain possibilities
- Chronic vs acute presentation
- Impact on daily activities
- Previous injuries in the area"""
```

## Form Data Structure

### Base Fields (All Categories)
```javascript
{
  symptoms: string              // Main symptom description
  duration: string             // "Today" | "Few days" | "1-2 weeks" | "Month+" | "Longer"
  impactLevel: number          // 1-10 scale
  aggravatingFactors: string[] // ["stress", "poor_sleep", "diet", "weather", "activity", "nothing_specific"]
  triedInterventions: string[] // ["rest", "otc_medication", "more_sleep", "diet_change", "exercise", "relaxation", "caffeine", "nothing"]
  
  // Optional location field for relevant categories
  bodyLocation?: {
    regions: string[]          // Can select multiple body regions
    description?: string       // Free text description of location
  }
}
```

### Category-Specific Fields

#### Energy & Fatigue
```javascript
{
  energyPattern: string        // "Morning" | "Afternoon" | "Evening" | "All day"
  wakingUpFeeling: string      // "Refreshed" | "Tired" | "Exhausted"
  sleepHours: string           // e.g., "6-7 hours"
}
```

#### Mental Health
```javascript
{
  moodPattern: string          // "Stable" | "Fluctuating" | "Declining"
  concentrationLevel: number   // 1-10 scale
  triggerEvents: string        // Free text about triggers
}
```

#### Feeling Sick
```javascript
{
  temperatureFeeling: string   // "Hot/Feverish" | "Cold/Chills" | "Normal" | "Fluctuating"
  symptomProgression: string   // "Worse" | "Stable" | "Better"
  contagiousExposure: boolean  // true/false
}
```

#### Medication Side Effects
```javascript
{
  symptomTiming: string        // "Right after" | "Hours later" | "Random times"
  doseChanges: boolean         // true/false
  timeSinceStarted: string     // e.g., "2 weeks", "3 months"
}
```

#### Multiple Issues
```javascript
{
  primaryConcern: string       // Text describing main concern
  symptomConnection: string    // "Related" | "Unrelated" | "Unsure"
  secondaryConcerns: string[]  // Array of other concerns
}
```

#### Unsure
```javascript
{
  currentActivity: string      // What made them seek help
  recentChanges: string        // Recent life/routine changes
}
```

#### Physical/Body (NEW)
```javascript
{
  bodyRegion: string           // "head_neck" | "chest" | "abdomen" | "back" | "arms" | "legs" | "joints" | "skin" | "multiple"
  issueType: string            // "pain" | "injury" | "rash" | "swelling" | "numbness" | "weakness" | "other"
  occurrencePattern: string    // "constant" | "movement" | "rest" | "random"
  affectedSide?: string        // "left" | "right" | "both" | "center"
  radiatingPain?: boolean      // true/false
  specificMovements?: string   // Description of triggering movements
}
```

## Model Selection

### Current Models in Use:
- **Flash Assessment**: `google/gemini-2.5-flash-lite` (fast, conversational)
- **General Assessment**: `deepseek/deepseek-chat` (DeepSeek V3 - balanced)
- **General Deep Dive**: `deepseek/deepseek-chat` (consistent JSON output)

### Model Rationale:
- Flash uses Gemini Flash Lite for quick, cost-effective triage
- General & Deep Dive use DeepSeek V3 for reliable JSON parsing
- All models support structured output format

## Location Fields Usage

The optional `bodyLocation` field should be shown for:
- **Physical**: Always show (primary use case)
- **Sick**: Show when symptoms are localized
- **Medication**: Show for localized side effects (rashes, pain)
- **Energy**: Optional for localized fatigue
- **Mental**: Optional for physical manifestations

## Response Formats

### Flash Assessment Response
```json
{
  "flash_id": "uuid",
  "response": "Conversational response text",
  "main_concern": "Extracted primary issue",
  "urgency": "low|medium|high|emergency",
  "confidence": 85,
  "next_steps": {
    "recommended_action": "general-assessment|body-scan|see-doctor|monitor",
    "reason": "Brief explanation"
  }
}
```

### General Assessment Response
```json
{
  "assessment_id": "uuid",
  "analysis": {
    "primary_assessment": "Main clinical impression",
    "confidence": 80,
    "key_findings": ["finding1", "finding2"],
    "possible_causes": [
      {"condition": "name", "likelihood": 70, "explanation": "why"}
    ],
    "recommendations": ["recommendation1", "recommendation2"],
    "urgency": "low|medium|high|emergency",
    "follow_up_questions": ["question1", "question2"]
  }
}
```

### Deep Dive Response Flow
1. **Start**: Returns first question
2. **Continue**: Returns next question or signals ready for analysis
3. **Complete**: Returns comprehensive analysis with differential diagnosis

## Testing Examples

```bash
# Flash Assessment
curl -X POST http://localhost:8000/api/flash-assessment \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "My knee hurts when I walk",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'

# General Assessment - Physical Category
curl -X POST http://localhost:8000/api/general-assessment \
  -H "Content-Type: application/json" \
  -d '{
    "category": "physical",
    "form_data": {
      "symptoms": "Sharp knee pain",
      "duration": "1-2 weeks",
      "impactLevel": 7,
      "bodyRegion": "legs",
      "issueType": "pain",
      "occurrencePattern": "movement",
      "affectedSide": "right",
      "specificMovements": "Hurts when going up stairs"
    },
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'

# General Assessment - Energy Category  
curl -X POST http://localhost:8000/api/general-assessment \
  -H "Content-Type: application/json" \
  -d '{
    "category": "energy",
    "form_data": {
      "symptoms": "Constant fatigue, brain fog",
      "duration": "Month+",
      "impactLevel": 8,
      "energyPattern": "All day",
      "sleepHours": "8-9",
      "wakingUpFeeling": "Exhausted"
    }
  }'
```

## Important Implementation Notes

1. **Medical Data Integration**: Always fetch user medical data when user_id is provided
2. **Category Validation**: Ensure category is one of the 7 valid options
3. **Location Context**: Include bodyLocation in prompts when provided
4. **Error Handling**: Return structured errors with helpful messages
5. **Timeline Integration**: Database triggers auto-populate timeline_events
6. **Model Fallbacks**: Consider implementing fallback models for reliability

## Migration SQL Required

```sql
-- Add physical category to enum
ALTER TYPE assessment_category ADD VALUE 'physical';

-- Ensure all tables support the new category
-- Timeline triggers will automatically handle new category
```

## Summary

The General Assessment system provides a flexible, category-based approach to health concerns that don't fit the precise 3D body visualization model. With 7 categories including the new Physical category, users can get appropriate assessments for systemic issues, vague symptoms, or multi-region pain. The system integrates seamlessly with existing user medical data and maintains consistency with the body-based assessment UI patterns.