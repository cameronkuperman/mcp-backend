# 🧠 Health Intelligence API - Frontend Integration Guide

## Overview
The Health Intelligence system provides AI-powered health insights, predictions, pattern detection, and strategic recommendations. All intelligence is generated weekly (automatically on Mondays at 8 AM EST) or on-demand.

## 🔑 Key Features
1. **Health Insights** - Actionable patterns from your health data
2. **Shadow Patterns** - Things you stopped tracking (potentially important)
3. **Health Predictions** - Future health events based on patterns
4. **Strategic Moves** - Prioritized health optimization strategies

## 📡 API Endpoints

### 1. Generate All Intelligence (Recommended)
**POST** `/api/generate-all-intelligence/{user_id}`

Generates all 4 intelligence types in one efficient call.

```typescript
// Request
const response = await fetch(`/api/generate-all-intelligence/${userId}?force_refresh=false`, {
  method: 'POST'
});

// Response
{
  "status": "success" | "partial" | "cached" | "error",
  "data": {
    "insights": [...],
    "shadow_patterns": [...],
    "predictions": [...],
    "strategies": [...]
  },
  "counts": {
    "insights": 5,
    "shadow_patterns": 3,
    "predictions": 4,
    "strategies": 6
  },
  "errors": {
    // Only present if status is "partial"
    "predictions": "Failed to generate predictions"
  },
  "metadata": {
    "generated_at": "2025-01-31T12:00:00Z",
    "week_of": "2025-01-27",
    "cached": false,
    "generation_time_ms": 4523,
    "model_used": "moonshotai/kimi-k2",
    "component_timings": {
      "insights": 1234,
      "shadow_patterns": 1456,
      "predictions": 1023,
      "strategies": 810
    }
  }
}
```

### 2. Individual Intelligence Endpoints

#### Health Insights
**POST** `/api/generate-insights/{user_id}`

```typescript
// Response
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "user_id": "user-uuid",
      "insight_type": "positive" | "warning" | "neutral",
      "title": "Sleep Pattern Improvement",
      "description": "Your sleep quality has improved 30% over the past week...",
      "confidence": 85,
      "week_of": "2025-01-27",
      "created_at": "2025-01-31T12:00:00Z"
    }
  ],
  "count": 5,
  "metadata": {
    "generated_at": "2025-01-31T12:00:00Z",
    "model_used": "moonshotai/kimi-k2",
    "week_of": "2025-01-27",
    "generation_time_ms": 1234,
    "cached": false,
    "confidence_avg": 82,
    "context_tokens": 1500,
    "comparison_period": "2025-01-20 to 2025-01-26"
  }
}
```

#### Shadow Patterns
**POST** `/api/generate-shadow-patterns/{user_id}`

```typescript
// Response
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "user_id": "user-uuid",
      "pattern_name": "Migraine tracking",
      "pattern_category": "symptom" | "treatment" | "wellness" | "medication" | "other",
      "last_seen_description": "Last mentioned 2 weeks ago during stress period",
      "significance": "high" | "medium" | "low",
      "last_mentioned_date": "2025-01-17",
      "days_missing": 14,
      "week_of": "2025-01-27",
      "created_at": "2025-01-31T12:00:00Z"
    }
  ],
  "count": 3,
  "metadata": {
    "generated_at": "2025-01-31T12:00:00Z",
    "model_used": "moonshotai/kimi-k2",
    "week_of": "2025-01-27",
    "generation_time_ms": 1456,
    "cached": false,
    "context_tokens": 2000,
    "current_week_range": "2025-01-27 to 2025-01-31"
  }
}
```

#### Health Predictions
**POST** `/api/generate-predictions/{user_id}`

```typescript
// Response
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "user_id": "user-uuid",
      "event_description": "Increased fatigue likely if sleep pattern disrupted",
      "probability": 75,
      "timeframe": "Next 7 days",
      "preventable": true,
      "reasoning": "Based on past patterns when sleep drops below 6 hours",
      "suggested_actions": [
        "Maintain 7+ hours sleep",
        "Avoid late caffeine",
        "Use sleep tracking"
      ],
      "week_of": "2025-01-27",
      "created_at": "2025-01-31T12:00:00Z"
    }
  ],
  "count": 4,
  "metadata": {
    "generated_at": "2025-01-31T12:00:00Z",
    "model_used": "moonshotai/kimi-k2",
    "week_of": "2025-01-27",
    "generation_time_ms": 1023,
    "cached": false,
    "probability_avg": 68,
    "context_tokens": 1800,
    "analysis_period": "Last 14 days ending 2025-01-31"
  }
}
```

#### Strategic Moves
**POST** `/api/generate-strategies/{user_id}`

