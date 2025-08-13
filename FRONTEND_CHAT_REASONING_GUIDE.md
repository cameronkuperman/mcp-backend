# Frontend Chat Reasoning Mode Implementation Guide

## 🎯 WORKING Implementation (Updated 2025-01-13)

### What is Reasoning Mode?
- **Enabled (`reasoning_mode: true`)**: Models show their "chain of thought" - the step-by-step thinking process
- **Disabled (`reasoning_mode: false`)**: Normal LLM response without visible thinking process

### ✅ CONFIRMED WORKING Models

#### Premium Tiers (Basic/Pro/Pro+)
- **Default (no reasoning)**: `openai/gpt-5-mini` or `anthropic/claude-sonnet-4`
- **With Reasoning**: `anthropic/claude-3.7-sonnet` ✅ - Returns reasoning in separate field
- **Fallback**: `openai/gpt-5` - Uses max_completion_tokens

#### Free Tier
- **Default (no reasoning)**: `deepseek/deepseek-chat`
- **With Reasoning**: `deepseek/deepseek-r1` ✅ - Returns reasoning in separate field

## 📡 API Request Format

```javascript
// Chat request with reasoning mode
const chatRequest = {
  query: "User's message",
  user_id: "user-uuid",
  conversation_id: "conv-uuid",
  reasoning_mode: true  // Enable chain of thought
};

const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(chatRequest)
});
```

## 📦 ACTUAL Response Format (TESTED & WORKING)

### Real Response Example - Claude 3.7 Sonnet
```javascript
{
  "response": "The answer to 5+5 is 10.\n\nI'm here primarily to help...",
  "message": "The answer to 5+5 is 10.\n\nI'm here primarily to help...",
  "reasoning": "This is a simple arithmetic question, not a health-related query. The user is asking what 5+5 equals, which is 10...",
  "has_reasoning": true,  // ✅ This actually works!
  "conversation_id": "550e8400-e29b-41d4-a716-446655440027",
  "usage": {
    "prompt_tokens": 329,
    "completion_tokens": 206,
    "total_tokens": 535,
    "reasoning_tokens": 134,  // ✅ Counted from reasoning text
    "response_tokens": 72     // ✅ Actual response without reasoning
  },
  "model": "anthropic/claude-3.7-sonnet",
  "reasoning_mode": true,
  "status": "success"
}
```

### Real Response Example - DeepSeek R1
```javascript
{
  "response": "3+3 equals 6.\n\nIs there anything health-related...",
  "reasoning": "Okay, the user asked, \"What is 3+3?\" Let me start by recalling their medical history...",
  "has_reasoning": true,  // ✅ Works for DeepSeek too!
  "usage": {
    "prompt_tokens": 191,
    "completion_tokens": 307,
    "total_tokens": 498,
    "reasoning_tokens": 230,  // ✅ DeepSeek counts these
    "response_tokens": 77
  },
  "model": "deepseek/deepseek-r1"
}
```

### Frontend Implementation (SIMPLE!)

```javascript
function handleChatResponse(response) {
  // IT'S THIS SIMPLE NOW!
  if (response.has_reasoning && response.reasoning) {
    // Show reasoning in UI
    return {
      mainResponse: response.response,
      reasoning: response.reasoning,
      reasoningTokens: response.usage?.reasoning_tokens || 0,
      model: response.model
    };
  } else {
    // No reasoning available
    return {
      mainResponse: response.response,
      reasoning: null,
      model: response.model
    };
  }
}
```

## 🎨 React Component Example (WORKING CODE)

```jsx
function ChatMessage({ response }) {
  const [showReasoning, setShowReasoning] = useState(false);
  
  return (
    <div className="chat-message">
      {/* Main Response */}
      <div className="message-content">
        {response.response}
      </div>
      
      {/* Reasoning Toggle - Only shows if reasoning exists */}
      {response.has_reasoning && response.reasoning && (
        <div className="reasoning-section">
          <button 
            onClick={() => setShowReasoning(!showReasoning)}
            className="reasoning-toggle-btn"
          >
            {showReasoning ? '🧠 Hide' : '🧠 Show'} Thinking Process
            {response.usage?.reasoning_tokens && (
              <span className="token-count">
                ({response.usage.reasoning_tokens} reasoning tokens)
              </span>
            )}
          </button>
          
          {showReasoning && (
            <div className="reasoning-content">
              <div className="reasoning-header">
                Chain of Thought • {response.model}
              </div>
              <pre className="reasoning-text">
                {response.reasoning}
              </pre>
            </div>
          )}
        </div>
      )}
      
      {/* Model & Token Info */}
      <div className="message-meta">
        <span className="model-badge">{response.model}</span>
        {response.reasoning_mode && (
          <span className="reasoning-badge">Enhanced Reasoning</span>
        )}
      </div>
    </div>
  );
}
```

## 🔄 Complete Working Implementation

