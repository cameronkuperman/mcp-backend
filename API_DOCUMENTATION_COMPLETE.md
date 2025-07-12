# MCP Backend - Complete API Documentation & Implementation Guide

## Overview

This MCP (Model Context Protocol) backend provides a comprehensive medical consultation API with three main applications:

1. **Main API** (`api_routes.py`) - General medical chat and quick scan features
2. **LLM Summary Tools** (`llm_summary_tools.py`) - Summary generation and aggregation
3. **Oracle Server** (`run_oracle.py`) - Advanced medical consultation with deep dive analysis

## Architecture

The backend uses:
- **FastAPI** for RESTful endpoints
- **Supabase** for data persistence
- **OpenRouter** for LLM integration
- **DeepSeek** as the primary AI model
- **FastMCP** for MCP protocol support

## Complete Endpoint Reference

### 1. Main API Endpoints (`api_routes.py`)

#### POST `/chat`
**Description**: HTTP endpoint for chat with automatic conversation history management

**Request Schema**:
```typescript
interface ChatRequest {
  query: string;                    // User's question or message
  user_id: string;                  // UUID of the user
  conversation_id: string;          // UUID for conversation tracking
  category?: string;                // Default: "health-scan"
  model?: string;                   // Optional model override
  temperature?: number;             // Default: 0.7
  max_tokens?: number;              // Default: 2048
}
```

**Response Schema**:
```typescript
interface ChatResponse {
  response: string | object;        // AI response (can be JSON for structured responses)
  raw_response: string;             // Always string version of response
  conversation_id: string;          // Same as request
  user_id: string;                  // Same as request
  category: string;                 // Category used
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model: string;                    // Model actually used
}
```

**Implementation Details**:
- Fetches user medical data from Supabase
- Builds conversation context from message history
- Stores both user and assistant messages
- Updates conversation metadata (timestamps, token counts)
- Handles both text and structured JSON responses

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have been experiencing headaches for the past week",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "conversation_id": "456e7890-e89b-12d3-a456-426614174000",
    "category": "health-scan"
  }'
```

#### POST `/quick-scan`
**Description**: Quick Scan endpoint for rapid health assessment with structured analysis

**Request Schema**:
```typescript
interface QuickScanRequest {
  body_part: string;                // Body part affected (e.g., "head", "chest")
  form_data: {                      // Structured symptom data
    symptoms?: string;              // Main symptoms description
    painLevel?: number;             // 1-10 pain scale
    duration?: string;              // How long symptoms lasted
    [key: string]: any;             // Additional form fields
  };
  user_id?: string;                 // Optional for anonymous users
  model?: string;                   // Optional model override
}
```

**Response Schema**:
```typescript
interface QuickScanResponse {
  scan_id: string;                  // UUID of the scan
  analysis: {
    confidence: number;             // 0-100 confidence score
    primaryCondition: string;       // Most likely condition
    likelihood: string;             // "Very likely" | "Likely" | "Possible"
    symptoms: string[];             // Identified symptoms
    recommendations: string[];      // Action items
    urgency: 'low' | 'medium' | 'high';
    differentials: Array<{
      condition: string;
      probability: number;
    }>;
    redFlags: string[];            // Warning signs
    selfCare: string[];            // Self-care tips
  };
  body_part: string;
  confidence: number;               // Same as analysis.confidence
  user_id?: string;
  usage: object;                    // Token usage stats
  model: string;                    // Model used
}
```

**Implementation Details**:
- Generates structured medical analysis using specialized prompts
- Saves scan results to `quick_scans` table
- Tracks symptoms in `symptom_tracking` table
- Returns JSON-structured medical assessment
- Handles anonymous users (no user_id required)

**Example Request**:
```bash
curl -X POST http://localhost:8000/api/quick-scan \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "head",
    "form_data": {
      "symptoms": "Severe headache with nausea",
      "painLevel": 8,
      "duration": "2 days"
    },
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

#### POST `/prompts/{category}`
**Description**: Generate prompts for different medical categories with health data

**Request Schema**:
```typescript
interface PromptRequest {
  user_id: string;
  query: string;
  height?: number;                  // Optional health metrics
  weight?: number;
  age?: number;
  gender?: string;
  llm_context?: string;            // Optional context override
  part_selected?: string;          // Body part focus
  region?: string;                 // Geographic region
  model?: string;                  // Model preference
}
```

**Response Schema**:
```typescript
interface PromptResponse {
  category: string;                 // Category from URL
  prompt: string;                   // Generated system prompt
  user_data: object;                // Merged user data
  parameters: {
    part_selected?: string;
    region?: string;
  };
}
```

