# Next.js Deep Dive Integration Guide

Deep Dive provides an interactive Q&A analysis that asks 2-3 diagnostic questions before delivering a comprehensive health assessment. The Deep Dive API is available on the same `run_oracle.py` server at port 8000.

## Overview

Deep Dive flow:
1. User submits initial symptoms (same form as Quick Scan)
2. AI asks 1st diagnostic question
3. User answers
4. AI decides if 2nd question is needed (based on internal criteria)
5. User answers if asked
6. AI may ask 3rd question (rare, only if critical info missing)
7. Final comprehensive analysis delivered in same format as Quick Scan

## API Endpoints

### 1. Start Deep Dive
**URL**: `POST http://localhost:8000/api/deep-dive/start`

**Request**:
```typescript
interface DeepDiveStartRequest {
  body_part: string;
  form_data: QuickScanFormData;  // Same as Quick Scan
  user_id?: string;  // Optional for anonymous
  model?: string;    // Optional - defaults to "deepseek/deepseek-r1-0528:free"
}
```

**Response**:
```typescript
interface DeepDiveStartResponse {
  session_id: string;
  question: string;
  question_number: 1;
  estimated_questions: "2-3";
  question_type: "differential" | "safety" | "severity" | "timeline";
  status: "success" | "error";
}
```

### 2. Continue Deep Dive
**URL**: `POST http://localhost:8000/api/deep-dive/continue`

**Request**:
```typescript
interface DeepDiveContinueRequest {
  session_id: string;
  answer: string;
  question_number: number;
}
```

**Response** (if more questions):
```typescript
interface DeepDiveContinueResponse {
  question: string;
  question_number: number;
  is_final_question: boolean;
  confidence_projection?: string;
  status: "success" | "error";
}
```

**Response** (if ready for analysis):
```typescript
interface DeepDiveReadyResponse {
  ready_for_analysis: true;
  questions_completed: number;
  status: "success";
}
```

### 3. Complete Deep Dive
**URL**: `POST http://localhost:8000/api/deep-dive/complete`

**Request**:
```typescript
interface DeepDiveCompleteRequest {
  session_id: string;
  final_answer?: string;  // Only if there was a final question
}
```

**Response**:
```typescript
interface DeepDiveCompleteResponse {
  deep_dive_id: string;
  analysis: AnalysisResult;  // Same format as Quick Scan!
  body_part: string;
  confidence: number;
  questions_asked: number;
  reasoning_snippets: string[];  // Transparency into AI's reasoning
  usage: TokenUsage;
  status: "success" | "error";
}
```

## Implementation Guide

### 1. Deep Dive Service

```typescript
// services/deepDiveService.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_ORACLE_API_URL || 'http://localhost:8000';

export const deepDiveService = {
  async startDeepDive(
    bodyPart: string,
    formData: QuickScanFormData,
    userId?: string,
    model?: string
  ) {
    const response = await fetch(`${API_BASE_URL}/api/deep-dive/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        body_part: bodyPart,
        form_data: formData,
        user_id: userId,
        model: model || 'deepseek/deepseek-r1-0528:free'
      }),
    });

    if (!response.ok) throw new Error('Failed to start deep dive');
    return response.json();
  },

  async continueDeepDive(
    sessionId: string,
    answer: string,
    questionNumber: number
  ) {
    const response = await fetch(`${API_BASE_URL}/api/deep-dive/continue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        answer: answer,
        question_number: questionNumber,
      }),
    });

    if (!response.ok) throw new Error('Failed to continue deep dive');
    return response.json();
  },

  async completeDeepDive(sessionId: string, finalAnswer?: string) {
    const response = await fetch(`${API_BASE_URL}/api/deep-dive/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        final_answer: finalAnswer,
      }),
    });

    if (!response.ok) throw new Error('Failed to complete deep dive');
    return response.json();
  },
};
```

### 2. Deep Dive Hook

```typescript
// hooks/useDeepDive.ts
import { useState, useCallback } from 'react';
import { deepDiveService } from '@/services/deepDiveService';
import { useAuth } from '@/hooks/useAuth';

