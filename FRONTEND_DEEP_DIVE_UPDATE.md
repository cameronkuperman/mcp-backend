# Frontend Deep Dive Update Guide

## ⚠️ IMPORTANT: Backend Now Returns Objects, NOT Strings!

### 1. Remove Any JSON.parse() Calls

If your frontend has any of these, REMOVE them:

```javascript
// ❌ WRONG - Don't do this anymore!
const analysis = JSON.parse(response.analysis);

// ✅ CORRECT - Use directly
const analysis = response.analysis;
```

### 2. Check Your Deep Dive Client

In `deepdive-client.ts`, make sure you're NOT parsing:

```typescript
// ✅ CORRECT - Backend returns parsed objects
async completeDeepDive(sessionId: string, finalAnswer?: string) {
  const response = await fetch(`${API_URL}/deep-dive/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      final_answer: finalAnswer,
      fallback_model: 'deepseek/deepseek-chat'  // Add fallback
    })
  });

  const data = await response.json();
  
  // ✅ Use analysis directly - it's already an object!
  console.log('Analysis confidence:', data.analysis.confidence); // Number
  console.log('Primary condition:', data.analysis.primaryCondition); // String
  
  return data;
}
```

### 3. Update Your Results Display

In `QuickScanResults.tsx` or similar components:

```typescript
// ✅ CORRECT - Direct access to properties
const QuickScanResults = ({ scanData }) => {
  const { analysis } = scanData;
  
  return (
    <div>
      <h2>{analysis.primaryCondition}</h2>
      <p>Confidence: {analysis.confidence}%</p>
      
      {/* Differentials are already objects */}
      {analysis.differentials.map((diff) => (
        <div key={diff.condition}>
          {diff.condition}: {diff.probability}%
        </div>
      ))}
    </div>
  );
};
```

### 4. Type Definitions (if using TypeScript)

Make sure your types match the actual response:

```typescript
interface DeepDiveAnalysis {
  confidence: number;  // NOT string!
  primaryCondition: string;
  likelihood: 'Very likely' | 'Likely' | 'Possible';
  symptoms: string[];
  recommendations: string[];
  urgency: 'low' | 'medium' | 'high';
  differentials: Array<{
    condition: string;
    probability: number;  // NOT string!
  }>;
  redFlags: string[];
  selfCare: string[];
  timeline: string;
  followUp: string;
  relatedSymptoms: string[];
  reasoning_snippets: string[];
}

interface DeepDiveCompleteResponse {
  deep_dive_id: string;
  analysis: DeepDiveAnalysis;  // NOT string!
  body_part: string;
  confidence: number;
  questions_asked: number;
  reasoning_snippets: string[];
  usage: object;
  status: 'success' | 'error';
}
```

### 5. Console Log Checks

Add these debug logs to verify you're getting objects:

```javascript
// In your Deep Dive complete handler
console.log('Deep Dive Complete Raw Response:', data);
console.log('Analysis type:', typeof data.analysis); // Should be "object"
console.log('Confidence type:', typeof data.analysis.confidence); // Should be "number"
```

### 6. Error Handling Update

```javascript
// Handle both old string responses (if any cached) and new object responses
const processAnalysis = (response) => {
  let analysis = response.analysis;
  
  // Safety check for old cached responses (remove after deploy)
  if (typeof analysis === 'string') {
    console.warn('Got string analysis - this should not happen with new backend');
    try {
      analysis = JSON.parse(analysis);
    } catch (e) {
      console.error('Failed to parse string analysis:', e);
    }
  }
  
  return analysis;
};
```

### 7. Quick Test After Deploy

```javascript
// Add this temporary test to verify
const testDeepDive = async () => {
  const response = await fetch('/api/deep-dive/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: 'your-test-session-id',
      fallback_model: 'deepseek/deepseek-chat'
    })
  });
  
  const data = await response.json();
  
  console.log('=== DEEP DIVE RESPONSE TEST ===');
  console.log('Full response:', data);
  console.log('Analysis is object?', typeof data.analysis === 'object');
  console.log('Confidence is number?', typeof data.analysis.confidence === 'number');
  console.log('Primary condition:', data.analysis.primaryCondition);
  console.log('Should see real medical terms, not generic "Analysis of X pain"');
};
```

## Summary of Changes:

1. **Remove all JSON.parse() on analysis fields**
2. **Add fallback_model: 'deepseek/deepseek-chat' to requests**
3. **Update TypeScript types to expect objects, not strings**
4. **Add console logs to verify object responses**
5. **Check that primaryCondition shows real conditions like "Rotator Cuff Tendinitis" not "Analysis of X pain"**

## Deploy Order:
1. Deploy backend first
2. Test with curl to verify
3. Update frontend code
4. Deploy frontend
5. Monitor console for any parsing errors