**Categories Available**:
- `health-scan`: General health consultation
- `quick-scan`: Rapid symptom assessment
- `deep-dive`: Detailed diagnostic questioning
- `deep-dive-initial`: Start deep dive session
- `deep-dive-continue`: Continue with follow-up questions
- `deep-dive-final`: Generate final analysis

#### GET `/prompts/{category}/{region}`
**Description**: Generate prompts with category and region in URL path

**Query Parameters**:
- `query` (required): The user's question
- `user_id` (required): User UUID
- `part_selected` (optional): Body part focus

**Response**: Same as POST `/prompts/{category}`

#### GET `/health`
**Description**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "service": "Medical Chat API"
}
```

#### GET `/`
**Description**: Root endpoint with API information

**Response**:
```json
{
  "message": "Oracle Medical Chat API",
  "docs": "http://localhost:8000/api/docs",
  "health": "http://localhost:8000/api/health",
  "mcp_tools": [
    "oracle_query",
    "health_scan_query",
    "quick_scan_query",
    "deep_dive_query",
    "create_llm_summary"
  ]
}
```

### 2. LLM Summary Tools Endpoints (`llm_summary_tools.py`)

#### POST `/api/generate_summary`
**Description**: Generate medical summary of conversation or quick scan

**Request Schema**:
```typescript
interface GenerateSummaryRequest {
  conversation_id?: string;         // For conversation summaries
  quick_scan_id?: string;          // For quick scan summaries
  user_id: string;                 // Required user ID
}
```

**Response Schema**:
```typescript
interface GenerateSummaryResponse {
  summary: string;                  // Generated medical summary
  type?: 'conversation' | 'quick_scan';
  scan_id?: string;                // For quick scan summaries
  token_count?: number;            // Tokens in summary
  compression_ratio?: number;      // Original/compressed ratio
  status: 'success' | 'error';
  error?: string;                  // Error message if failed
}
```

**Implementation Details**:
- For conversations: Fetches all messages, generates clinical notes
- For quick scans: Creates summary from scan data and analysis
- Uses adaptive summary length based on content size
- Stores summaries in `llm_context` table
- Deletes old summaries before inserting new ones

**Token-based Summary Sizing**:
- < 1,000 tokens: 100-token summary
- 1,000-10,000 tokens: 100-500 token summary
- 10,000-20,000 tokens: 500-750 token summary
- 20,000-100,000 tokens: 750-2000 token summary
- > 100,000 tokens: 2000 token summary max

#### POST `/api/aggregate_summaries`
**Description**: Aggregate all user's summaries with intelligent compression

**Request Schema**:
```typescript
interface AggregateSummariesRequest {
  user_id: string;
  current_query: string;           // Current context for prioritization
}
```

**Response Schema**:
```typescript
interface AggregateSummariesResponse {
  aggregated_summary: string;      // Compressed medical history
  original_token_count: number;    // Tokens before compression
  compressed_token_count: number;  // Tokens after compression
  compression_ratio: number;       // Compression factor applied
  consultations_included: number;  // Number of summaries aggregated
  model_used: string;             // Model used for aggregation
  status: 'success' | 'error';
  error?: string;
}
```

**Compression Ratios**:
- < 25,000 tokens: No compression (1.0x)
- 25,000-50,000 tokens: 1.5x compression
- 50,000-100,000 tokens: 2.0x compression
- 100,000-200,000 tokens: 5.0x compression
- 200,000-500,000 tokens: 10.0x compression
- 500,000-1,000,000 tokens: 20.0x compression
- > 1,000,000 tokens: 100.0x compression

**Model Selection**:
- Uses `google/gemini-2.0-flash-exp:free` for contexts > 200,000 tokens
- Uses `deepseek/deepseek-chat` for smaller contexts

#### GET `/api/health`
**Description**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "service": "LLM Summary Tools"
}
```

### 3. Oracle Server Endpoints (`run_oracle.py`)

#### POST `/api/chat`
**Description**: Oracle chat with real-time medical history and context integration

**Request Schema**:
```typescript
interface ChatRequest {
  query: string;
  user_id: string;
  conversation_id: string;
  category?: string;               // Default: "health-scan"
  model?: string;                  // Optional model override
}
```

**Response Schema**:
```typescript
interface ChatResponse {
  response: string;                // AI response
  raw_response: string;            // Same as response
  conversation_id: string;
  user_id: string;
  category: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model: string;
  status: 'success' | 'error';
  medical_data_loaded: boolean;    // Whether user medical data was found
  context_loaded: boolean;         // Whether LLM context was loaded
  history_count: number;           // Number of historical messages
}
```

**Key Features**:
- Integrates user's complete medical history
- Intelligent context aggregation for large histories
- References past conversations naturally
- Maintains conversation continuity
- Updates conversation metadata in real-time

#### POST `/api/generate_summary`
**Description**: Generate medical summary (same as LLM Summary Tools)

