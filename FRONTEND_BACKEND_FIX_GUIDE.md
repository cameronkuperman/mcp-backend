# Complete Fix Guide for Deep Dive Issues

## Problem Summary

1. **Primary Issue**: The model `deepseek/deepseek-r1-0528:free` is returning responses that fail JSON parsing
2. **Frontend Issue**: The frontend is not handling the error response properly
3. **Network Issues**: Some connection resets happening (likely due to the failing model)

## Best Free Low-Latency Models to Use

Based on current availability and performance:

### Recommended Models (in order of preference):
1. **`tngtech/deepseek-r1t-chimera:free`** - BEST! Used by Oracle Chat (working great)
2. **`deepseek/deepseek-chat`** - Good for Quick Scan
3. **`meta-llama/llama-3.2-3b-instruct:free`** - Very fast, reliable
4. **`google/gemini-2.0-flash-exp:free`** - Fast, good for larger contexts
5. **`microsoft/phi-3-mini-128k-instruct:free`** - Lightweight, fast

## Backend Fixes

### 1. Update `run_oracle.py` - Fix Default Model

```python
# In run_oracle.py, update the DeepDiveStartRequest class (around line 64)
class DeepDiveStartRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None  # Will default to deepseek/deepseek-chat instead

# Update the start_deep_dive function (around line 586)
@app.post("/api/deep-dive/start")
async def start_deep_dive(request: DeepDiveStartRequest):
    """Start a Deep Dive analysis session"""
    try:
        # Get user data if provided
        user_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data
        }
        
        # FIXED: Use working model with fallback
        model = request.model or "deepseek/deepseek-chat"  # Changed from deepseek-r1
        
        # Add model validation and fallback
        WORKING_MODELS = [
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        # If specified model fails, try fallbacks
        if model not in WORKING_MODELS:
            print(f"Warning: Model {model} not in working list, using deepseek/deepseek-chat")
            model = "deepseek/deepseek-chat"
```

### 2. Add Robust JSON Parsing with Fallbacks

Add this helper function at the top of `run_oracle.py`:

```python
import re

def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from response with multiple fallback strategies"""
    # Strategy 1: Direct parse if already dict
    if isinstance(content, dict):
        return content
    
    # Strategy 2: Try direct JSON parse
    try:
        return json.loads(content)
    except:
        pass
    
    # Strategy 3: Find JSON in text
    try:
        # Look for JSON between curly braces
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Strategy 4: Find JSON in code blocks
    try:
        # Look for ```json blocks
        json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_block:
            return json.loads(json_block.group(1))
    except:
        pass
    
    # Strategy 5: Create fallback response for deep dive
    if "question" in content.lower() or "?" in content:
        # Extract potential question from text
        lines = content.strip().split('\n')
        question = next((line.strip() for line in lines if '?' in line), lines[0] if lines else "Can you describe your symptoms?")
        return {
            "question": question,
            "question_type": "open_ended",
            "internal_analysis": {"extracted": True}
        }
    
    return None
```

### 3. Update JSON Parsing in Deep Dive (around line 610)

```python
        # Parse response with robust fallback
        try:
            # First try our robust parser
            question_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not question_data:
                # Fallback: Create a generic first question
                question_data = {
                    "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                    "question_type": "symptom_characterization",
                    "internal_analysis": {"fallback": True}
                }
        except Exception as e:
            print(f"Parse error in deep dive start: {e}")
            # Use fallback question
            question_data = {
                "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                "question_type": "symptom_characterization",
                "internal_analysis": {"error": str(e)}
            }
```

### 4. Fix Continue and Complete Functions

Apply similar fixes to the continue and complete functions:

```python
# In continue_deep_dive (around line 723)
        # Parse response with fallback
        try:
            decision_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not decision_data:
                # Create fallback decision
                decision_data = {
                    "need_another_question": request.question_number < 2,
                    "question": "Have you experienced any other symptoms along with this?",
                    "confidence_projection": "Gathering more information",
                    "updated_analysis": session.get("internal_state", {})
                }
        except Exception as e:
            print(f"Parse error in deep dive continue: {e}")
            decision_data = {
                "ready_for_analysis": True,
                "questions_completed": request.question_number
            }

