# Complete Oracle Chat Integration Guide for Next.js

This guide shows **exactly** how to integrate the Oracle chat functionality into your Next.js application.

## Server Setup

### 1. Start the Server

```bash
# Navigate to your backend directory
cd /path/to/mcp-backend

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Run the full server (MCP + HTTP)
uv run python run_full_server.py
```

**Alternative: Use a different port**
```bash
# Edit run_full_server.py to use port 8001
# Then in your Next.js .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8001
```

Server will be available at:
- **Base URL**: `http://localhost:8000`
- **API Endpoints**: `http://localhost:8000/api/*`
- **API Docs**: `http://localhost:8000/api/docs`

## Oracle Chat Endpoint Details

### Endpoint: `POST /api/chat`

**URL**: `http://localhost:8000/api/chat`

**Request Body**:
```json
{
  "query": "string",              // User's health question
  "user_id": "string",            // Unique user identifier
  "conversation_id": "string",    // Unique conversation ID (generate with uuid)
  "category": "string",           // Default: "health-scan"
  "model": "string",              // Optional: defaults to free model
  "temperature": 0.7,             // Optional: 0.0-1.0
  "max_tokens": 2048              // Optional: max response length
}
```

**Response**:
```json
{
  "response": "string or object", // Oracle's response (can be JSON)
  "raw_response": "string",       // Always string version
  "conversation_id": "string",    // Same as input
  "user_id": "string",           // Same as input
  "category": "string",          // Same as input
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 456,
    "total_tokens": 579
  },
  "model": "tngtech/deepseek-r1t-chimera:free"
}
```

## Next.js Implementation

### 1. Install Dependencies

```bash
npm install uuid axios
# or
npm install uuid fetch
```

### 2. Create Oracle API Client

Create `lib/oracle-client.ts`:

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

### 3. Create React Hook

Create `hooks/useOracle.ts`:

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

### 4. Create Oracle Chat Component

Create `components/OracleChat.tsx`:

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

### 5. Use in Your Page

Create `app/oracle/page.tsx`:

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

## Environment Variables

Add to `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture: How FastMCP Works

### Server Architecture

The server runs **both** MCP tools and HTTP endpoints on the same port:

1. **MCP Tools** (for Claude Desktop or MCP clients):
   - Available at base URL: `http://localhost:8000`
   - Tools like `oracle_query`, `health_scan_query` are MCP protocol tools
   - Can be called via MCP protocol OR converted to HTTP by FastMCP

2. **HTTP API** (for your Next.js app):
   - Mounted at `/api/*` prefix
   - Standard REST endpoints like `/api/chat`
   - Uses FastAPI under the hood

### What Happens When You Call `/api/chat`:

1. **HTTP Request** → Your Next.js app sends POST to `/api/chat`
2. **FastAPI Handler** → `chat_endpoint()` in `api_routes.py` receives request
3. **Message Building** → `build_messages_for_llm()` checks conversation:
   - **First message**: Creates Oracle system prompt
   - **Subsequent**: Retrieves all messages from DB
4. **LLM Call** → Sends to OpenRouter with full conversation
5. **Storage** → Saves user message + assistant response
6. **Response** → Returns to your Next.js app

### MCP Tools vs HTTP Endpoints

**You are using HTTP endpoints**, not MCP tools directly:
- `/api/chat` is a regular HTTP endpoint
- It internally uses the same business logic as MCP tools
- Your Next.js app doesn't need to understand MCP protocol
- The MCP tools (`oracle_query`, etc.) are available for Claude Desktop

## How It Works

### 1. First Message
- User sends a query
- Backend checks if conversation has messages
- If no messages: Creates Oracle system prompt
- Stores system message + user message
- Returns Oracle's response

### 2. Subsequent Messages
- Retrieves full conversation history
- Adds new user message to history
- Sends complete history to LLM
- Stores both messages
- Updates conversation metadata

### 3. Conversation Management
- Each conversation has unique ID (UUID)
- Messages stored with roles: system, user, assistant
- Token counts tracked per message
- Timestamps and metadata preserved

## Testing

### 1. Quick Test Script

```bash
# Test the endpoint directly
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a persistent headache for 3 days",
    "user_id": "test-user",
    "conversation_id": "test-conv-123"
  }'
```

### 2. Test from Browser Console

```javascript
// Paste this in your browser console
fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "What could cause frequent headaches?",
    user_id: "browser-test",
    conversation_id: "browser-conv-456"
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

## Error Handling

The integration includes:
- Automatic retry with exponential backoff
- Server health checks
- Graceful error messages
- Loading states
- Network error handling

## Advanced Features

### Custom Models

```typescript
await sendMessage("My symptoms...", {
  model: "gpt-4", // Use a different model
  temperature: 0.3, // More focused responses
  maxTokens: 4096 // Longer responses
});
```

### Structured Responses

Oracle can return JSON for forms:

```typescript
// Request structured data
const response = await sendMessage(
  "Analyze my symptoms and return confidence levels",
  { category: "health-analysis" }
);

// response.response might be:
{
  "confidence_level": 0.85,
  "symptoms_identified": ["headache", "fatigue"],
  "urgency": "moderate",
  "recommendations": ["rest", "hydration", "monitor"]
}
```

## Production Considerations

1. **Authentication**: Add proper auth headers
2. **Rate Limiting**: Implement client-side rate limiting
3. **Error Logging**: Send errors to your logging service
4. **Analytics**: Track usage and response times
5. **Caching**: Consider caching health check results