# Oracle Health AI - Frontend Tier System & Reasoning Mode Guide

## 🎯 Executive Summary

We've implemented a comprehensive tier-based model selection system with enhanced reasoning capabilities. All paid tiers get the same premium models, with differentiation happening on the frontend for features and limits.

## 📊 Subscription Tiers

### Tier Structure
1. **Free** - Chinese/open-source models (DeepSeek, free Gemini)
2. **Basic** - Premium models (GPT-5, Gemini 2.5)  
3. **Pro** - Premium models + Claude 4 Sonnet for chat
4. **Pro+** - Premium models + Claude 4 Sonnet for chat (same as Pro)

> **Important**: Basic, Pro, and Pro+ all get the same premium models. The main difference is Pro/Pro+ get Claude 4 Sonnet for chat interactions.

## 🧠 Reasoning Mode Feature

### What is Reasoning Mode?

Reasoning mode enables deeper, more thoughtful AI analysis by:
- Allocating more processing tokens (up to 8,000-12,000)
- Using specialized reasoning models when available
- Enabling step-by-step thinking for complex medical analysis

### How It Works by Tier

#### Free Tier
- **Default**: `deepseek/deepseek-chat` (fast, efficient)
- **With Reasoning**: `deepseek/deepseek-r1` (shows thinking process)
- **Token Limit**: Up to 8,000 tokens when reasoning enabled

#### Premium Tiers (Basic/Pro/Pro+)
- **Default**: Model based on endpoint (GPT-5-mini, Gemini 2.5)
- **With Reasoning**: GPT-5 with extended token limits
- **Special for Pro/Pro+**: Claude 4 Sonnet for chat (always enhanced)
- **Token Limit**: Up to 8,000-12,000 tokens when reasoning enabled

## 🔌 API Integration

### Request Format

Add `reasoning_mode` field to all applicable API requests:

```javascript
// Chat endpoint
POST /api/chat
{
  "query": "User's message",
  "user_id": "user-uuid",
  "conversation_id": "conv-uuid",
  "reasoning_mode": true  // Enable enhanced reasoning
}

// Deep Dive (always uses reasoning)
POST /api/deep-dive/start
{
  "body_part": "chest",
  "form_data": {...},
  "user_id": "user-uuid",
  "reasoning_mode": true  // Optional - always on for deep dive
}

// Flash Assessment
POST /api/flash-assessment
{
  "user_query": "symptoms description",
  "user_id": "user-uuid",
  "reasoning_mode": false  // Toggle as needed
}
```

### Response Format

Responses will include model information:

```javascript
{
  "response": "AI generated content",
  "model_used": "openai/gpt-5",
  "reasoning_tokens": 1250,  // Only for DeepSeek R1
  "usage": {
    "prompt_tokens": 500,
    "completion_tokens": 2000,
    "total_tokens": 2500
  },
  "tier": "pro",  // User's current tier
  "reasoning_mode": true  // Whether reasoning was used
}
```

## 🎨 UI/UX Implementation

### Reasoning Toggle Component

```jsx
function ReasoningToggle({ tier, enabled, onChange }) {
  // Don't show toggle for endpoints that always use reasoning
  const alwaysOn = ['deep_dive', 'reports', 'ultra_think'].includes(currentEndpoint);
  
  if (alwaysOn) {
    return (
      <div className="reasoning-always-on">
        <span className="icon">🧠</span>
        <span>Enhanced analysis active</span>
      </div>
    );
  }
  
  return (
    <div className="reasoning-toggle">
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onChange(e.target.checked)}
          className="toggle-checkbox"
        />
        <span className="font-medium">Enhanced Reasoning</span>
      </label>
      
      {/* Tier-specific messaging */}
      {tier === 'free' ? (
        <p className="text-sm text-gray-600 mt-1">
          Enable DeepSeek R1 for transparent step-by-step analysis
        </p>
      ) : (
        <p className="text-sm text-gray-600 mt-1">
          Activate extended processing for deeper medical insights
        </p>
      )}
    </div>
  );
}
```

