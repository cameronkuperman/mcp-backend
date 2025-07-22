# Frontend Implementation Guide: Ask Me More Feature 🚀

## Overview
The Ask Me More feature allows users to request additional diagnostic questions after the initial Deep Dive analysis to increase confidence in the diagnosis. This guide provides complete implementation details for frontend developers.

## Key Concepts

### 1. Session States
- **`active`**: Still asking initial questions (1-6)
- **`analysis_ready`**: Initial analysis complete, Ask Me More available
- **`completed`**: Final state after all interactions

### 2. Question Limits
- Initial Deep Dive: 6 questions
- Ask Me More: Up to 5 additional questions
- Total maximum: 11 questions

### 3. Confidence Tracking
- Each session has a `final_confidence` value (0-100)
- Users can set a `target_confidence` (default: 95)
- The system generates questions to bridge the gap

## API Endpoints

### Deep Dive Ask Me More
```
POST /api/deep-dive/ask-more
```

### Request Format
```javascript
{
  "session_id": "uuid-here",           // Required
  "current_confidence": 75,            // Optional (falls back to session)
  "target_confidence": 95,             // Optional (default: 95)
  "max_questions": 5                   // Optional (default: 5)
}
```

### Response Format
```javascript
{
  "status": "success",
  "question": "Have you experienced any neurological symptoms?",
  "question_number": 7,
  "question_category": "red_flags",
  "current_confidence": 75,
  "target_confidence": 95,
  "confidence_gap": 20,
  "estimated_questions_remaining": 2,
  "max_questions_remaining": 5,
  "reasoning": "This helps identify potential red flags...",
  "expected_confidence_gain": 15
}
```

### Error Response
```javascript
{
  "status": "error",
  "error": "Error message here",
  "details": {
    // Debug information
  }
}
```

## Complete Implementation Example

### 1. Basic Ask Me More Button Component
```javascript
import React, { useState } from 'react';

const AskMeMoreButton = ({ sessionId, currentConfidence, onNewQuestion }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAskMore = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/deep-dive/ask-more', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          current_confidence: currentConfidence,
          target_confidence: 95
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        onNewQuestion(data);
      } else {
        setError(data.error || 'Failed to generate question');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button 
        onClick={handleAskMore}
        disabled={loading}
        className="ask-more-button"
      >
        {loading ? 'Generating Question...' : 'Ask Me More'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
};
```

