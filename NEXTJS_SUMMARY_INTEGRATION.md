# Next.js Oracle + Summary Integration Guide

## 🚀 Complete Backend Integration

Your Oracle server now has **3 main endpoints**:

### 1. Chat Endpoint (existing)
```javascript
POST http://localhost:8000/api/chat
```

### 2. Generate Summary (NEW)
```javascript
POST http://localhost:8000/api/generate_summary
```

### 3. Health Check
```javascript
GET http://localhost:8000/api/health
```

## 📱 Next.js Integration Code

### 1. Add Summary Generation to Your Chat Component

```typescript
// In your chat component or API service

// When user ends chat or navigates away
const generateChatSummary = async (conversationId: string, userId: string) => {
  try {
    const response = await fetch('http://localhost:8000/api/generate_summary', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        user_id: userId
      })
    });

    const result = await response.json();
    
    if (result.status === 'success') {
      console.log('Summary generated:', result.summary);
      console.log('Token count:', result.token_count);
      console.log('Compression ratio:', result.compression_ratio);
    }
  } catch (error) {
    console.error('Error generating summary:', error);
  }
};
```

### 2. Auto-Generate Summary on Chat End

```typescript
// In your chat component
import { useEffect } from 'react';
import { useRouter } from 'next/router';

const ChatPage = () => {
  const router = useRouter();
  const { conversationId, userId } = useYourAuthHook();

  // Generate summary when leaving page
  useEffect(() => {
    const handleRouteChange = () => {
      // Generate summary when navigating away
      generateChatSummary(conversationId, userId);
    };

    router.events.on('routeChangeStart', handleRouteChange);
    
    // Cleanup
    return () => {
      router.events.off('routeChangeStart', handleRouteChange);
    };
  }, [conversationId, userId]);

  // Also handle browser close/refresh
  useEffect(() => {
    const handleUnload = () => {
      // Use sendBeacon for reliability
      navigator.sendBeacon(
        'http://localhost:8000/api/generate_summary',
        JSON.stringify({
          conversation_id: conversationId,
          user_id: userId
        })
      );
    };

    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, [conversationId, userId]);

  // Your chat UI here
};
```

### 3. Create a Custom Hook for Chat Management

```typescript
// hooks/useOracleChat.ts
import { useState, useCallback, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const useOracleChat = (userId: string, conversationId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  // Send message to Oracle
  const sendMessage = useCallback(async (query: string) => {
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          user_id: userId,
          conversation_id: conversationId,
          category: 'health-scan'
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        setMessages(prev => [
          ...prev,
          { role: 'user', content: query },
          { role: 'assistant', content: data.response }
        ]);
      }
      
      return data;
    } finally {
      setLoading(false);
    }
  }, [userId, conversationId]);

  // Generate summary
  const generateSummary = useCallback(async () => {
    const response = await fetch('http://localhost:8000/api/generate_summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        user_id: userId
      })
    });

    return response.json();
  }, [userId, conversationId]);

  // Auto-generate summary on unmount
  useEffect(() => {
    return () => {
      if (messages.length > 0) {
        // Generate summary when component unmounts
        generateSummary().catch(console.error);
      }
    };
  }, [messages.length, generateSummary]);

  return {
    messages,
    sendMessage,
    generateSummary,
    loading
  };
};
```

### 4. Complete Chat Component Example

```tsx
// components/OracleChat.tsx
import { useState } from 'react';
import { useOracleChat } from '../hooks/useOracleChat';

export const OracleChat = ({ userId, conversationId }) => {
  const [input, setInput] = useState('');
  const { messages, sendMessage, generateSummary, loading } = useOracleChat(userId, conversationId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    await sendMessage(input);
    setInput('');
  };

  const handleEndChat = async () => {
    // Manually trigger summary generation
    const result = await generateSummary();
    console.log('Chat summary generated:', result);
    
    // Navigate away or close chat
    // router.push('/dashboard');
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? 'You' : 'Oracle'}:</strong>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Oracle about your health..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          Send
        </button>
      </form>

      <button onClick={handleEndChat} className="end-chat-btn">
        End Chat & Save Summary
      </button>
    </div>
  );
};
```

## 🔧 How the Backend Works

### When you call `/api/chat`:
1. Fetches user medical data from `medical` table
2. Fetches LLM context from `llm_context` table
3. If context > 25k tokens, automatically aggregates all summaries
4. Sends to AI with full context
5. Saves message to `messages` table
6. Updates conversation in `conversations` table

### When you call `/api/generate_summary`:
1. Fetches ALL messages from the conversation
2. Counts tokens to determine summary length (sliding scale)
3. Generates medical-style summary via AI
4. Deletes old summary if exists
5. Saves new summary to `llm_context` table

### Automatic Context Management:
- < 25k tokens: Uses specific conversation summary
- > 25k tokens: Aggregates all user summaries with compression
- Compression ratios: 1.5x → 2x → 5x → 10x → 20x → 100x

## 🎯 Testing in Your Next.js App

```javascript
// Quick test script
const testOracleWithSummary = async () => {
  const userId = 'your-user-id';  // From your auth
  const conversationId = 'some-uuid';  // Generate or use existing

  // Send a few messages
  for (const msg of ['I have headaches', 'They last 4 hours', 'Happens daily']) {
    await fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: msg,
        user_id: userId,
        conversation_id: conversationId
      })
    });
  }

  // Generate summary
  const summaryResponse = await fetch('http://localhost:8000/api/generate_summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      user_id: userId
    })
  });

  const summary = await summaryResponse.json();
  console.log('Generated summary:', summary);
};
```

## 🚨 Important Notes

1. **UUIDs**: Your Supabase uses UUID columns, so make sure your IDs are valid UUIDs
2. **Auto-Summary**: The system automatically generates summaries when you call the endpoint
3. **Context Loading**: Oracle automatically uses summaries for context in future chats
4. **Token Management**: Everything is handled automatically based on conversation length

## 🛠️ Error Handling

```typescript
try {
  const result = await generateSummary();
  if (result.status === 'error') {
    console.error('Summary generation failed:', result.error);
    // Handle error - maybe retry or notify user
  }
} catch (error) {
  console.error('Network error:', error);
}
```

## 📝 Summary Response Format

```typescript
interface SummaryResponse {
  summary: string;           // The medical summary
  token_count: number;       // Tokens in summary
  compression_ratio: number; // How much it was compressed
  status: 'success' | 'error';
  error?: string;           // Only if status is error
}
```

That's it! Your Oracle server now has full summary generation integrated. Just call the endpoints from your Next.js app!