```jsx
function ChatInterface() {
  const [reasoningMode, setReasoningMode] = useState(false);
  const [messages, setMessages] = useState([]);
  
  const sendMessage = async (text) => {
    // Send to backend
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,  // or 'query' - both work
        user_id: currentUser.id,
        conversation_id: currentConversation.id,
        reasoning_mode: reasoningMode  // ← This triggers reasoning!
      })
    });
    
    const data = await response.json();
    
    // THE RESPONSE ALREADY HAS EVERYTHING SEPARATED!
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: data.response,           // Clean response
      reasoning: data.reasoning,        // Reasoning text (if any)
      has_reasoning: data.has_reasoning, // Boolean flag
      tokens: {
        total: data.usage?.total_tokens,
        reasoning: data.usage?.reasoning_tokens,
        response: data.usage?.response_tokens
      },
      model: data.model
    }]);
  };
  
  return (
    <div className="chat-interface">
      {/* Reasoning Toggle */}
      <label>
        <input
          type="checkbox"
          checked={reasoningMode}
          onChange={(e) => setReasoningMode(e.target.checked)}
        />
        Enable Chain of Thought Reasoning
      </label>
      
      {/* Messages */}
      {messages.map((msg, idx) => (
        <ChatMessage key={idx} response={msg} />
      ))}
    </div>
  );
}
```

## 📊 What Actually Happens

### When `reasoning_mode: true`

| User Tier | Model Used | Reasoning Field | Tokens Tracked |
|-----------|------------|-----------------|----------------|
| Free | `deepseek/deepseek-r1` | ✅ Yes, in `reasoning` field | ✅ Yes, `reasoning_tokens` |
| Basic/Pro/Pro+ | `anthropic/claude-3.7-sonnet` | ✅ Yes, in `reasoning` field | ✅ Yes, `reasoning_tokens` |

### When `reasoning_mode: false`

| User Tier | Model Used | Reasoning Field | 
|-----------|------------|-----------------|
| Free | `deepseek/deepseek-chat` | ❌ No, `null` |
| Basic/Pro/Pro+ | `openai/gpt-5-mini` | ❌ No, `null` |

## 🔍 Key Points for Frontend Implementation

1. **Always check `has_reasoning` flag first** - This tells you if reasoning is available
2. **Reasoning is in a separate field** - Look for `response.reasoning`, not embedded in content
3. **Token counts are provided** - `reasoning_tokens` and `response_tokens` are calculated
4. **Models matter** - Only Claude 3.7 Sonnet and DeepSeek R1 return reasoning currently

## ⚡ Quick Implementation Checklist

```javascript
// 1. Send request with reasoning_mode
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    message: userInput,
    reasoning_mode: true  // ← Enable reasoning
  })
});

// 2. Check if reasoning is available
const data = await response.json();
if (data.has_reasoning && data.reasoning) {
  // Show reasoning UI
  showReasoningSection(data.reasoning);
  showTokenCount(data.usage.reasoning_tokens);
}

// 3. Display the main response
showResponse(data.response);
```

### DeepSeek R1
- Provides `reasoning_tokens` count
- Reasoning is transparent and included
- Uses `include_reasoning: true` parameter

### Claude Sonnet 4
- No reasoning mode (always direct responses)
- Used for non-reasoning premium chat

## ⚡ Quick Implementation Checklist

- [ ] Add `reasoning_mode` boolean to chat requests
- [ ] Implement `parseReasoningResponse()` function
- [ ] Create UI toggle for reasoning mode
- [ ] Add reasoning display with show/hide toggle
- [ ] Show reasoning token count when available
- [ ] Display current model being used
- [ ] Handle different reasoning formats per model
- [ ] Test with both free and premium tier users

## 🎯 Important Notes

1. **Token Usage**: Reasoning mode uses significantly more tokens (2-4x)
2. **Response Time**: Reasoning mode takes longer (2-5x slower)
3. **Cost**: Premium models with reasoning cost more
4. **UI/UX**: Always show loading state during reasoning
5. **Parsing**: Different models format reasoning differently

## 🚀 Example Test Cases

```javascript
// Test 1: Free tier without reasoning
{
  user_id: "free-user-id",
  reasoning_mode: false
  // Expected: deepseek/deepseek-chat, no reasoning
}

// Test 2: Free tier with reasoning
{
  user_id: "free-user-id", 
  reasoning_mode: true
  // Expected: deepseek/deepseek-r1, transparent reasoning
}

// Test 3: Premium tier without reasoning
{
  user_id: "premium-user-id",
  reasoning_mode: false
  // Expected: anthropic/claude-sonnet-4, no reasoning
}

// Test 4: Premium tier with reasoning
{
  user_id: "premium-user-id",
  reasoning_mode: true
  // Expected: openai/gpt-5-mini, includes thinking process
}
```

---

Last Updated: 2025-01-17