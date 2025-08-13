# Frontend Reasoning Toggle Implementation Guide

## Overview
This guide explains how to implement the reasoning toggle feature in your frontend to enable enhanced AI reasoning for different subscription tiers.

## What is Reasoning Mode?

Reasoning mode enables deeper, more thoughtful AI responses by:
- **For Free Tier**: Switches from `deepseek/deepseek-chat` to `deepseek/deepseek-r1` (with full reasoning visibility)
- **For Premium Tiers**: Enables extended token limits and enhanced prompting for deeper analysis
- **Automatic for certain endpoints**: Deep dive, reports, and health analysis always use reasoning

## Implementation

### 1. Add Reasoning Toggle State

```javascript
// React example
import { useState } from 'react';

function ChatComponent() {
  const [reasoningMode, setReasoningMode] = useState(false);
  const [userTier, setUserTier] = useState('free'); // Get from user context
  
  // ... rest of component
}
```

### 2. Create the Toggle UI Component

```jsx
// React component example
function ReasoningToggle({ tier, enabled, onChange }) {
  return (
    <div className="reasoning-toggle">
      <label className="flex items-center space-x-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onChange(e.target.checked)}
          className="toggle-checkbox"
        />
        <span className="font-medium">Enhanced Reasoning</span>
      </label>
      
      <div className="reasoning-info text-sm text-gray-600 mt-1">
        {tier === 'free' ? (
          <>
            <span className="icon">🧠</span>
            Uses DeepSeek R1 with full reasoning transparency
          </>
        ) : (
          <>
            <span className="icon">⚡</span>
            Enables deeper analysis with extended processing
          </>
        )}
      </div>
    </div>
  );
}
```

### 3. Include Reasoning Mode in API Requests

```javascript
// API call function
async function sendChatMessage(message, conversationId, userId, reasoningMode) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: message,
      user_id: userId,
      conversation_id: conversationId,
      reasoning_mode: reasoningMode  // Add this field
    })
  });
  
  return response.json();
}

// For other endpoints that support reasoning
async function startDeepDive(bodyPart, formData, userId, reasoningMode) {
  const response = await fetch('/api/deep-dive/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      body_part: bodyPart,
      form_data: formData,
      user_id: userId,
      reasoning_mode: reasoningMode  // Optional - deep dive always uses reasoning
    })
  });
  
  return response.json();
}
```

### 4. Show Active Model Indicator

```jsx
// Model indicator component
function ModelIndicator({ tier, reasoningMode, endpoint }) {
  const getModelInfo = () => {
    if (!reasoningMode) return null;
    
    if (tier === 'free') {
      if (endpoint === 'chat') return 'DeepSeek R1 (with reasoning tokens)';
      if (endpoint === 'deep_dive') return 'DeepSeek R1 (extended analysis)';
      return 'Enhanced reasoning enabled';
    } else {
      if (endpoint === 'chat' && (tier === 'pro' || tier === 'pro_plus')) {
        return 'Claude 4 Sonnet (advanced reasoning)';
      }
      if (endpoint === 'deep_dive') return 'GPT-5 (maximum reasoning)';
      return 'GPT-5 (enhanced analysis)';
    }
  };
  
  const modelInfo = getModelInfo();
  
  if (!modelInfo) return null;
  
  return (
    <div className="model-indicator">
      <span className="icon">🧠</span>
      <span className="model-name">{modelInfo}</span>
    </div>
  );
}
```

### 5. Handle Response with Reasoning

```javascript
// Handle responses that may include reasoning
function handleAIResponse(response) {
  // Check if response includes reasoning tokens (for DeepSeek R1)
  if (response.reasoning_tokens) {
    console.log('Reasoning tokens used:', response.reasoning_tokens);
  }
  
  // Display the response
  displayMessage(response.message || response.response);
  
  // Show token usage if available
  if (response.usage) {
    displayTokenUsage(response.usage);
  }
}
```

## Endpoints That Support Reasoning

### Always Use Reasoning (no toggle needed):
- `/api/deep-dive/*` - All deep dive endpoints
- `/api/reports/*` - All report generation
- `/api/health-analysis/*` - Health analysis endpoints
- `/api/ultra-think` - Ultra thinking mode