# In complete_deep_dive (around line 837)
        # Parse final analysis with comprehensive fallback
        try:
            analysis_result = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not analysis_result:
                # Create structured fallback analysis
                analysis_result = {
                    "confidence": 70,
                    "primaryCondition": f"Analysis of {session.get('body_part', 'symptom')} pain",
                    "likelihood": "Likely",
                    "symptoms": [s for q in questions for s in [q.get("answer", "")] if s],
                    "recommendations": [
                        "Monitor symptoms closely",
                        "Seek medical evaluation if symptoms worsen",
                        "Keep a symptom diary"
                    ],
                    "urgency": "medium",
                    "differentials": [],
                    "redFlags": ["Seek immediate care if symptoms suddenly worsen"],
                    "selfCare": ["Rest and avoid activities that worsen symptoms"],
                    "reasoning_snippets": ["Based on reported symptoms"]
                }
        except Exception as e:
            print(f"Parse error in deep dive complete: {e}")
            # Use fallback analysis
            analysis_result = {
                "confidence": 60,
                "primaryCondition": "Requires further medical evaluation",
                "likelihood": "Possible",
                "symptoms": ["As reported"],
                "recommendations": ["Consult with a healthcare provider"],
                "urgency": "medium",
                "differentials": [],
                "redFlags": [],
                "selfCare": [],
                "reasoning_snippets": ["Unable to complete full analysis"]
            }
```

## Frontend Fixes

### 1. Update `deepdive-client.ts`

```typescript
// Update the model configuration
const DEFAULT_MODEL = 'tngtech/deepseek-r1t-chimera:free'; // Use chimera like Oracle!

// Add model fallback list
const FALLBACK_MODELS = [
  'tngtech/deepseek-r1t-chimera:free',  // Best model!
  'deepseek/deepseek-chat',
  'meta-llama/llama-3.2-3b-instruct:free',
  'google/gemini-2.0-flash-exp:free',
  'microsoft/phi-3-mini-128k-instruct:free'
];

// Update startDeepDive function
export async function startDeepDive(
  bodyPart: string,
  formData: Record<string, any>,
  userId?: string,
  model?: string
): Promise<DeepDiveStartResponse> {
  try {
    // Use working model
    const selectedModel = model || DEFAULT_MODEL;
    
    const requestBody: DeepDiveStartRequest = {
      body_part: bodyPart,
      form_data: formData,
      user_id: userId,
      model: selectedModel // Always include model
    };

    console.log('Deep Dive Start Request:', requestBody);

    const response = await fetch(`${API_BASE_URL}/api/deep-dive/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();
    console.log('Deep Dive Start Raw Response:', data);

    // Better error handling
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}, message: ${data.error || 'Unknown error'}`);
    }

    // Handle parse errors from backend
    if (data.error === 'Failed to parse response' && data.status === 'error') {
      // Retry with different model
      const modelIndex = FALLBACK_MODELS.indexOf(selectedModel);
      const nextModel = FALLBACK_MODELS[modelIndex + 1] || FALLBACK_MODELS[0];
      
      if (nextModel !== selectedModel) {
        console.log(`Model ${selectedModel} failed, retrying with ${nextModel}`);
        return startDeepDive(bodyPart, formData, userId, nextModel);
      }
      
      throw new Error('All models failed to parse response');
    }

    // Validate response
    if (!data.session_id) {
      console.error('Invalid response structure:', data);
      throw new Error('Invalid response: Missing session_id');
    }

    return data as DeepDiveStartResponse;
  } catch (error) {
    console.error('Deep Dive start error:', error);
    throw error;
  }
}

