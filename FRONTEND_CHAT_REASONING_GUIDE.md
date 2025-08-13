# Frontend Chat Reasoning Mode Implementation Guide

## 🧠 Understanding Reasoning Mode

### What is Reasoning Mode?
- **Enabled (`reasoning_mode: true`)**: Models show their "chain of thought" - the step-by-step thinking process
- **Disabled (`reasoning_mode: false`)**: Normal LLM response without visible thinking process

### Model Behavior by Tier

#### Premium Tiers (Pro/Pro+)
- **Default (no reasoning)**: `anthropic/claude-sonnet-4` - Direct responses
- **With Reasoning**: `openai/gpt-5-mini` → `openai/gpt-5` - Shows thinking process

#### Free Tier
- **Default (no reasoning)**: `deepseek/deepseek-chat` - Direct responses  
- **With Reasoning**: `deepseek/deepseek-r1` - Shows transparent thinking

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

## 📦 Response Format & Parsing

### Response Structure
```javascript
{
  "response": "Final answer without reasoning",  // Clean response
  "message": "Final answer without reasoning",   // Duplicate for compatibility
  "model": "openai/gpt-5-mini",
  "reasoning_tokens": 850,  // Only for DeepSeek R1
  "reasoning": "The thinking process...",  // Only for GPT-5/o1 models
  "usage": {
    "prompt_tokens": 500,
    "completion_tokens": 2000,
    "total_tokens": 2500,
    "reasoning_tokens": 850  // If available
  },
  "tier": "pro_plus",
  "reasoning_mode": true,
  "status": "success"
}
```

### Parsing Reasoning from Response

For models that include reasoning in the main content (GPT-5, o1):

```javascript
function parseReasoningResponse(response) {
  const content = response.response || response.message;
  
  // GPT-5/o1 models may include reasoning in the response
  // Look for reasoning markers
  const reasoningMarkers = [
    '**Reasoning:**',
    '**Thinking:**',
    '<reasoning>',
    '**Chain of thought:**'
  ];
  
  let reasoning = null;
  let cleanResponse = content;
  
  // Check if model is GPT-5/o1 (they include reasoning)
  if (response.model?.includes('gpt-5') || response.model?.includes('o1')) {
    // Try to extract reasoning section
    for (const marker of reasoningMarkers) {
      const index = content.indexOf(marker);
      if (index !== -1) {
        reasoning = content.substring(index);
        cleanResponse = content.substring(0, index).trim();
        break;
      }
    }
    
    // Alternative: Check for reasoning in response object
    if (response.reasoning) {
      reasoning = response.reasoning;
    }
  }
  
  // DeepSeek R1 provides reasoning separately
  if (response.model?.includes('deepseek-r1')) {
    reasoning = response.reasoning || null;
    // DeepSeek R1 reasoning is already separated
  }
  
  return {
    reasoning,
    cleanResponse,
    hasReasoning: !!reasoning,
    reasoningTokens: response.reasoning_tokens || response.usage?.reasoning_tokens || 0
  };
}
```

## 🎨 UI Component Example

```jsx
function ChatMessage({ message, response }) {
  const [showReasoning, setShowReasoning] = useState(false);
  const { reasoning, cleanResponse, hasReasoning } = parseReasoningResponse(response);
  
  return (
    <div className="chat-message">
      {/* Main Response */}
      <div className="message-content">
        {cleanResponse}
      </div>
      
      {/* Reasoning Toggle (only if reasoning exists) */}
      {hasReasoning && (
        <div className="reasoning-section">
          <button 
            onClick={() => setShowReasoning(!showReasoning)}
            className="reasoning-toggle-btn"
          >
            {showReasoning ? '🧠 Hide' : '🧠 Show'} Thinking Process
            {response.reasoning_tokens && (
              <span className="token-count">
                ({response.reasoning_tokens} reasoning tokens)
              </span>
            )}
          </button>
          
          {showReasoning && (
            <div className="reasoning-content">
              <div className="reasoning-header">
                Chain of Thought ({response.model})
              </div>
              <pre className="reasoning-text">
                {reasoning}
              </pre>
            </div>
          )}
        </div>
      )}
      
      {/* Model Indicator */}
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

## 🔄 Complete Implementation Flow

```jsx
function ChatInterface() {
  const [reasoningMode, setReasoningMode] = useState(false);
  const [messages, setMessages] = useState([]);
  const [userTier, setUserTier] = useState('free');
  
  const sendMessage = async (text) => {
    // Add user message to UI
    const userMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    
    // Prepare request
    const request = {
      query: text,
      user_id: currentUser.id,
      conversation_id: currentConversation.id,
      reasoning_mode: reasoningMode
    };
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      
      const data = await response.json();
      
      // Parse reasoning if present
      const { reasoning, cleanResponse } = parseReasoningResponse(data);
      
      // Add assistant message
      const assistantMessage = {
        role: 'assistant',
        content: cleanResponse,
        reasoning: reasoning,
        model: data.model,
        reasoning_mode: data.reasoning_mode,
        full_response: data
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setUserTier(data.tier);
      
    } catch (error) {
      console.error('Chat error:', error);
    }
  };
  
  return (
    <div className="chat-interface">
      {/* Reasoning Mode Toggle */}
      <div className="chat-controls">
        <label className="reasoning-toggle">
          <input
            type="checkbox"
            checked={reasoningMode}
            onChange={(e) => setReasoningMode(e.target.checked)}
          />
          <span>
            {userTier === 'free' 
              ? 'Enable Transparent Thinking (DeepSeek R1)'
              : 'Enable Enhanced Analysis (GPT-5)'}
          </span>
        </label>
        
        {reasoningMode && (
          <div className="reasoning-info">
            {userTier === 'free' ? (
              <p>DeepSeek R1 will show its step-by-step reasoning process</p>
            ) : (
              <p>GPT-5 will provide deeper analysis with extended processing</p>
            )}
          </div>
        )}
      </div>
      
      {/* Messages */}
      <div className="messages">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} response={msg.full_response} />
        ))}
      </div>
    </div>
  );
}
```

## 📊 Model Selection by Tier & Mode

| Tier | Reasoning Mode | Primary Model | Fallback | Shows Thinking? |
|------|---------------|--------------|----------|-----------------|
| Free | OFF | `deepseek/deepseek-chat` | - | No |
| Free | ON | `deepseek/deepseek-r1` | - | Yes (transparent) |
| Pro/Pro+ | OFF | `anthropic/claude-sonnet-4` | `openai/gpt-4o` | No |
| Pro/Pro+ | ON | `openai/gpt-5-mini` | `openai/gpt-5` | Yes (in response) |

## 🔍 Detecting Reasoning in Response

Different models provide reasoning differently:

### GPT-5/GPT-5-mini
- Reasoning may be included in the main response
- Look for the `reasoning` field in response
- May use markers like "**Reasoning:**" in content

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