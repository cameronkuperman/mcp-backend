# Manual Test Commands for Ask Me More

## First, get a valid session ID from your frontend console

Look for a session ID in your browser console from a recent Deep Dive session.

## Test Commands:

### 1. Test with Frontend Field Names
```bash
# Replace YOUR_SESSION_ID with an actual session ID
curl -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "current_confidence": 70,
    "target_confidence": 90
  }'
```

### 2. Test with Alternate Names
```bash
curl -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "confidence": 70,
    "target": 90
  }'
```

### 3. Test with Both (like frontend does)
```bash
curl -X POST http://localhost:8000/api/deep-dive/ask-more \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "current_confidence": 70,
    "target_confidence": 90,
    "confidence": 70,
    "target": 90
  }'
```

## What You Should See:

Instead of an AttributeError, you should get:

```json
{
  "status": "success",
  "question": "Have you noticed any specific triggers...",
  "question_number": 7,
  "current_confidence": 70,
  "target_confidence": 90,
  "confidence_gap": 20,
  "estimated_questions_remaining": 2,
  "max_questions_remaining": 4
}
```

## From Your Browser Console:

You can also test directly:

```javascript
// Get a session ID from a recent Deep Dive
const sessionId = 'd8209e32-8e54-4a7d-abe1-284b3c258613'; // Use your actual ID

// Test the endpoint
fetch('/api/deep-dive/ask-more', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    current_confidence: 70,
    target_confidence: 90,
    confidence: 70,
    target: 90
  })
})
.then(r => r.json())
.then(data => {
  console.log('Ask Me More Response:', data);
  console.log('Got question?', !!data.question);
  console.log('Error?', data.error);
});
```