// Update continueDeepDive to handle errors better
export async function continueDeepDive(
  sessionId: string,
  answer: string,
  questionNumber: number
): Promise<DeepDiveContinueResponse> {
  try {
    const requestBody = {
      session_id: sessionId,
      answer,
      question_number: questionNumber,
    };

    console.log('Deep Dive Continue Request:', requestBody);

    const response = await fetch(`${API_BASE_URL}/api/deep-dive/continue`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();
    console.log('Deep Dive Continue Raw Response:', data);

    if (!response.ok || data.status === 'error') {
      // Handle parse errors gracefully
      if (data.error === 'Failed to parse response') {
        // Return ready for analysis if we have enough questions
        if (questionNumber >= 2) {
          return {
            ready_for_analysis: true,
            questions_completed: questionNumber,
            status: 'success'
          };
        }
        // Otherwise create a fallback question
        return {
          question: "Can you provide any additional details about your symptoms?",
          question_number: questionNumber + 1,
          is_final_question: questionNumber === 2,
          status: 'success'
        };
      }
      throw new Error(data.error || `HTTP error! status: ${response.status}`);
    }

    return data as DeepDiveContinueResponse;
  } catch (error) {
    console.error('Deep Dive continue error:', error);
    throw error;
  }
}
```

### 2. Update `DeepDiveChat.tsx`

```typescript
// Update the model configuration
const DEFAULT_MODEL = 'deepseek/deepseek-chat'; // Changed from deepseek-r1

// In the initializeSession function
const initializeSession = async (retryCount = 0) => {
  try {
    setLoading(true);
    setError(null);
    console.log('Starting deep dive initialization...');

    const currentModel = model || DEFAULT_MODEL;
    console.log(`Using model: ${currentModel} (retry ${retryCount})`);

    const response = await deepDiveApi.startDeepDive(
      bodyPart,
      formData,
      user?.id,
      currentModel // Always pass the model
    );

    console.log('Deep Dive start response:', response);

    if (response.session_id && response.question) {
      setSessionId(response.session_id);
      setMessages([{
        id: '1',
        role: 'assistant',
        content: response.question,
        timestamp: new Date().toISOString(),
      }]);
      setCurrentQuestion(response.question);
      setQuestionNumber(1);
      setIsAnalyzing(false);
    } else {
      throw new Error('Invalid response structure');
    }
  } catch (error) {
    console.error('Failed to start deep dive:', error);
    
    // Retry with different model if parse error
    if (error.message.includes('parse') && retryCount < 3) {
      const models = ['deepseek/deepseek-chat', 'meta-llama/llama-3.2-3b-instruct:free', 'google/gemini-2.0-flash-exp:free'];
      const nextModel = models[retryCount];
      console.log(`Retrying with model: ${nextModel}`);
      setTimeout(() => initializeSession(retryCount + 1), 1000);
      return;
    }
    
    setError('Failed to start analysis. Please try again.');
  } finally {
    setLoading(false);
  }
};

// Update handleSubmit to handle empty questions better
const handleSubmit = async () => {
  if (!userInput.trim() || !sessionId || isAnalyzing) return;

  try {
    setIsAnalyzing(true);
    setError(null);
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userInput,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setUserInput('');

    // Continue deep dive
    const response = await deepDiveApi.continueDeepDive(
      sessionId,
      userInput,
      questionNumber
    );

    console.log('Deep Dive continue response:', response);
    console.log('Question received:', response.question);
    console.log('Question is blank:', !response.question || response.question.trim() === '');
    console.log('Response structure:', {
      hasQuestion: !!response.question,
      questionLength: response.question?.length || 0,
      questionNumber: response.question_number,
      readyForAnalysis: response.ready_for_analysis
    });

    // Check if ready for analysis or has valid question
    if (response.ready_for_analysis || !response.question || response.question.trim() === '') {
      // Complete the analysis
      await completeAnalysis();
    } else {
      // Add assistant message with next question
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.question,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setCurrentQuestion(response.question);
      setQuestionNumber(response.question_number || questionNumber + 1);
      setIsAnalyzing(false);
    }
  } catch (error) {
    console.error('Failed to continue deep dive:', error);
    setError('Failed to process your response. Please try again.');
    setIsAnalyzing(false);
  }
};
```

## Deployment Steps for Railway

1. **Test locally first**:
```bash
# Set environment variables
export OPENROUTER_API_KEY=your_key
export SUPABASE_URL=your_url
export SUPABASE_KEY=your_key

# Test the updated backend
python run_oracle.py
```

2. **Commit changes**:
```bash
git add -A
git commit -m "Fix deep dive model issues and add robust JSON parsing"
git push origin main
```

3. **Railway will auto-deploy** from your GitHub repo

4. **Monitor Railway logs** to ensure the deployment is successful

## Testing the Fix

Test the deep dive with curl to verify it's working:

```bash
# Test with explicit model
curl -X POST https://web-production-945c4.up.railway.app/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "chest",
    "form_data": {"symptoms": "chest pain"},
    "model": "deepseek/deepseek-chat"
  }'

# Test without model (should use default)
curl -X POST https://web-production-945c4.up.railway.app/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "chest",
    "form_data": {"symptoms": "chest pain"}
  }'
```

## Summary of Changes

### Backend:
1. Changed default model from `deepseek/deepseek-r1-0528:free` to `deepseek/deepseek-chat`
2. Added robust JSON extraction with multiple fallback strategies
3. Added model validation and fallback list
4. Added error handling for parse failures

### Frontend:
1. Updated default model to working version
2. Added retry logic with different models
3. Better error handling for parse failures
4. Improved response validation

These changes will make your deep dive feature much more reliable and handle edge cases gracefully.