### Model Indicator

Show users which AI model is being used:

```jsx
function ModelIndicator({ tier, endpoint, reasoningMode }) {
  const getModelName = () => {
    if (tier === 'free') {
      if (reasoningMode) return 'DeepSeek R1 (Reasoning)';
      return 'DeepSeek Chat';
    }
    
    if (tier === 'pro' || tier === 'pro_plus') {
      if (endpoint === 'chat') return 'Claude 4 Sonnet';
    }
    
    if (endpoint === 'ultra_think') return 'Grok 4 (Maximum Analysis)';
    if (endpoint === 'deep_dive') return 'GPT-5 (Deep Analysis)';
    
    return reasoningMode ? 'GPT-5 (Enhanced)' : 'GPT-5 Mini';
  };
  
  return (
    <div className="model-indicator">
      <span className="model-badge">{getModelName()}</span>
    </div>
  );
}
```

## 📋 Endpoint Behavior

### Always Use Reasoning (No Toggle)
- `/api/deep-dive/*` - All deep dive endpoints
- `/api/reports/*` - All medical reports
- `/api/ultra-think` - Maximum reasoning analysis
- `/api/health-analysis/*` - Health predictions & insights

### Optional Reasoning (Show Toggle)
- `/api/chat` - Oracle chat
- `/api/flash-assessment` - Quick health checks
- `/api/general-assessment` - General health evaluation
- `/api/quick-scan` - Body scan analysis

### Model Selection by Endpoint

| Endpoint | Free Tier | Premium Tiers | Reasoning Mode |
|----------|-----------|---------------|----------------|
| Chat | DeepSeek | Gemini 2.5 Flash / GPT-5 | DeepSeek R1 / GPT-5 |
| Chat (Pro/Pro+) | DeepSeek | Claude 4 Sonnet | DeepSeek R1 / GPT-5 |
| Quick Scan | DeepSeek | GPT-5 Mini | Always available |
| Deep Dive | DeepSeek R1 | GPT-5 | Always on |
| Ultra Think | Grok 4 | Grok 4 | Always on |
| Reports | GPT-5 | GPT-5 | Always on |
| Photo Analysis | GPT-5 | GPT-5 | Standard |

## 💰 Token Limits & Costs

### By Tier (Maximum Allowed)
- **Free**: 2,000 tokens (8,000 with reasoning)
- **Basic**: 4,000 tokens (8,000 with reasoning)
- **Pro**: 8,000 tokens (8,000 with reasoning)
- **Pro+**: 16,000 tokens (12,000 with reasoning)

> **Note**: Models don't have to use all allocated tokens - they use what they need for the task.

### Cost Implications
- Reasoning mode uses more tokens = higher cost
- DeepSeek R1 charges separately for reasoning tokens
- GPT-5 with `max_completion_tokens` may use more tokens
- Monitor usage via the `model_usage` table

## 🚀 Implementation Checklist

### Frontend Tasks

- [ ] Add `reasoning_mode` field to all API request interfaces
- [ ] Implement reasoning toggle component
- [ ] Add model indicator to show active AI
- [ ] Update loading states (reasoning takes longer)
- [ ] Add token usage display (optional)
- [ ] Test with different tier accounts
- [ ] Add reasoning explanation in UI
- [ ] Handle fallback model notifications

### Testing Scenarios

1. **Free Tier**
   - [ ] Chat without reasoning → DeepSeek Chat
   - [ ] Chat with reasoning → DeepSeek R1
   - [ ] Deep Dive → Always DeepSeek R1
   - [ ] Verify token limits

2. **Basic Tier**
   - [ ] Chat → Gemini 2.5 Flash
   - [ ] Chat with reasoning → GPT-5
   - [ ] Deep Dive → GPT-5
   - [ ] Reports → GPT-5