### 2. Full Deep Dive Flow with Ask Me More
```javascript
import React, { useState, useEffect } from 'react';

const DeepDiveAnalysis = ({ sessionId }) => {
  const [session, setSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [showAskMore, setShowAskMore] = useState(false);
  const [questionsAsked, setQuestionsAsked] = useState(0);
  const [confidence, setConfidence] = useState(0);

  // Load session data
  useEffect(() => {
    loadSession();
  }, [sessionId]);

  const loadSession = async () => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`);
      const data = await response.json();
      
      setSession(data);
      setConfidence(data.final_confidence || 0);
      setQuestionsAsked(data.questions?.length || 0);
      
      // Show Ask Me More if analysis is ready and under 11 questions
      if (data.status === 'analysis_ready' && questionsAsked < 11) {
        setShowAskMore(true);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const handleAskMore = async () => {
    try {
      const response = await fetch('/api/deep-dive/ask-more', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          current_confidence: confidence,
          target_confidence: 95
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        setCurrentQuestion(data);
        setShowAskMore(false);
        setQuestionsAsked(data.question_number);
      }
    } catch (error) {
      console.error('Ask Me More failed:', error);
    }
  };

  const handleAnswerQuestion = async (answer) => {
    try {
      const response = await fetch('/api/deep-dive/continue', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          answer: answer,
          question_number: currentQuestion.question_number
        })
      });

      const data = await response.json();
      
      // Update confidence
      if (data.final_confidence) {
        setConfidence(data.final_confidence);
      }
      
      // Check if we should show Ask Me More again
      if (data.status === 'analysis_ready' && questionsAsked < 10) {
        setShowAskMore(true);
        setCurrentQuestion(null);
      }
    } catch (error) {
      console.error('Failed to submit answer:', error);
    }
  };

  return (
    <div className="deep-dive-container">
      {/* Current Analysis Display */}
      {session && (
        <div className="analysis-summary">
          <h2>Current Analysis</h2>
          <div className="confidence-meter">
            <label>Diagnostic Confidence: {confidence}%</label>
            <progress value={confidence} max="100" />
          </div>
          
          {/* Show primary diagnosis if available */}
          {session.final_analysis && (
            <div className="diagnosis">
              <h3>Primary Diagnosis</h3>
              <p>{session.final_analysis.primary_condition}</p>
            </div>
          )}
        </div>
      )}

      {/* Current Question */}
      {currentQuestion && (
        <div className="question-container">
          <h3>Additional Question {currentQuestion.question_number}</h3>
          <p>{currentQuestion.question}</p>
          
          <div className="question-meta">
            <small>Category: {currentQuestion.question_category}</small>
            <small>Expected confidence gain: +{currentQuestion.expected_confidence_gain}%</small>
          </div>
          
          <QuestionAnswerForm 
            onSubmit={handleAnswerQuestion}
            questionNumber={currentQuestion.question_number}
          />
        </div>
      )}

      {/* Ask Me More Button */}
      {showAskMore && !currentQuestion && (
        <div className="ask-more-section">
          <p>Current confidence: {confidence}%</p>
          <p>Would you like to answer more questions to increase diagnostic confidence?</p>
          
          <button 
            onClick={handleAskMore}
            className="ask-more-button primary"
          >
            Ask Me More Questions
          </button>
          
          <button 
            onClick={() => completeAnalysis()}
            className="complete-button secondary"
          >
            I'm Satisfied with Current Analysis
          </button>
          
          <small>
            You can answer up to {11 - questionsAsked} more questions
          </small>
        </div>
      )}

      {/* Reached Question Limit */}
      {questionsAsked >= 11 && (
        <div className="limit-reached">
          <p>You've reached the maximum number of questions.</p>
          <button onClick={() => completeAnalysis()}>
            Complete Analysis
          </button>
        </div>
      )}
    </div>
  );
};
```

### 3. Advanced Implementation with Target Confidence
```javascript
const AskMeMoreAdvanced = ({ sessionId, currentConfidence }) => {
  const [targetConfidence, setTargetConfidence] = useState(95);
  const [showSettings, setShowSettings] = useState(false);
  
  const handleAskMore = async () => {
    const response = await fetch('/api/deep-dive/ask-more', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        current_confidence: currentConfidence,
        target_confidence: targetConfidence
      })
    });

    const data = await response.json();
    // Handle response...
  };

  return (
    <div className="ask-more-advanced">
      <div className="confidence-info">
        <div>Current Confidence: {currentConfidence}%</div>
        <div>Target Confidence: {targetConfidence}%</div>
        <div>Gap: {targetConfidence - currentConfidence}%</div>
      </div>
      
      <button onClick={() => setShowSettings(!showSettings)}>
        Adjust Target Confidence
      </button>
      
      {showSettings && (
        <div className="confidence-settings">
          <label>
            Target Confidence Level:
            <input
              type="range"
              min={currentConfidence + 5}
              max="100"
              value={targetConfidence}
              onChange={(e) => setTargetConfidence(Number(e.target.value))}
            />
            <span>{targetConfidence}%</span>
          </label>
        </div>
      )}
      
      <button onClick={handleAskMore} className="primary">
        Generate Questions to Reach {targetConfidence}% Confidence
      </button>
    </div>
  );
};
```

## Important Implementation Notes

### 1. DO NOT Parse JSON Responses
```javascript
// ❌ WRONG - Backend already returns objects
const data = await response.json();
const analysis = JSON.parse(data.analysis);

// ✅ CORRECT
const data = await response.json();
const analysis = data.analysis; // Already an object
```

### 2. Handle Missing Confidence
```javascript
// The backend will use session's final_confidence if not provided
// But it's better to always send it explicitly