*Schema identical to LLM Summary Tools version*

#### POST `/api/quick-scan`
**Description**: Quick Scan endpoint (same as Main API)

*Schema identical to Main API version*

#### POST `/api/deep-dive/start`
**Description**: Start a Deep Dive diagnostic session with intelligent questioning

**Request Schema**:
```typescript
interface DeepDiveStartRequest {
  body_part: string;
  form_data: {
    symptoms?: string;
    [key: string]: any;
  };
  user_id?: string;                // Optional for anonymous
  model?: string;                  // Default: "deepseek/deepseek-r1-0528:free"
}
```

**Response Schema**:
```typescript
interface DeepDiveStartResponse {
  session_id: string;              // UUID for session tracking
  question: string;                // First diagnostic question
  question_number: 1;              // Always starts at 1
  estimated_questions: "2-3";      // Expected question count
  question_type: string;           // Type of question (e.g., "differential")
  status: 'success' | 'error';
}
```

#### POST `/api/deep-dive/continue`
**Description**: Continue Deep Dive with answer processing

**Request Schema**:
```typescript
interface DeepDiveContinueRequest {
  session_id: string;              // From start response
  answer: string;                  // User's answer
  question_number: number;         // Current question number
}
```

**Response Schema**:
```typescript
interface DeepDiveContinueResponse {
  // If more questions needed:
  question?: string;               // Next question
  question_number?: number;        // Next question number
  is_final_question?: boolean;     // True if this is the last question
  confidence_projection?: string;  // AI's confidence assessment
  
  // If ready for analysis:
  ready_for_analysis?: boolean;    // True when ready to complete
  questions_completed?: number;    // Total questions asked
  
  status: 'success' | 'error';
}
```

#### POST `/api/deep-dive/complete`
**Description**: Generate final Deep Dive analysis

**Request Schema**:
```typescript
interface DeepDiveCompleteRequest {
  session_id: string;
  final_answer?: string;           // Optional last answer
}
```

**Response Schema**:
```typescript
interface DeepDiveCompleteResponse {
  deep_dive_id: string;            // Same as session_id
  analysis: {
    confidence: number;            // 0-100
    primaryCondition: string;
    likelihood: string;
    symptoms: string[];
    recommendations: string[];
    urgency: 'low' | 'medium' | 'high';
    differentials: Array<{
      condition: string;
      probability: number;
    }>;
    redFlags: string[];
    selfCare: string[];
    reasoning_snippets: string[];  // AI's reasoning chain
  };
  body_part: string;
  confidence: number;              // Same as analysis.confidence
  questions_asked: number;         // Total questions in session
  reasoning_snippets: string[];    // Reasoning explanations
  usage: object;                   // Token usage
  status: 'success' | 'error';
}
```

**Deep Dive Session Flow**:
1. Start session with symptoms
2. AI asks 2-3 targeted diagnostic questions
3. Each answer refines the analysis
4. Final comprehensive analysis with reasoning

