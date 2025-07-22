# Frontend Integration Guide - Final 🎯

## 1. Deep Dive Changes

### ❌ Remove ALL JSON.parse() calls
```javascript
// ❌ WRONG - Backend already returns objects
const analysis = JSON.parse(response.analysis);

// ✅ CORRECT - Use directly
const analysis = response.analysis;
```

### What You'll Get Now:
```javascript
// Instead of generic: "Analysis of Left Deltoid pain"
// You'll get real: "Rotator Cuff Tendinitis (shoulder tendon inflammation)"

{
  "analysis": {
    "confidence": 85,  // Number, not string
    "primaryCondition": "Rotator Cuff Tendinitis (shoulder tendon inflammation)",
    "differentials": [
      {"condition": "Impingement Syndrome", "probability": 70}  // probability is number
    ]
  }
}
```

## 2. Ask Me More Request Format

### ✅ Send These Fields:
```javascript
const askMoreRequest = {
  session_id: sessionId,
  current_confidence: 70,  // IMPORTANT: Send this!
  target_confidence: 90,
  max_questions: 5  // This works now!
};

// Backend also accepts alternate names:
// confidence: 70 (instead of current_confidence)
// target: 90 (instead of target_confidence)
```

### ❌ DON'T Auto-Complete:
```javascript
// ❌ BAD - This breaks Ask Me More
async function handleAskMore() {
  const response = await askMeMore();
  await completeDeepDive(); // NO! This finalizes session
}

// ✅ GOOD - Let user decide
async function handleAskMore() {
  const response = await askMeMore();
  if (response.question) {
    showQuestion(response.question);
    // Wait for user to answer
  }
}
```

## 3. Response Handling

### Ask Me More Returns 3 Types:

#### Type 1: Continue with Question
```javascript
{
  "status": "success",
  "question": "Do you hear clicking sounds when moving your shoulder?",
  "question_number": 7,
  "current_confidence": 70,
  "target_confidence": 90,
  "confidence_gap": 20,
  "estimated_questions_remaining": 2,
  "max_questions_remaining": 4
}
```

#### Type 2: Target Reached
```javascript
{
  "status": "success",
  "message": "Target confidence of 90% already achieved",
  "current_confidence": 92,
  "questions_needed": 0
}
```

#### Type 3: Max Questions (But Low Confidence)
```javascript
{
  "status": "success",
  "message": "Maximum additional questions (5) reached. Current confidence: 85%",
  "should_finalize": true,
  "current_confidence": 85,
  "target_confidence": 90,
  "info": "Consider using Ultra Think for higher confidence analysis"
}
```

## 4. Complete Frontend Flow

```javascript
class DeepDiveManager {
  async askMoreQuestions() {
    const response = await fetch('/api/deep-dive/ask-more', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId,
        current_confidence: this.currentConfidence, // Always send!
        target_confidence: 90,
        max_questions: 5
      })
    });

    const data = await response.json();

    // Handle response types
    if (data.error) {
      // Session not found - only happens with old sessions
      this.showError("Please complete analysis or start new Deep Dive");
      return;
    }

    if (data.question) {
      // Show new question
      this.currentQuestion = data.question;
      this.questionNumber = data.question_number;
      this.showProgress(data.confidence_gap, data.max_questions_remaining);
    } else if (data.should_finalize) {
      // Hit limit but didn't reach target
      this.showLimitReached(data.message);
      if (data.current_confidence < 90) {
        this.showUltraThinkOption();
      }
    } else if (data.message?.includes('achieved')) {
      // Success! Target reached
      this.showSuccess("Target confidence achieved!");
    }
  }
}
```

## 5. Important Notes

### For Old Sessions (before deploy):
- Won't have `initial_questions_count`
- Might error on Ask Me More
- Solution: Use new Deep Dive sessions

### For New Sessions:
- Everything works automatically
- Tracks up to 11 questions (6 initial + 5 more)
- Stops at target confidence OR max

### Always:
- Send `current_confidence` with Ask Me More
- Don't auto-complete after Ask Me More
- Check `analysis.primaryCondition` for real medical terms

## 6. Quick Test

```javascript
// In browser console after Deep Dive complete
const testAskMore = async (sessionId) => {
  const response = await fetch('/api/deep-dive/ask-more', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      current_confidence: 70,
      target_confidence: 90
    })
  });
  
  const data = await response.json();
  console.log('Ask Me More works?', !!data.question);
  console.log('Response:', data);
};

// Use with your session ID
testAskMore('your-session-id-here');
```

## Summary:
1. ✅ Remove JSON.parse() - responses are objects
2. ✅ Send `current_confidence` field
3. ✅ Don't auto-complete after Ask Me More
4. ✅ Handle 3 response types (question/target/limit)
5. ✅ Old sessions might error (expected)

The backend is ready - these frontend updates will make everything work! 🚀