interface DeepDiveState {
  sessionId: string | null;
  currentQuestion: string | null;
  questionNumber: number;
  answers: Array<{ question: string; answer: string }>;
  isComplete: boolean;
  finalAnalysis: any | null;
}

export const useDeepDive = () => {
  const { user } = useAuth();
  const [state, setState] = useState<DeepDiveState>({
    sessionId: null,
    currentQuestion: null,
    questionNumber: 0,
    answers: [],
    isComplete: false,
    finalAnalysis: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startDeepDive = useCallback(async (
    bodyPart: string,
    formData: QuickScanFormData
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await deepDiveService.startDeepDive(
        bodyPart,
        formData,
        user?.id
      );

      setState({
        sessionId: result.session_id,
        currentQuestion: result.question,
        questionNumber: result.question_number,
        answers: [],
        isComplete: false,
        finalAnalysis: null,
      });

      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start deep dive');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  const answerQuestion = useCallback(async (answer: string) => {
    if (!state.sessionId) throw new Error('No active session');

    setIsLoading(true);
    setError(null);

    try {
      // Save current Q&A
      const newAnswers = [...state.answers, {
        question: state.currentQuestion!,
        answer: answer,
      }];

      const result = await deepDiveService.continueDeepDive(
        state.sessionId,
        answer,
        state.questionNumber
      );

      if (result.ready_for_analysis) {
        // Ready to complete
        const finalResult = await deepDiveService.completeDeepDive(
          state.sessionId,
          undefined // No final answer needed
        );

        setState(prev => ({
          ...prev,
          answers: newAnswers,
          isComplete: true,
          finalAnalysis: finalResult,
        }));

        return finalResult;
      } else {
        // More questions
        setState(prev => ({
          ...prev,
          currentQuestion: result.question,
          questionNumber: result.question_number,
          answers: newAnswers,
        }));

        return result;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process answer');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [state.sessionId, state.currentQuestion, state.questionNumber, state.answers]);

  const reset = useCallback(() => {
    setState({
      sessionId: null,
      currentQuestion: null,
      questionNumber: 0,
      answers: [],
      isComplete: false,
      finalAnalysis: null,
    });
    setError(null);
  }, []);

  return {
    ...state,
    isLoading,
    error,
    startDeepDive,
    answerQuestion,
    reset,
  };
};
```

### 3. Deep Dive UI Component

```tsx
// components/DeepDiveInterface.tsx
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDeepDive } from '@/hooks/useDeepDive';
import { Brain, MessageCircle, ChevronRight } from 'lucide-react';

interface DeepDiveInterfaceProps {
  bodyPart: string;
  formData: QuickScanFormData;
  onComplete: (analysis: any) => void;
  onCancel: () => void;
}

export const DeepDiveInterface: React.FC<DeepDiveInterfaceProps> = ({
  bodyPart,
  formData,
  onComplete,
  onCancel,
}) => {
  const {
    currentQuestion,
    questionNumber,
    answers,
    isComplete,
    finalAnalysis,
    isLoading,
    error,
    startDeepDive,
    answerQuestion,
  } = useDeepDive();

  const [currentAnswer, setCurrentAnswer] = useState('');

  useEffect(() => {
    // Start deep dive on mount
    startDeepDive(bodyPart, formData);
  }, []);

  useEffect(() => {
    if (isComplete && finalAnalysis) {
      onComplete(finalAnalysis);
    }
  }, [isComplete, finalAnalysis]);

  const handleSubmitAnswer = async () => {
    if (!currentAnswer.trim()) return;
    
    try {
      await answerQuestion(currentAnswer);
      setCurrentAnswer(''); // Clear for next question
    } catch (err) {
      // Error handled by hook
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Brain className="w-8 h-8 text-purple-400" />
          <h2 className="text-2xl font-bold text-white">Deep Dive Analysis</h2>
        </div>
        <p className="text-gray-400">
          I'll ask you a few specific questions to better understand your symptoms
        </p>
      </div>

      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">
            Question {questionNumber} of 2-3
          </span>
          <span className="text-sm text-gray-400">
            {answers.length} answered
          </span>
        </div>
        <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
            initial={{ width: 0 }}
            animate={{ width: `${(questionNumber / 3) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Q&A History */}
      {answers.length > 0 && (
        <div className="mb-8 space-y-4">
          {answers.map((qa, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-900/50 rounded-xl p-4 border border-white/10"
            >
              <div className="flex items-start gap-3 mb-2">
                <Brain className="w-5 h-5 text-purple-400 mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-gray-400">Question {index + 1}</p>
                  <p className="text-white">{qa.question}</p>
                </div>
              </div>
              <div className="flex items-start gap-3 ml-8">
                <MessageCircle className="w-5 h-5 text-blue-400 mt-1" />
                <div className="flex-1">
                  <p className="text-sm text-gray-400">Your answer</p>
                  <p className="text-white">{qa.answer}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Current Question */}
      {currentQuestion && !isComplete && (
        <AnimatePresence mode="wait">
          <motion.div
            key={questionNumber}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="mb-8"
          >
            <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 
              rounded-2xl p-6 border border-purple-500/30"
            >
              <div className="flex items-start gap-3 mb-4">
                <Brain className="w-6 h-6 text-purple-400 mt-1" />
                <div className="flex-1">
                  <p className="text-lg font-medium text-white mb-1">
                    {currentQuestion}
                  </p>
                  <p className="text-sm text-gray-400">
                    Please be as specific as possible
                  </p>
                </div>
              </div>

              <textarea
                value={currentAnswer}
                onChange={(e) => setCurrentAnswer(e.target.value)}
                placeholder="Type your answer here..."
                className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white 
                  border border-gray-700 focus:border-purple-500 focus:ring-2 
                  focus:ring-purple-500/20 focus:outline-none resize-none 
                  transition-all placeholder-gray-500"
                rows={4}
                disabled={isLoading}
              />

              <div className="flex items-center justify-between mt-4">
                <button
                  onClick={onCancel}
                  className="px-4 py-2 text-gray-400 hover:text-gray-300 
                    transition-colors"
                  disabled={isLoading}
                >
                  Cancel
                </button>

                <button
                  onClick={handleSubmitAnswer}
                  disabled={!currentAnswer.trim() || isLoading}
                  className="px-6 py-3 rounded-xl bg-purple-600 hover:bg-purple-700 
                    disabled:bg-gray-700 disabled:cursor-not-allowed text-white 
                    font-medium transition-all duration-200 flex items-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Spinner className="w-5 h-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Continue
                      <ChevronRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      )}

      {/* Loading state while processing final analysis */}
      {isLoading && answers.length > 0 && !currentQuestion && (
        <div className="text-center py-12">
          <Brain className="w-12 h-12 text-purple-400 mx-auto mb-4 animate-pulse" />
          <p className="text-lg text-white mb-2">Analyzing your responses...</p>
          <p className="text-gray-400">Generating comprehensive analysis</p>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/50 
          text-red-300 mb-4"
        >
          {error}
        </div>
      )}
    </div>
  );
};
```

### 4. Integration with Quick Scan Results

Update your Quick Scan results to offer Deep Dive:

```tsx
// In QuickScanResults component
const handleDeepDive = () => {
  // Navigate to deep dive with same form data
  sessionStorage.setItem('deepDiveContext', JSON.stringify({
    bodyPart: body_part,
    formData: originalFormData, // You'll need to pass this from Quick Scan
    quickScanResult: analysis,
  }));
  
  router.push('/deep-dive');
};

// Add Deep Dive button alongside Oracle button
<button
  onClick={handleDeepDive}
  className="px-6 py-4 rounded-xl bg-gradient-to-r from-purple-600 
    to-pink-600 hover:from-purple-700 hover:to-pink-700 
    transition-all flex items-center justify-center gap-3 group"
>
  <Brain className="w-5 h-5 text-white" />
  <div className="text-left">
    <div className="font-medium text-white">Get Deep Dive Analysis</div>
    <div className="text-xs text-purple-200">
      Interactive Q&A for precise diagnosis
    </div>
  </div>
</button>
```

### 5. Deep Dive Page

```tsx
// pages/deep-dive.tsx
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { DeepDiveInterface } from '@/components/DeepDiveInterface';
import { QuickScanResults } from '@/components/QuickScanResults';

export default function DeepDivePage() {
  const router = useRouter();
  const [context, setContext] = useState(null);
  const [finalResult, setFinalResult] = useState(null);

  useEffect(() => {
    // Get context from session storage
    const contextStr = sessionStorage.getItem('deepDiveContext');
    if (contextStr) {
      setContext(JSON.parse(contextStr));
      sessionStorage.removeItem('deepDiveContext');
    } else {
      // No context, redirect to home
      router.push('/');
    }
  }, []);

  const handleComplete = (result: any) => {
    // Deep Dive returns same format as Quick Scan
    setFinalResult(result);
  };

  const handleCancel = () => {
    router.push('/');
  };

  if (!context) {
    return <div>Loading...</div>;
  }

  if (finalResult) {
    // Show results using same component as Quick Scan
    return (
      <QuickScanResults
        result={{
          scan_id: finalResult.deep_dive_id,
          analysis: finalResult.analysis,
          body_part: finalResult.body_part,
          confidence: finalResult.confidence,
          user_id: finalResult.user_id,
        }}
        onReset={() => router.push('/')}
        isDeepDive={true}
        questionsAsked={finalResult.questions_asked}
        reasoningSnippets={finalResult.reasoning_snippets}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white py-12">
      <div className="container mx-auto px-4">
        <DeepDiveInterface
          bodyPart={context.bodyPart}
          formData={context.formData}
          onComplete={handleComplete}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
}
```

## Model Selection

To use a different model, pass it in the URL or request:

```typescript
// Use different model
const result = await deepDiveService.startDeepDive(
  bodyPart,
  formData,
  userId,
  'gpt-4' // or any model available on OpenRouter
);

// From URL params
const model = searchParams.get('model') || 'deepseek/deepseek-r1-0528:free';
```

## Key Features

1. **Smart Question Decision**: The AI internally decides if a 3rd question is needed based on:
   - Confidence spread between conditions
   - Safety concerns
   - Severity + uncertainty
   - Missing demographic info

2. **Session Management**: Sessions are stored in `deep_dive_sessions` table with full Q&A history

3. **Same Output Format**: Final analysis uses exact same format as Quick Scan for UI consistency

4. **Auto-Summary**: Summaries are automatically saved to `llm_context` table for future reference

5. **Anonymous Support**: Works for both authenticated and anonymous users

## Testing Checklist

- [ ] Deep Dive starts successfully from Quick Scan results
- [ ] Questions are clear and relevant
- [ ] Answer submission works smoothly
- [ ] 2nd question appears when needed
- [ ] 3rd question only appears in edge cases
- [ ] Final analysis matches Quick Scan format
- [ ] Confidence is higher than Quick Scan
- [ ] Reasoning snippets provide transparency
- [ ] Session abandonment handled gracefully
- [ ] Summary saved to llm_context table
- [ ] Works for anonymous users
- [ ] Model selection works correctly

## Error Handling

The Deep Dive gracefully handles:
- Session timeouts (sessions don't expire but could add this)
- Abandoned sessions (marked as 'abandoned' status)
- Parse errors (returns error status)
- Network issues (standard error handling)

This implementation provides a seamless Q&A experience that feels like a chat but maintains the structured analysis format users expect.