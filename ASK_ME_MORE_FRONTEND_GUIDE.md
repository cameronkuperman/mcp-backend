# Ask Me More - Frontend Implementation Guide

## ✅ Backend Fix Complete!

### What's Fixed:
1. **Normal Deep Dive**: Still limited to 6 questions max
2. **Ask Me More**: Now allows up to 5 additional questions (11 total)
3. **Target Confidence**: Continues until target is reached OR max questions hit
4. **Better Responses**: Returns actual questions instead of "max reached" message

## API Response Changes

### When Confidence Target Reached:
```json
{
  "status": "success",
  "message": "Target confidence of 90% already achieved",
  "current_confidence": 92,
  "questions_needed": 0
}
```

### When Continuing Questions:
```json
{
  "status": "success",
  "question": "Have you noticed if your symptoms change with specific activities?",
  "question_number": 7,
  "question_category": "temporal_factors",
  "current_confidence": 70,
  "target_confidence": 90,
  "confidence_gap": 20,
  "estimated_questions_remaining": 2,
  "max_questions_remaining": 4,
  "reasoning": "Understanding patterns can help narrow the diagnosis",
  "expected_confidence_gain": 10
}
```

### When Max Questions Reached (but confidence < target):
```json
{
  "status": "success",
  "message": "Maximum additional questions (5) reached. Current confidence: 85%",
  "questions_asked": 5,
  "should_finalize": true,
  "current_confidence": 85,
  "target_confidence": 90,
  "info": "Consider using Ultra Think for higher confidence analysis"
}
```

## Frontend Implementation

### 1. Update Ask Me More Handler
```typescript
async function handleAskMeMore() {
  const response = await fetch('/api/deep-dive/ask-more', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId,
      current_confidence: currentConfidence,
      target_confidence: 90,  // Default target
      max_questions: 5  // Max additional questions
    })
  });

  const data = await response.json();

  if (data.question) {
    // Continue with new question
    setCurrentQuestion(data.question);
    setQuestionNumber(data.question_number);
    setEstimatedRemaining(data.estimated_questions_remaining);
  } else if (data.should_finalize) {
    // Hit max questions but didn't reach target
    showMessage(data.message);
    if (data.current_confidence < 90) {
      showUltraThinkOption(); // Suggest Ultra Think
    }
  } else if (data.current_confidence >= data.target_confidence) {
    // Target reached!
    showSuccessMessage("Target confidence achieved!");
  }
}
```

### 2. Update UI to Show Progress
```typescript
const AskMeMoreProgress = ({ 
  currentConfidence, 
  targetConfidence, 
  questionsAsked, 
  maxAdditional = 5 
}) => {
  const confidenceGap = targetConfidence - currentConfidence;
  const questionsRemaining = maxAdditional - questionsAsked;

  return (
    <div className="ask-more-progress">
      <div className="confidence-bar">
        <div className="current" style={{ width: `${currentConfidence}%` }} />
        <div className="target-marker" style={{ left: `${targetConfidence}%` }} />
      </div>
      
      <div className="stats">
        <p>Current: {currentConfidence}% → Target: {targetConfidence}%</p>
        <p>Questions remaining: {questionsRemaining} of {maxAdditional} additional</p>
        {confidenceGap > 15 && questionsRemaining < 3 && (
          <p className="warning">May need Ultra Think to reach target</p>
        )}
      </div>
    </div>
  );
};
```

### 3. Handle Different Response Types
```typescript
interface AskMoreResponse {
  status: 'success' | 'error';
  
  // When continuing
  question?: string;
  question_number?: number;
  question_category?: string;
  current_confidence?: number;
  target_confidence?: number;
  confidence_gap?: number;
  estimated_questions_remaining?: number;
  max_questions_remaining?: number;
  
  // When complete/limited
  message?: string;
  should_finalize?: boolean;
  questions_asked?: number;
  info?: string;
}

function processAskMoreResponse(response: AskMoreResponse) {
  if (response.question) {
    // New question available
    return { 
      type: 'CONTINUE', 
      question: response.question,
      progress: {
        current: response.current_confidence,
        target: response.target_confidence,
        remaining: response.max_questions_remaining
      }
    };
  }
  
  if (response.should_finalize) {
    // Hit limit but didn't reach target
    return { 
      type: 'MAX_REACHED',
      needsUltraThink: response.current_confidence < response.target_confidence,
      message: response.message
    };
  }
  
  if (response.message?.includes('achieved')) {
    // Target confidence reached
    return { type: 'TARGET_REACHED' };
  }
  
  return { type: 'ERROR', message: response.error || 'Unknown error' };
}
```

### 4. Show Ultra Think Option When Needed
```typescript
const ShowUltraThinkOption = ({ currentConfidence, targetConfidence }) => {
  if (currentConfidence >= targetConfidence) return null;

  return (
    <div className="ultra-think-suggestion">
      <h3>Need Higher Confidence?</h3>
      <p>Current analysis reached {currentConfidence}% confidence.</p>
      <p>Ultra Think can provide deeper analysis to reach {targetConfidence}%.</p>
      <button onClick={handleUltraThink}>
        Use Ultra Think (Grok 4)
      </button>
    </div>
  );
};
```

## Testing the Fix

```bash
# Test Ask Me More continuing beyond 6 questions
curl -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "current_confidence": 70,
    "target_confidence": 90,
    "max_questions": 5
  }' | jq '.'
```

## Summary

- **Regular Deep Dive**: 6 questions max (unchanged)
- **Ask Me More**: Up to 5 additional questions (11 total)
- **Smart Limits**: Stops at target confidence OR max questions
- **Fallback**: Suggests Ultra Think if can't reach target
- **No more "max reached" errors** when confidence is low

The backend now properly handles continuing questions to reach target confidence! 🎉