```typescript
// Response
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "user_id": "user-uuid",
      "strategy": "Resume daily migraine tracking to identify triggers",
      "strategy_type": "discovery" | "pattern" | "prevention" | "optimization",
      "priority": 9,  // 1-10 scale, 10 is highest
      "rationale": "Gap in tracking may be hiding important patterns",
      "expected_outcome": "Identify triggers within 2 weeks of consistent tracking",
      "week_of": "2025-01-27",
      "created_at": "2025-01-31T12:00:00Z"
    }
  ],
  "count": 6,
  "metadata": {
    "generated_at": "2025-01-31T12:00:00Z",
    "model_used": "moonshotai/kimi-k2",
    "week_of": "2025-01-27",
    "generation_time_ms": 810,
    "cached": false,
    "priority_avg": 7.2,
    "context_tokens": 2200,
    "intelligence_sources": {
      "insights": 5,
      "predictions": 4,
      "shadow_patterns": 3
    }
  }
}
```

## 🔄 Caching & Force Refresh

### Default Behavior
- Intelligence is cached for the current week
- Subsequent calls return cached data instantly
- Cache automatically expires when a new week starts

### Force Refresh
Add `?force_refresh=true` to regenerate intelligence:
```typescript
await fetch(`/api/generate-insights/${userId}?force_refresh=true`, {
  method: 'POST'
});
```

## 📅 Automatic Weekly Generation
- **When**: Every Monday at 8 AM EST
- **What**: All 4 intelligence types for all active users
- **Retry**: Automatic 3 attempts with exponential backoff
- **No user notification** - Intelligence appears seamlessly

## 🎨 Frontend Implementation Examples

