# Oracle Chat Integration Guide for Next.js

## Overview
This document explains how to integrate the Oracle medical chat backend with your Next.js application.

## Backend Server Setup

### Starting the Server

**For HTTP API (Web/Mobile apps):**
```bash
# Option 1: Using uv
uv run python run_api_server.py

# Option 2: Using the script
./run_server.sh

# The server will run on http://0.0.0.0:8000 (same as http://localhost:8000)
# API docs available at: http://0.0.0.0:8000/docs
```

**For MCP Tools (Claude Desktop):**
```bash
# This requires fixing the mount issue first
# Currently, run HTTP API only
```

### API Endpoints
- **POST** `/api/chat` - Main chat endpoint for Oracle conversations
- **GET** `/api/health` - Health check endpoint

## Next.js Integration

### 1. Create API Utility Functions

Create `lib/oracle-api.ts`:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChatRequest {
  query: string;
  user_id: string;
  conversation_id: string;
  category?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

interface ChatResponse {
  response: string | Record<string, any>; // Can be JSON for structured data
  raw_response: string;
  conversation_id: string;
  user_id: string;
  category: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model: string;
}

export async function sendChatMessage(
  request: ChatRequest,
  retries = 3
): Promise<ChatResponse> {
  let lastError: Error | null = null;

  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...request,
          category: request.category || 'health-scan',
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      lastError = error as Error;
      
      // Wait before retry (exponential backoff)
      if (i < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
      }
    }
  }

  throw lastError || new Error('Failed to send message after retries');
}
```

### 2. Create Chat Hook

Create `hooks/useOracleChat.ts`:

```typescript
import { useState, useCallback } from 'react';
import { sendChatMessage } from '@/lib/oracle-api';
import { useUser } from '@clerk/nextjs'; // or your auth provider

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string | Record<string, any>;
  timestamp: Date;
}

export function useOracleChat(conversationId: string) {
  const { user } = useUser(); // Get user from your auth
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (query: string) => {
    if (!user?.id) {
      setError('User not authenticated');
      return;
    }

    setIsLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await sendChatMessage({
        query,
        user_id: user.id,
        conversation_id: conversationId,
      });

      // Add assistant response
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [user, conversationId]);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
  };
}
```

### 3. Create Chat Component

Create `components/OracleChat.tsx`:

```tsx
'use client';

import { useState, useEffect } from 'react';
import { useOracleChat } from '@/hooks/useOracleChat';
import { v4 as uuidv4 } from 'uuid';

interface OracleChatProps {
  initialConversationId?: string;
}

export function OracleChat({ initialConversationId }: OracleChatProps) {
  const [conversationId] = useState(initialConversationId || uuidv4());
  const [input, setInput] = useState('');
  const { messages, sendMessage, isLoading, error } = useOracleChat(conversationId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    setInput('');
    await sendMessage(query);
  };

  const renderMessage = (message: typeof messages[0]) => {
    // Handle structured responses (JSON)
    if (typeof message.content === 'object') {
      return (
        <div className="structured-response">
          <pre className="bg-gray-100 p-2 rounded">
            {JSON.stringify(message.content, null, 2)}
          </pre>
        </div>
      );
    }

    // Regular text response
    return <p className="whitespace-pre-wrap">{message.content}</p>;
  };

  return (
    <div className="oracle-chat flex flex-col h-full">
      <div className="messages-container flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${
              message.role === 'user' 
                ? 'ml-auto bg-blue-500 text-white' 
                : 'mr-auto bg-gray-200'
            } max-w-[80%] p-3 rounded-lg`}
          >
            {renderMessage(message)}
          </div>
        ))}
        
        {isLoading && (
          <div className="mr-auto bg-gray-200 p-3 rounded-lg">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" />
            </div>
          </div>
        )}
        
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded-lg">
            Error: {error}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Oracle about your health..."
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
```

### 4. Using in Your Page

```tsx
// app/oracle/page.tsx
import { OracleChat } from '@/components/OracleChat';

export default function OraclePage() {
  return (
    <div className="container mx-auto max-w-4xl h-screen py-8">
      <h1 className="text-2xl font-bold mb-4">Oracle Health Assistant</h1>
      <div className="h-[calc(100vh-8rem)] bg-white rounded-lg shadow-lg">
        <OracleChat />
      </div>
    </div>
  );
}
```

## Environment Variables

Add to your `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## How It Works

1. **Conversation Flow**:
   - Next.js generates a `conversation_id` (UUID) when chat starts
   - First message: Backend creates system prompt with Oracle persona
   - Subsequent messages: Backend retrieves full history from messages table
   - All messages are stored with roles (system/user/assistant)

2. **Message Storage**:
   - User messages stored immediately when sent
   - Assistant responses stored after LLM responds
   - Token counts and metadata tracked

3. **Structured Responses**:
   - Oracle can return JSON for forms (confidence levels, symptoms, etc.)
   - Frontend detects and renders appropriately

4. **Error Handling**:
   - Automatic retry with exponential backoff
   - User-friendly error messages
   - Failed messages removed from UI

## Creating Conversations in Next.js

If you need to create conversation records from Next.js:

```typescript
// lib/conversations.ts
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function createConversation(userId: string, title: string) {
  const { data, error } = await supabase
    .table('conversations')
    .insert({
      user_id: userId,
      title: title,
      conversation_type: 'oracle_health',
      status: 'active',
      ai_provider: 'openrouter',
      model_name: 'tngtech/deepseek-r1t-chimera:free',
      metadata: {}
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}
```

## Testing

1. Start the backend server:
   ```bash
   cd mcp-backend
   python mcp-backend.py
   ```

2. Start your Next.js app:
   ```bash
   npm run dev
   ```

3. Navigate to `/oracle` and start chatting!

## Troubleshooting

- **CORS Issues**: Backend uses FastAPI which handles CORS. If issues, add CORS middleware
- **Connection Refused**: Ensure backend is running on port 8000
- **Auth Issues**: Verify user_id is being passed correctly from your auth provider
- **Empty Responses**: Check OpenRouter API key and model availability