# Next.js Oracle Integration - Complete Copy & Paste Guide

Follow these steps exactly and your Oracle chat will work immediately.

## Step 1: Install Dependencies

Run this in your Next.js project root:

```bash
npm install uuid axios
```

## Step 2: Add Environment Variable

Create or add to `.env.local` in your Next.js root:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Step 3: Create the Oracle Client

Create file: `lib/oracle-client.ts`

```typescript
import { v4 as uuidv4 } from 'uuid';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface OracleMessage {
  query: string;
  user_id: string;
  conversation_id: string;
  category?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface OracleResponse {
  response: string | Record<string, any>;
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

export class OracleClient {
  private baseUrl: string;
  private defaultRetries: number = 3;
  private defaultTimeout: number = 30000; // 30 seconds

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Send a message to Oracle and get a response
   */
  async sendMessage(
    query: string,
    userId: string,
    conversationId?: string,
    options?: {
      category?: string;
      model?: string;
      temperature?: number;
      maxTokens?: number;
      retries?: number;
    }
  ): Promise<OracleResponse> {
    // Generate conversation ID if not provided
    const convId = conversationId || uuidv4();
    
    const message: OracleMessage = {
      query,
      user_id: userId,
      conversation_id: convId,
      category: options?.category || 'health-scan',
      model: options?.model,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens
    };

    const retries = options?.retries || this.defaultRetries;
    
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await axios.post<OracleResponse>(
          `${this.baseUrl}/api/chat`,
          message,
          {
            timeout: this.defaultTimeout,
            headers: {
              'Content-Type': 'application/json',
            }
          }
        );

        return response.data;
      } catch (error) {
        if (attempt === retries) {
          throw this.handleError(error);
        }
        // Exponential backoff
        await this.delay(Math.pow(2, attempt - 1) * 1000);
      }
    }

    throw new Error('Failed after all retries');
  }

  /**
   * Create a new conversation
   */
  async createConversation(userId: string): Promise<string> {
    return uuidv4();
  }

  /**
   * Check server health
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/health`);
      return response.data.status === 'healthy';
    } catch {
      return false;
    }
  }

  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with error
        return new Error(`Oracle API Error: ${error.response.status} - ${error.response.data.detail || error.response.statusText}`);
      } else if (error.request) {
        // No response received
        return new Error('Oracle API is not responding. Please check if the server is running.');
      }
    }
    return new Error('An unexpected error occurred');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton instance
export const oracleClient = new OracleClient();
```

## Step 4: Create the React Hook

Create file: `hooks/useOracle.ts`

```typescript
import { useState, useCallback, useRef, useEffect } from 'react';
import { oracleClient, OracleResponse } from '@/lib/oracle-client';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string | Record<string, any>;
  timestamp: Date;
  metadata?: {
    tokens?: number;
    model?: string;
  };
}

export interface UseOracleOptions {
  userId: string;
  conversationId?: string;
  onError?: (error: Error) => void;
  onSuccess?: (response: OracleResponse) => void;
}

export function useOracle({
  userId,
  conversationId: initialConversationId,
  onError,
  onSuccess
}: UseOracleOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [conversationId, setConversationId] = useState<string>(
    initialConversationId || ''
  );
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  // Initialize conversation ID
  useEffect(() => {
    if (!conversationId) {
      oracleClient.createConversation(userId).then(setConversationId);
    }
  }, [conversationId, userId]);

  // Check server health on mount
  useEffect(() => {
    oracleClient.checkHealth().then(setIsHealthy);
  }, []);

  const sendMessage = useCallback(
    async (query: string, options?: {
      category?: string;
      model?: string;
      temperature?: number;
      maxTokens?: number;
    }) => {
      if (!query.trim()) {
        const err = new Error('Message cannot be empty');
        setError(err);
        onError?.(err);
        return;
      }

      if (!conversationId) {
        const err = new Error('No conversation ID available');
        setError(err);
        onError?.(err);
        return;
      }

      setIsLoading(true);
      setError(null);

      // Add user message immediately for better UX
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);

      try {
        const response = await oracleClient.sendMessage(
          query,
          userId,
          conversationId,
          options
        );

        // Add Oracle's response
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
          metadata: {
            tokens: response.usage.total_tokens,
            model: response.model
          }
        };
        setMessages(prev => [...prev, assistantMessage]);

        onSuccess?.(response);
        return response;
      } catch (err) {
        const error = err as Error;
        setError(error);
        onError?.(error);
        
        // Remove the user message on error
        setMessages(prev => prev.filter(m => m.id !== userMessage.id));
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId, userId, onError, onSuccess]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const startNewConversation = useCallback(async () => {
    const newId = await oracleClient.createConversation(userId);
    setConversationId(newId);
    clearMessages();
    return newId;
  }, [userId, clearMessages]);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    conversationId,
    isHealthy,
    clearMessages,
    startNewConversation
  };
}
```

## Step 5: Create the Oracle Chat Component

Create file: `components/OracleChat.tsx`

```tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { useOracle } from '@/hooks/useOracle';

