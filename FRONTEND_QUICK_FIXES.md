# Frontend Quick Fixes - Copy & Paste 📋

## 1. Fix Deep Dive Response Handling
```javascript
// In your deep dive complete handler
const handleDeepDiveComplete = async (sessionId) => {
  const response = await fetch('/api/deep-dive/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      fallback_model: 'deepseek/deepseek-chat'
    })
  });

  const data = await response.json();
  
  // ✅ NO JSON.parse needed!
  const analysis = data.analysis; // Already an object
  console.log('Confidence:', analysis.confidence); // Number
  console.log('Condition:', analysis.primaryCondition); // Should be real medical term
};
```

## 2. Fix Ask Me More Request
```javascript
// In your ask me more handler
const handleAskMeMore = async () => {
  const response = await fetch('/api/deep-dive/ask-more', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: currentSessionId,
      current_confidence: latestConfidence, // ✅ Add this field!
      target_confidence: 90,
      max_questions: 5 // ✅ Keep this!
    })
  });

  const data = await response.json();
  
  if (data.question) {
    // Continue with question
    setCurrentQuestion(data.question);
    setQuestionNumber(data.question_number);
    // DON'T auto-complete here!
  } else if (data.should_finalize) {
    // Max questions reached
    showMessage(data.message);
    if (data.current_confidence < 90) {
      showUltraThinkButton();
    }
  }
};
```

## 3. Remove Auto-Complete
```javascript
// ❌ Find and remove this pattern:
askMeMore().then(() => completeDeepDive());

// ✅ Replace with:
askMeMore().then(response => {
  if (response.question) {
    // Just show the question, don't complete
    displayQuestion(response.question);
  }
});
```

## 4. Type Updates (if using TypeScript)
```typescript
interface DeepDiveAnalysis {
  confidence: number;  // NOT string
  primaryCondition: string;
  differentials: Array<{
    condition: string;
    probability: number;  // NOT string
  }>;
}

interface AskMoreRequest {
  session_id: string;
  current_confidence?: number;  // Add this
  target_confidence?: number;
  max_questions?: number;  // Keep this
}
```

## 5. Debug Helper
```javascript
// Add this temporarily to verify responses
window.debugDeepDive = (response) => {
  console.log('=== DEEP DIVE DEBUG ===');
  console.log('Analysis type:', typeof response.analysis);
  console.log('Confidence type:', typeof response.analysis?.confidence);
  console.log('Is generic?', response.analysis?.primaryCondition?.includes('Analysis of'));
  console.log('Full response:', response);
};
```

## That's It!
Main fixes:
1. Remove JSON.parse() on analysis
2. Add current_confidence to Ask Me More
3. Don't auto-complete after Ask Me More
4. Update types to expect numbers not strings

The backend is ready - just apply these frontend fixes! 🚀