#### GET `/api/health`
**Description**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "service": "Oracle AI API"
}
```

#### GET `/`
**Description**: Root endpoint listing all available endpoints

**Response**:
```json
{
  "message": "Oracle AI Server Running",
  "endpoints": {
    "chat": "POST /api/chat",
    "health": "GET /api/health",
    "generate_summary": "POST /api/generate_summary",
    "quick_scan": "POST /api/quick-scan",
    "deep_dive": {
      "start": "POST /api/deep-dive/start",
      "continue": "POST /api/deep-dive/continue",
      "complete": "POST /api/deep-dive/complete"
    }
  }
}
```

## Database Schema

### Tables Used:

#### `messages`
- `id`: UUID
- `conversation_id`: UUID
- `role`: "user" | "assistant"
- `content`: Text
- `content_type`: "text"
- `token_count`: Integer
- `model_used`: String
- `created_at`: Timestamp

#### `conversations`
- `id`: UUID
- `user_id`: UUID
- `title`: String
- `ai_provider`: "openrouter"
- `model_name`: String
- `conversation_type`: "health_analysis"
- `status`: "active" | "completed"
- `message_count`: Integer
- `total_tokens`: Integer
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `last_message_at`: Timestamp

#### `quick_scans`
- `id`: UUID
- `user_id`: UUID
- `body_part`: String
- `form_data`: JSONB
- `analysis_result`: JSONB
- `confidence_score`: Float
- `urgency_level`: String
- `llm_summary`: Text (added by summary generation)
- `created_at`: Timestamp

#### `symptom_tracking`
- `id`: UUID
- `user_id`: UUID
- `quick_scan_id`: UUID
- `symptom_name`: String
- `body_part`: String
- `severity`: Integer
- `created_at`: Timestamp

#### `llm_context`
- `id`: UUID
- `conversation_id`: UUID (nullable for deep dives)
- `user_id`: UUID
- `llm_summary`: Text
- `created_at`: Timestamp
- `token_count`: Integer
- `original_message_count`: Integer
- `original_token_count`: Integer

#### `deep_dive_sessions`
- `id`: UUID
- `user_id`: UUID
- `body_part`: String
- `form_data`: JSONB
- `model_used`: String
- `questions`: JSONB array
- `current_step`: Integer
- `internal_state`: JSONB
- `status`: "active" | "completed"
- `created_at`: Timestamp
- `completed_at`: Timestamp
- `final_analysis`: JSONB
- `final_confidence`: Float
- `reasoning_chain`: JSONB array
- `tokens_used`: JSONB

#### `medical`
- `id`: UUID (user_id)
- User's medical history and profile data

## Authentication & Security

- **CORS**: Configured for localhost:3000 and localhost:3001
- **User Identification**: Via `user_id` parameter (UUID)
- **Anonymous Support**: Quick scans and deep dives support anonymous users
- **API Keys**: Stored in environment variables
  - `OPENROUTER_API_KEY`: For LLM access
  - `SUPABASE_URL`: Supabase project URL
  - `SUPABASE_KEY`: Supabase anon key

## Error Handling

All endpoints return consistent error responses:

```typescript
interface ErrorResponse {
  error: string;                   // Error message
  status: "error";                 // Always "error" for failures
  detail?: string;                 // Additional error details
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad Request (invalid parameters)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error

## Rate Limiting & Performance

- **Token Limits**: Configurable per endpoint
- **Context Aggregation**: Automatic for large histories
- **Caching**: 15-minute cache for web fetches
- **Timeout**: 30 seconds for LLM calls

## Deployment

### Environment Variables Required:
```bash
OPENROUTER_API_KEY=your_openrouter_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
PORT=8000  # Optional, defaults to 8000
```

### Running the Services:

1. **Main API + MCP Server**:
```bash
python mcp-backend.py
```

2. **LLM Summary Tools**:
```bash
python llm_summary_tools.py
```

3. **Oracle Server**:
```bash
python run_oracle.py
```

### Railway Deployment:
The project includes Railway deployment configuration that runs all services together.

## Integration with Frontend

### Headers Required:
```typescript
headers: {
  'Content-Type': 'application/json',
  // No authentication headers required
}
```

### Example Frontend Integration:

```typescript
// Chat endpoint
const response = await fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "I have a headache",
    user_id: userId,
    conversation_id: conversationId,
    category: "health-scan"
  })
});

// Quick Scan
const scanResponse = await fetch('http://localhost:8000/api/quick-scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    body_part: "head",
    form_data: {
      symptoms: "Migraine with aura",
      painLevel: 7,
      duration: "3 hours"
    },
    user_id: userId
  })
});

// Deep Dive Flow
// 1. Start
const startResponse = await fetch('http://localhost:8000/api/deep-dive/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    body_part: "chest",
    form_data: { symptoms: "Chest pain when breathing" },
    user_id: userId
  })
});

// 2. Continue with answers
const continueResponse = await fetch('http://localhost:8000/api/deep-dive/continue', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    answer: "The pain is sharp and gets worse with deep breaths",
    question_number: 1
  })
});

// 3. Complete for final analysis
const completeResponse = await fetch('http://localhost:8000/api/deep-dive/complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionId,
    final_answer: "No, I haven't had any recent injuries"
  })
});
```

## MCP Integration

The backend integrates with MCP (Model Context Protocol) through `mcp-backend.py`, which wraps the FastAPI application and provides the following MCP tools:

- `oracle_query`: General health consultation
- `health_scan_query`: Health scanning with context
- `quick_scan_query`: Rapid symptom assessment
- `deep_dive_query`: Detailed diagnostic analysis
- `create_llm_summary`: Generate conversation summaries

## Best Practices

1. **User IDs**: Always use valid UUIDs for user_id and conversation_id
2. **Error Handling**: Check status field in responses
3. **Token Management**: Monitor usage in responses for cost tracking
4. **Session Management**: Keep conversation_ids consistent for context
5. **Anonymous Users**: Use quick scan and deep dive without user_id for privacy
6. **Summary Generation**: Run periodically for long conversations
7. **Context Aggregation**: Automatic for histories > 25,000 tokens

## Model Configuration

Default models by endpoint:
- Chat: `deepseek/deepseek-chat`
- Quick Scan: `deepseek/deepseek-chat`
- Deep Dive: `deepseek/deepseek-r1-0528:free`
- Summaries: `deepseek/deepseek-chat`
- Large Aggregations: `google/gemini-2.0-flash-exp:free`

All endpoints accept an optional `model` parameter to override defaults.