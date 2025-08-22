# Frontend Intelligence Guide: Photo Analysis Question Detection

## Overview
The photo analysis endpoint now includes **automatic question detection** that intelligently identifies when users ask questions about their photos and provides direct, specific answers alongside the standard medical analysis.

## How It Works

### No API Changes Required
- Uses the existing `context` field in the `/api/photo-analysis/analyze` endpoint
- Fully backward compatible - no changes needed to existing frontend code
- The LLM automatically detects questions in the user's description

### What Gets Detected

The system recognizes various types of questions:

1. **Direct Questions**
   - "Is this serious?"
   - "What is this?"
   - "Should I see a doctor?"
   - "Does this look normal?"

2. **Implied Questions**
   - "I'm worried about this rash..."
   - "I'm not sure if this is healing properly"
   - "Could this be an infection?"
   - "I wonder if this is getting worse"

3. **Comparative Questions**
   - "Is this getting worse?"
   - "Has this improved since yesterday?"
   - "Is it bigger than before?"

4. **Concern Expressions**
   - "This looks concerning to me"
   - "I'm scared about this spot"
   - "Is this dangerous?"

## Response Structure

### When a Question IS Detected

```json
{
  "analysis_id": "uuid",
  "analysis": {
    "question_detected": true,
    "question_answer": "Based on the visual analysis, this appears to be a common dermatitis that is not immediately concerning. The redness and mild scaling suggest irritation rather than infection. However, monitoring for any spreading or increased symptoms is recommended.",
    "primary_assessment": "Contact dermatitis",
    "confidence": 85,
    "visual_observations": [...],
    "differential_diagnosis": [...],
    "recommendations": [...],
    "red_flags": [...],
    "trackable_metrics": [...],
    "urgency_level": "low",
    "follow_up_timing": "1 week"
  },
  "comparison": null,
  "expires_at": null
}
```

### When NO Question is Detected

```json
{
  "analysis_id": "uuid",
  "analysis": {
    "question_detected": false,
    // Note: question_answer field is NOT included
    "primary_assessment": "Seborrheic keratosis",
    "confidence": 90,
    "visual_observations": [...],
    "differential_diagnosis": [...],
    "recommendations": [...],
    "red_flags": [...],
    "trackable_metrics": [...],
    "urgency_level": "low",
    "follow_up_timing": "3 months"
  },
  "comparison": null,
  "expires_at": null
}
```

## Frontend Implementation

### Basic Usage (No Changes Needed)
If you're already using the photo analysis endpoint, the feature works automatically:

```javascript
const analyzePhoto = async (photoIds, sessionId, description) => {
  const response = await fetch('/api/photo-analysis/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      photo_ids: photoIds,
      session_id: sessionId,
      context: description,  // User's description/question goes here
      temporary_analysis: false
    })
  });
  
  const data = await response.json();
  return data;
};
```

### Enhanced UI to Show Question Answers

```javascript
const PhotoAnalysisResult = ({ analysisData }) => {
  const { analysis } = analysisData;
  
  return (
    <div>
      {/* Show direct answer if question was detected */}
      {analysis.question_detected && analysis.question_answer && (
        <div className="question-answer-section">
          <h3>Your Question Answered:</h3>
          <p className="direct-answer">{analysis.question_answer}</p>
        </div>
      )}
      
      {/* Standard analysis display */}
      <div className="analysis-section">
        <h3>Medical Analysis</h3>
        <p><strong>Assessment:</strong> {analysis.primary_assessment}</p>
        <p><strong>Confidence:</strong> {analysis.confidence}%</p>
        {/* ... rest of analysis display ... */}
      </div>
    </div>
  );
};
```

### Example User Flows

#### Flow 1: User Asks Direct Question
```javascript
// User uploads photo with description
const userInput = "Red rash on my arm, is this serious?";

// Send to API
const result = await analyzePhoto(
  ['photo-id-123'],
  'session-id-456',
  userInput
);

// Response includes question answer
console.log(result.analysis.question_detected); // true
console.log(result.analysis.question_answer); 
// "Based on the visual analysis, this rash appears to be..."
```

