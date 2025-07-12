# Quick Scan Integration Guide

## API Implementation Complete

### 1. Quick Scan Endpoint
- **URL**: `POST /quick-scan`
- **Request Body**:
```json
{
  "body_part": "head",
  "form_data": {
    "symptoms": "headache",
    "painType": ["throbbing", "sharp"],
    "painLevel": 7,
    "duration": "days",
    "dailyImpact": ["work", "sleep"],
    "worseWhen": "moving",
    "betterWhen": "resting",
    "sleepImpact": "waking",
    "frequency": "sometimes",
    "whatTried": "ibuprofen",
    "didItHelp": "temporarily",
    "associatedSymptoms": "nausea"
  },
  "user_id": "optional-for-anonymous",
  "model": "optional-defaults-to-deepseek"
}
```

- **Response**:
```json
{
  "scan_id": "uuid",
  "analysis": {
    "confidence": 82,
    "primaryCondition": "Tension Headache",
    "likelihood": "Very likely",
    "symptoms": ["headache", "nausea"],
    "recommendations": ["rest", "hydration", "etc"],
    "urgency": "low",
    "differentials": [
      {"condition": "Migraine", "probability": 35}
    ],
    "redFlags": ["sudden severe headache"],
    "selfCare": ["regular sleep", "stress management"],
    "timeline": "2-3 days with treatment",
    "followUp": "See doctor if no improvement in 3 days",
    "relatedSymptoms": ["vision changes", "fever"]
  },
  "body_part": "head",
  "confidence": 82,
  "user_id": "user-id-or-null",
  "usage": {},
  "model": "deepseek/deepseek-chat"
}
```

### 2. Oracle Integration

When user clicks "Ask Oracle" from Quick Scan results, pass this context:

```javascript
const oracleContext = {
  source: 'quick_scan',
  scanId: quickScanId,
  bodyPart: selectedBodyPart,
  formData: formData,
  analysis: analysisResult,
  prompt: analysisResult.confidence < 70
    ? `I just did a Quick Scan for ${selectedBodyPart} symptoms but the confidence was low (${analysisResult.confidence}%). Can you help me understand my symptoms better?`
    : `I was diagnosed with ${analysisResult.primaryCondition} from Quick Scan. Can you provide more detailed insights?`,
  metadata: {
    confidence: analysisResult.confidence,
    urgency: analysisResult.urgency,
    primaryCondition: analysisResult.primaryCondition
  }
};

// Send to existing Oracle endpoint
const oracleResponse = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: oracleContext.prompt,
    user_id: userId,
    conversation_id: newConversationId,
    category: 'health-scan',
    // The Oracle will receive the quick scan context through the query
  })
});
```

### 3. Summary Generation

To generate a summary for a Quick Scan:

```javascript
const summaryResponse = await fetch('/api/generate_summary', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    quick_scan_id: scanId,
    user_id: userId
  })
});
```

### 4. Supabase Setup

Run these migrations in order:

1. **Create Tables**: Run `supabase_migrations/quick_scan_tables.sql`
2. **Helper Functions**: Run `supabase_migrations/quick_scan_queries.sql`

### 5. Key Features Implemented

- ✅ Anonymous user support (user_id is optional)
- ✅ Automatic symptom tracking for authenticated users
- ✅ Low confidence detection and Oracle escalation prompt
- ✅ JSON response validation with retry on malformed output
- ✅ Summary generation that avoids hallucination
- ✅ RLS policies for data security

### 6. Error Handling

The API includes proper error handling:
- Malformed JSON from LLM triggers retry logic
- Database errors are logged but don't break the flow for anonymous users
- Clear error messages returned to client

### 7. Next Steps for Client

1. Update the QuickScanDemo component to call the new `/quick-scan` endpoint
2. Handle the response and populate the UI
3. Implement the Oracle escalation flow
4. Add symptom tracking visualization using the `symptom_tracking` table
5. Implement the "Generate Report" functionality