interface OracleChatProps {
  userId: string;
  conversationId?: string;
  className?: string;
}

export function OracleChat({ userId, conversationId, className = '' }: OracleChatProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    sendMessage,
    isLoading,
    error,
    conversationId: currentConversationId,
    isHealthy,
    startNewConversation
  } = useOracle({
    userId,
    conversationId,
    onError: (error) => {
      console.error('Oracle error:', error);
      // You can add toast notifications here
    }
  });

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    setInput('');
    
    try {
      await sendMessage(query);
    } catch (error) {
      // Error is already handled by the hook
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const renderMessage = (message: typeof messages[0]) => {
    // Handle structured JSON responses
    if (typeof message.content === 'object' && message.content !== null) {
      // Check if it's a health form response
      if ('confidence_level' in message.content || 'symptoms' in message.content) {
        return (
          <div className="structured-health-response">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold mb-2">Health Analysis</h4>
              <pre className="text-sm overflow-x-auto">
                {JSON.stringify(message.content, null, 2)}
              </pre>
            </div>
          </div>
        );
      }
      
      // Generic JSON response
      return (
        <pre className="bg-gray-100 p-3 rounded overflow-x-auto text-sm">
          {JSON.stringify(message.content, null, 2)}
        </pre>
      );
    }

    // Regular text response - preserve line breaks
    return (
      <div className="whitespace-pre-wrap break-words">
        {message.content}
      </div>
    );
  };

  return (
    <div className={`oracle-chat flex flex-col h-full bg-white rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Oracle Health Assistant</h2>
            <p className="text-sm text-gray-500">
              Conversation: {currentConversationId?.slice(0, 8)}...
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${
                isHealthy === true ? 'bg-green-500' : 
                isHealthy === false ? 'bg-red-500' : 
                'bg-gray-400'
              }`} />
              <span className="text-sm text-gray-600">
                {isHealthy === true ? 'Connected' : 
                 isHealthy === false ? 'Disconnected' : 
                 'Checking...'}
              </span>
            </div>
            <button
              onClick={startNewConversation}
              className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
            >
              New Chat
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg mb-2">Welcome to Oracle Health Assistant</p>
            <p className="text-sm">Ask me anything about your health concerns</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[70%] ${
              message.role === 'user' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-900'
            } rounded-lg px-4 py-3`}>
              <div className="text-xs opacity-75 mb-1">
                {message.role === 'user' ? 'You' : 'Oracle'}
                {message.metadata?.tokens && (
                  <span className="ml-2">• {message.metadata.tokens} tokens</span>
                )}
              </div>
              {renderMessage(message)}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            <p className="font-semibold">Error</p>
            <p className="text-sm">{error.message}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your symptoms or health concerns..."
            className="flex-1 min-h-[50px] max-h-[150px] p-3 border rounded-lg 
                     focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            disabled={isLoading}
            rows={1}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg 
                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors duration-200"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}
```

## Step 6: Create the Oracle Page

Create file: `app/oracle/page.tsx`

```tsx
'use client';

import { OracleChat } from '@/components/OracleChat';
import { useUser } from '@clerk/nextjs'; // or your auth provider

export default function OraclePage() {
  const { user } = useUser();

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Please log in to use Oracle Health Assistant</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto h-[calc(100vh-2rem)]">
        <OracleChat userId={user.id} />
      </div>
    </div>
  );
}
```

## Step 7: (Optional) If Not Using Clerk Auth

Replace the page with this simpler version:

```tsx
'use client';

import { OracleChat } from '@/components/OracleChat';

export default function OraclePage() {
  // Use a hardcoded user ID for testing
  const userId = "test-user-123"; // Replace with actual user ID logic
  
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto h-[calc(100vh-2rem)]">
        <OracleChat userId={userId} />
      </div>
    </div>
  );
}
```

## Step 8: Start Your Backend Server

In your backend directory (`mcp-backend`), run:

```bash
# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start the server
uv run python run_full_server.py
```

## Step 9: Run Your Next.js App

```bash
npm run dev
```

## Step 10: Navigate to Oracle

Open your browser and go to:
```
http://localhost:3000/oracle
```

## That's It! 🎉

Your Oracle chat should now be working. Just:
1. Type a health question
2. Press Enter
3. Get response from Oracle

## Quick Test

To test if everything is working, open your browser console and run:

```javascript
fetch('http://localhost:8000/api/health')
  .then(res => res.json())
  .then(console.log);
```

You should see: `{status: "healthy", service: "Medical Chat API"}`

## Troubleshooting

If it doesn't work:

1. **Check backend is running**: Visit http://localhost:8000/api/health
2. **Check console errors**: Open browser dev tools
3. **Check CORS**: Make sure backend allows localhost:3000
4. **Check .env.local**: Must have `NEXT_PUBLIC_API_URL=http://localhost:8000`

## File Structure

After creating all files, you should have:
```
your-nextjs-app/
├── .env.local
├── lib/
│   └── oracle-client.ts
├── hooks/
│   └── useOracle.ts
├── components/
│   └── OracleChat.tsx
└── app/
    └── oracle/
        └── page.tsx
```