const askMore = async (sessionId, confidence = null) => {
  const body = {
    session_id: sessionId,
    target_confidence: 95
  };
  
  // Only add current_confidence if we have it
  if (confidence !== null && confidence !== undefined) {
    body.current_confidence = confidence;
  }
  
  const response = await fetch('/api/deep-dive/ask-more', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  return response.json();
};
```

### 3. Track Question Count
```javascript
const QuestionTracker = ({ session }) => {
  const initialQuestions = session.initial_questions_count || 6;
  const additionalQuestions = session.additional_questions_count || 0;
  const totalQuestions = initialQuestions + additionalQuestions;
  const maxQuestions = 11;
  const remainingQuestions = maxQuestions - totalQuestions;
  
  return (
    <div className="question-tracker">
      <p>Questions answered: {totalQuestions}/{maxQuestions}</p>
      {remainingQuestions > 0 && (
        <p>You can ask {remainingQuestions} more questions</p>
      )}
    </div>
  );
};
```

### 4. Error Handling Best Practices
```javascript
const robustAskMore = async (sessionId, currentConfidence) => {
  try {
    const response = await fetch('/api/deep-dive/ask-more', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        current_confidence: currentConfidence,
        target_confidence: 95
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.status === 'error') {
      // Handle specific errors
      if (data.error.includes('reached maximum')) {
        return { error: 'question_limit', message: 'Maximum questions reached' };
      }
      if (data.error.includes('not found')) {
        return { error: 'session_not_found', message: 'Session expired or not found' };
      }
      return { error: 'general', message: data.error };
    }
    
    return { success: true, data };
  } catch (error) {
    console.error('Ask Me More error:', error);
    return { error: 'network', message: 'Network error occurred' };
  }
};
```

## Testing Your Implementation

### 1. Test Basic Flow
```javascript
// In browser console
const testAskMore = async () => {
  const response = await fetch('/api/deep-dive/ask-more', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: 'your-session-id-here',
      current_confidence: 75,
      target_confidence: 95
    })
  });
  console.log(await response.json());
};

testAskMore();
```

### 2. Test Edge Cases
```javascript
// Test without current_confidence
fetch('/api/deep-dive/ask-more', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'your-session-id',
    target_confidence: 90
  })
}).then(r => r.json()).then(console.log);

// Test with alternate field names (backwards compatibility)
fetch('/api/deep-dive/ask-more', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'your-session-id',
    confidence: 80,  // alternate name
    target: 90       // alternate name
  })
}).then(r => r.json()).then(console.log);
```

## UI/UX Best Practices

### 1. Show Progress Clearly
- Display current confidence with visual progress bar
- Show confidence gap to target
- Indicate questions remaining

### 2. Provide Context
- Explain why more questions might help
- Show expected confidence gain
- Display question category/purpose

### 3. User Control
- Let users set their target confidence
- Allow skipping Ask Me More
- Provide "Complete Analysis" option

### 4. Loading States
- Show loading indicator during API calls
- Disable buttons during requests
- Provide feedback on success/failure

## Common Pitfalls to Avoid

1. **Don't look for "ask-more-ultra-think" endpoint** - it doesn't exist
2. **Don't auto-complete after Ask Me More** - let users control when done
3. **Don't assume confidence exists** - always check and provide fallback
4. **Don't parse already-parsed JSON** - responses are objects
5. **Don't ignore question limits** - max 11 total questions

## Summary Checklist

- [ ] Implement Ask Me More button that appears when session is `analysis_ready`
- [ ] Always send `current_confidence` in requests
- [ ] Handle responses as objects (no JSON.parse needed)
- [ ] Track question count and enforce limits
- [ ] Provide clear UI feedback and progress indicators
- [ ] Handle errors gracefully with user-friendly messages
- [ ] Allow users to complete analysis at any time
- [ ] Test with various confidence levels and edge cases

That's it! Your Ask Me More feature should now work perfectly. 🎉