3. **Pro/Pro+ Tier**
   - [ ] Chat → Claude 4 Sonnet
   - [ ] Chat with reasoning → GPT-5
   - [ ] Ultra Think → Grok 4
   - [ ] Verify higher token limits

## 📊 Analytics & Monitoring

### Track Usage
The backend logs all model usage to `model_usage` table:
- Model used
- Tokens consumed (prompt, completion, reasoning)
- Response time
- Success/failure
- User tier at time of request

### Key Metrics to Monitor
- Reasoning mode adoption rate
- Average tokens per request by tier
- Model failure rates and fallbacks
- Cost per user by tier
- Response time differences

## 🔧 Troubleshooting

### Common Issues

1. **"Reasoning not available"**
   - Check if endpoint supports reasoning
   - Verify user tier allows the feature

2. **Slow responses with reasoning**
   - Normal - reasoning takes 2-5x longer
   - Show appropriate loading state

3. **Model fallback notifications**
   - Primary model failed, using backup
   - Log for monitoring but don't alarm user

4. **Token limit exceeded**
   - Reasoning mode hit max tokens
   - Response may be truncated

## 📱 Mobile Considerations

- Reasoning toggle should be easily accessible
- Consider defaulting to OFF on mobile for faster responses
- Show clear loading indicators for reasoning mode
- Optimize token usage for mobile (shorter responses)

## 🔒 Security & Privacy

- Reasoning mode doesn't affect data privacy
- All models follow same security protocols
- DeepSeek R1's reasoning is transparent (shows thinking)
- No additional PII exposure with reasoning

## 📞 Support & Communication

### User-Facing Messages

**For Free Users:**
> "Enable Enhanced Reasoning to see how Oracle thinks through your health concerns step-by-step using DeepSeek R1's transparent analysis."

**For Premium Users:**
> "Enhanced Reasoning provides deeper medical insights using extended AI processing. Oracle will take more time to thoroughly analyze your case."

**For Pro/Pro+ Users:**
> "You're using Claude 4 Sonnet, our most advanced conversational AI. Enable Enhanced Reasoning for maximum analytical depth."

### Marketing Points
- Free tier gets transparent reasoning with DeepSeek R1
- All paid tiers get premium GPT-5 and Gemini models
- Pro/Pro+ exclusive: Claude 4 Sonnet for chat
- Reasoning mode: 4x more processing power

## 🎯 Quick Reference

### API Fields
```typescript
interface RequestWithReasoning {
  // ... existing fields
  reasoning_mode?: boolean;  // Add to all requests
}

interface ResponseWithTier {
  // ... existing fields
  tier: 'free' | 'basic' | 'pro' | 'pro_plus';
  model_used: string;
  reasoning_tokens?: number;  // Only for DeepSeek R1
}
```

### Feature Flags by Tier
```javascript
const TIER_FEATURES = {
  free: {
    reasoning_toggle: true,
    max_tokens: 2000,
    reasoning_tokens: 8000,
    models: 'chinese'
  },
  basic: {
    reasoning_toggle: true,
    max_tokens: 4000,
    reasoning_tokens: 8000,
    models: 'premium'
  },
  pro: {
    reasoning_toggle: true,
    max_tokens: 8000,
    reasoning_tokens: 8000,
    models: 'premium',
    claude_chat: true
  },
  pro_plus: {
    reasoning_toggle: true,
    max_tokens: 16000,
    reasoning_tokens: 12000,
    models: 'premium',
    claude_chat: true
  }
};
```

---

## Questions? Need Help?

- Backend implementation: Check `/core/model_selector.py`
- Model configuration: See `/config/model_tiers.json`
- Frontend examples: Review `/FRONTEND_REASONING_GUIDE.md`
- SQL migrations: Run `/migrations/add_tier_system.sql`

Remember: The goal is to provide the best possible health AI experience at every tier, with clear value progression that justifies upgrades.