### 1. Intelligence Dashboard Component
```typescript
interface IntelligenceData {
  insights: HealthInsight[];
  shadowPatterns: ShadowPattern[];
  predictions: HealthPrediction[];
  strategies: StrategicMove[];
}

const HealthIntelligenceDashboard = ({ userId }: { userId: string }) => {
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIntelligence();
  }, [userId]);

  const fetchIntelligence = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/generate-all-intelligence/${userId}?force_refresh=${forceRefresh}`,
        { method: 'POST' }
      );
      
      const data = await response.json();
      
      if (data.status === 'error') {
        throw new Error(data.error || 'Failed to generate intelligence');
      }
      
      setIntelligence(data.data);
      
      // Handle partial success
      if (data.status === 'partial' && data.errors) {
        console.warn('Some intelligence components failed:', data.errors);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="intelligence-dashboard">
      <header>
        <h2>Weekly Health Intelligence</h2>
        <button onClick={() => fetchIntelligence(true)}>
          Refresh Analysis
        </button>
      </header>
      
      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} />}
      
      {intelligence && (
        <>
          <InsightsSection insights={intelligence.insights} />
          <PredictionsSection predictions={intelligence.predictions} />
          <ShadowPatternsSection patterns={intelligence.shadowPatterns} />
          <StrategiesSection strategies={intelligence.strategies} />
        </>
      )}
    </div>
  );
};
```

### 2. Insights Display Component
```typescript
const InsightsSection = ({ insights }: { insights: HealthInsight[] }) => {
  const grouped = insights.reduce((acc, insight) => {
    if (!acc[insight.insight_type]) acc[insight.insight_type] = [];
    acc[insight.insight_type].push(insight);
    return acc;
  }, {} as Record<string, HealthInsight[]>);

  return (
    <section className="insights-section">
      <h3>Key Health Insights</h3>
      
      {grouped.positive?.length > 0 && (
        <div className="positive-insights">
          <h4>🟢 Positive Trends</h4>
          {grouped.positive.map(insight => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
      
      {grouped.warning?.length > 0 && (
        <div className="warning-insights">
          <h4>⚠️ Areas of Concern</h4>
          {grouped.warning.map(insight => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
      
      {grouped.neutral?.length > 0 && (
        <div className="neutral-insights">
          <h4>ℹ️ Observations</h4>
          {grouped.neutral.map(insight => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </section>
  );
};
```

### 3. Shadow Patterns Alert
```typescript
const ShadowPatternAlert = ({ pattern }: { pattern: ShadowPattern }) => {
  const getDaysText = (days: number) => {
    if (days === 1) return '1 day';
    if (days < 7) return `${days} days`;
    if (days < 14) return '1 week';
    if (days < 21) return '2 weeks';
    return `${Math.floor(days / 7)} weeks`;
  };

  return (
    <div className={`shadow-alert ${pattern.significance}-significance`}>
      <div className="pattern-header">
        <span className="pattern-name">{pattern.pattern_name}</span>
        <span className="days-missing">
          Not tracked for {getDaysText(pattern.days_missing)}
        </span>
      </div>
      <p className="last-seen">{pattern.last_seen_description}</p>
      {pattern.significance === 'high' && (
        <button className="resume-tracking">
          Resume Tracking
        </button>
      )}
    </div>
  );
};
```

### 4. Strategy Prioritization
```typescript
const StrategiesSection = ({ strategies }: { strategies: StrategicMove[] }) => {
  // Sort by priority (high to low)
  const sorted = [...strategies].sort((a, b) => b.priority - a.priority);
  
  return (
    <section className="strategies-section">
      <h3>Strategic Health Moves</h3>
      <div className="strategy-list">
        {sorted.map((strategy, index) => (
          <div 
            key={strategy.id} 
            className={`strategy-item priority-${strategy.priority}`}
          >
            <div className="strategy-header">
              <span className="priority-badge">
                Priority {strategy.priority}/10
              </span>
              <span className="strategy-type">
                {strategy.strategy_type}
              </span>
            </div>
            <h4>{strategy.strategy}</h4>
            <p className="rationale">{strategy.rationale}</p>
            <p className="outcome">
              <strong>Expected:</strong> {strategy.expected_outcome}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};
```

## 🏷️ TypeScript Types

```typescript
interface HealthInsight {
  id: string;
  user_id: string;
  story_id?: string | null;
  insight_type: 'positive' | 'warning' | 'neutral';
  title: string;
  description: string;
  confidence: number;
  week_of: string;
  created_at: string;
  metadata?: Record<string, any>;
}

interface ShadowPattern {
  id: string;
  user_id: string;
  pattern_name: string;
  pattern_category: 'symptom' | 'treatment' | 'wellness' | 'medication' | 'other';
  last_seen_description: string;
  significance: 'high' | 'medium' | 'low';
  last_mentioned_date?: string;
  days_missing: number;
  week_of: string;
  created_at: string;
}

interface HealthPrediction {
  id: string;
  user_id: string;
  story_id?: string | null;
  event_description: string;
  probability: number;
  timeframe: string;
  preventable: boolean;
  reasoning?: string;
  suggested_actions?: string[];
  week_of: string;
  created_at: string;
}

interface StrategicMove {
  id: string;
  user_id: string;
  strategy: string;
  strategy_type: 'discovery' | 'pattern' | 'prevention' | 'optimization';
  priority: number;  // 1-10
  rationale?: string;
  expected_outcome?: string;
  week_of: string;
  created_at: string;
  completion_status?: 'pending' | 'in_progress' | 'completed' | 'skipped';
}

interface IntelligenceResponse {
  status: 'success' | 'partial' | 'cached' | 'error' | 'no_data';
  data: any[] | IntelligenceData;
  count?: number;
  counts?: Record<string, number>;
  errors?: Record<string, string>;
  error?: string;
  message?: string;
  metadata: {
    generated_at: string;
    week_of: string;
    cached: boolean;
    model_used?: string;
    generation_time_ms?: number;
    [key: string]: any;
  };
}
```

## 🚦 Status Codes & Error Handling

### Success Responses
- **200 OK** - Intelligence generated successfully
- **status: "success"** - All components generated
- **status: "partial"** - Some components failed (check errors field)
- **status: "cached"** - Returning cached data

### Error Responses
- **status: "error"** - Complete failure
- **status: "no_data"** - User has no health data to analyze

### Example Error Handling
```typescript
const handleIntelligenceResponse = (response: IntelligenceResponse) => {
  switch (response.status) {
    case 'success':
    case 'cached':
      // Display all intelligence
      break;
      
    case 'partial':
      // Display what succeeded, show warnings for failures
      console.warn('Partial intelligence:', response.errors);
      break;
      
    case 'no_data':
      // Show onboarding or prompt to track health
      showEmptyState('Start tracking your health to get AI insights');
      break;
      
    case 'error':
      // Show error message
      showError(response.error || 'Failed to generate intelligence');
      break;
  }
};
```

## 💡 Best Practices

1. **Use Combined Endpoint**: Prefer `/generate-all-intelligence` over individual calls
2. **Cache Wisely**: Don't force refresh unless user explicitly requests
3. **Handle Partial Success**: Some components may fail while others succeed
4. **Show Loading States**: Generation can take 5-15 seconds
5. **Respect Priority**: Sort strategies by priority score
6. **Act on High Significance**: Highlight high-significance shadow patterns
7. **Time-Sensitive**: Show predictions with urgent timeframes prominently

## 🔧 Troubleshooting

### Common Issues

1. **Timeout Errors**
   - Intelligence generation can take up to 30 seconds
   - Increase client timeout to 60 seconds

2. **No Data Response**
   - User needs to track health data first
   - Check if user has recent scans/sessions

3. **Partial Failures**
   - Normal if user has limited data
   - Display what's available

4. **Stale Cache**
   - Cache persists for current week
   - Use force_refresh=true to update

### Debug Mode
Add these headers for detailed logs:
```typescript
headers: {
  'X-Debug-Mode': 'true',
  'X-Client-Version': '1.0.0'
}
```

## 📊 Analytics Tracking

Track these events for insights:
- Intelligence generation triggered (manual vs auto)
- Cache hit rate
- Component failure rate
- Time to generate
- User engagement with each intelligence type
- Strategy completion rate

---

Last Updated: 2025-01-31
Generated with Kimi K2 AI Model