### Toggle-Based Reasoning:
- `/api/chat` - Main chat endpoint
- `/api/flash-assessment` - Quick assessments
- `/api/general-assessment` - General health assessments

### Endpoints by Tier:

#### Free Tier Models:
| Endpoint | Default Model | With Reasoning |
|----------|--------------|----------------|
| Chat | `deepseek/deepseek-chat` | `deepseek/deepseek-r1` |
| Deep Dive | `deepseek/deepseek-r1` | Always on |
| Flash Assessment | `deepseek/deepseek-chat` | `deepseek/deepseek-r1` |

#### Premium Tiers (Basic/Pro/Pro+):
| Endpoint | Default Model | With Reasoning |
|----------|--------------|----------------|
| Chat (Basic) | `google/gemini-2.5-flash` | `openai/gpt-5` (8k tokens) |
| Chat (Pro/Pro+) | `anthropic/claude-4-sonnet` | `openai/gpt-5` (8k tokens) |
| Deep Dive | `openai/gpt-5` | Always on (8k tokens) |
| Reports | `openai/gpt-5` | Always on (8k tokens) |
| Ultra Think | `x-ai/grok-4` | Always on (12k tokens) |

## Token Limits by Mode

### Standard Mode:
- Free: 2,000 tokens
- Basic: 4,000 tokens
- Pro: 8,000 tokens
- Pro+: 16,000 tokens

### Reasoning Mode:
- All tiers: Up to 8,000 completion tokens
- Models use what they need (not forced to use all)
- DeepSeek R1: Includes reasoning tokens separately

## Example Full Implementation

```jsx
import React, { useState, useContext } from 'react';
import { UserContext } from './contexts/UserContext';

function EnhancedChat() {
  const { userId, userTier } = useContext(UserContext);
  const [message, setMessage] = useState('');
  const [reasoningMode, setReasoningMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  
  const sendMessage = async () => {
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: message,
          user_id: userId,
          conversation_id: conversationId,
          reasoning_mode: reasoningMode
        })
      });
      
      const data = await response.json();
      
      // Add to conversation
      setConversation(prev => [...prev, 
        { role: 'user', content: message },
        { 
          role: 'assistant', 
          content: data.response,
          model: data.model_used,
          reasoning_tokens: data.reasoning_tokens
        }
      ]);
      
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="chat-container">
      {/* Reasoning Toggle */}
      <div className="chat-controls">
        <ReasoningToggle
          tier={userTier}
          enabled={reasoningMode}
          onChange={setReasoningMode}
        />
        {reasoningMode && (
          <ModelIndicator
            tier={userTier}
            reasoningMode={reasoningMode}
            endpoint="chat"
          />
        )}
      </div>
      
      {/* Chat Messages */}
      <div className="messages">
        {conversation.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.content}
            {msg.reasoning_tokens && (
              <div className="reasoning-info">
                Used {msg.reasoning_tokens} reasoning tokens
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Input */}
      <div className="chat-input">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading}>
          {isLoading ? 'Thinking...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
```

## Testing Your Implementation

1. **Test Free Tier Reasoning Toggle**:
   - Enable reasoning → Should use DeepSeek R1
   - Check response includes reasoning tokens

2. **Test Premium Tier Reasoning**:
   - Enable reasoning → Should use enhanced GPT-5
   - Pro/Pro+ in chat → Should use Claude 4 Sonnet

3. **Test Auto-Reasoning Endpoints**:
   - Deep dive should always use reasoning
   - Reports should always use reasoning
   - No toggle should appear for these

4. **Test Fallback Behavior**:
   - If primary model fails, should use fallback
   - Reasoning mode should persist through fallback

## Notes

- **Reasoning doesn't force max tokens**: Models use what they need up to the limit
- **Cost considerations**: Reasoning mode uses more tokens, affecting costs
- **Response time**: Reasoning mode may take longer due to deeper processing
- **DeepSeek R1 specific**: Returns reasoning within `<think>` tags when `include_reasoning: true`
- **No rate limiting in backend**: Handle rate limiting in frontend as needed