#### Flow 2: User Provides Description Only
```javascript
// User uploads photo with description
const userInput = "Mole on shoulder, 5mm diameter";

// Send to API
const result = await analyzePhoto(
  ['photo-id-789'],
  'session-id-012',
  userInput
);

// No question detected
console.log(result.analysis.question_detected); // false
console.log(result.analysis.question_answer); // undefined
```

## UI/UX Recommendations

### 1. Highlight Question Answers
When a question is detected, display the answer prominently:
- Use a distinct visual container (e.g., colored background, icon)
- Place it above the technical analysis
- Use conversational, reassuring language

### 2. Input Field Hints
Update placeholder text to encourage questions:
```html
<textarea 
  placeholder="Describe what you see or ask a question (e.g., 'Is this healing normally?')"
/>
```

### 3. Example Questions
Show users example questions they can ask:
- "Is this getting better?"
- "Should I be concerned?"
- "Does this look infected?"
- "Is this normal healing?"

### 4. Progressive Disclosure
Structure the response with hierarchy:
1. **Question Answer** (if detected) - Most prominent
2. **Primary Assessment** - Clear diagnosis
3. **Urgency Level** - Visual indicator (color/icon)
4. **Detailed Analysis** - Collapsible section
5. **Technical Metrics** - For tracking

## Testing Examples

### Test Case 1: Direct Question
**Input:**
```json
{
  "context": "This spot on my leg has been growing, should I see a doctor?"
}
```

**Expected Response Fields:**
- `question_detected`: true
- `question_answer`: Present with specific guidance about seeing a doctor

### Test Case 2: Implied Concern
**Input:**
```json
{
  "context": "I'm worried this mole looks different than last month"
}
```

**Expected Response Fields:**
- `question_detected`: true
- `question_answer`: Addresses the concern about changes

### Test Case 3: Pure Description
**Input:**
```json
{
  "context": "Brown spot, oval shape, approximately 8mm"
}
```

**Expected Response Fields:**
- `question_detected`: false
- `question_answer`: Not present in response

## Backend Logging

The backend logs question detection for monitoring:
```
✓ Question detected! Answer: Based on the visual analysis, this appears to be...
```

This helps track:
- How often users ask questions
- Types of questions being asked
- Quality of answers provided

## Benefits

1. **Better User Experience**
   - Direct answers to user concerns
   - Reduces anxiety with clear responses
   - More conversational interaction

2. **No Frontend Changes Required**
   - Works with existing implementations
   - Fully backward compatible
   - Optional UI enhancements only

3. **Intelligent Context Understanding**
   - Automatically detects various question formats
   - Provides relevant, specific answers
   - Maintains medical accuracy

## Migration Guide

### For Existing Implementations
**No changes required!** The feature works automatically with your current code.

### For Enhanced Experience
1. Check for `question_detected` in response
2. If true, display `question_answer` prominently
3. Update input placeholders to encourage questions
4. Add example questions in UI

## FAQ

**Q: What if the user asks multiple questions?**
A: The system will identify the primary question and provide a comprehensive answer that addresses the main concern.

**Q: Does this work with photo comparisons?**
A: Yes, questions about progression ("Is this getting worse?") work especially well with comparison photos.

**Q: What languages are supported?**
A: Currently optimized for English. Other languages may work but aren't guaranteed.

**Q: Can it detect medical emergencies?**
A: Yes, urgent concerns trigger both question answers and elevated urgency levels in the response.

## Summary

The automatic question detection feature enhances photo analysis by:
- Detecting questions in user descriptions automatically
- Providing direct, specific answers when questions are found
- Maintaining full backward compatibility
- Requiring zero changes to existing implementations
- Enabling optional UI enhancements for better UX

This creates a more intelligent, conversational experience that better addresses user concerns while maintaining medical accuracy and comprehensive analysis.