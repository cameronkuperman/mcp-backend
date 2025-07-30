# Frontend AI Predictions Implementation Guide

## Backend API Endpoints Available

The backend AI predictions module is now ready with the following endpoints:

### 1. Dashboard Alert Endpoint
```
GET /api/ai/dashboard-alert/{user_id}
```
Returns:
```json
{
  "alert": {
    "id": "uuid",
    "severity": "info|warning|critical",
    "title": "Brief alert title",
    "description": "Detailed description",
    "timeframe": "Next 48 hours",
    "confidence": 85,
    "actionUrl": "/predictive-insights?focus=uuid",
    "preventionTip": "Optional quick tip",
    "generated_at": "2025-01-30T..."
  }
}
```

### 2. AI Predictions Endpoint
```
GET /api/ai/predictions/{user_id}
```
Returns:
```json
{
  "predictions": [
    {
      "id": "uuid",
      "type": "immediate|seasonal|longterm",
      "severity": "info|warning|alert",
      "title": "Prediction title",
      "description": "Detailed description",
      "pattern": "Pattern detected",
      "confidence": 75,
      "preventionProtocols": ["Action 1", "Action 2"],
      "category": "migraine|sleep|energy|mood|stress|other",
      "reasoning": "Optional AI reasoning",
      "dataPoints": ["Optional data points"],
      "gradient": "from-blue-600/10 to-cyan-600/10",
      "generated_at": "2025-01-30T..."
    }
  ],
  "generated_at": "2025-01-30T...",
  "data_quality_score": 85
}
```

### 3. Pattern Questions Endpoint
```
GET /api/ai/pattern-questions/{user_id}
```
Returns:
```json
{
  "questions": [
    {
      "id": "uuid",
      "question": "Why do I always feel tired on Wednesdays?",
      "category": "sleep|energy|mood|physical|other",
      "answer": "Brief answer",
      "deepDive": ["Insight 1", "Insight 2", "..."],
      "connections": ["Related pattern 1", "Related pattern 2"],
      "relevanceScore": 85,
      "basedOn": ["Data point 1", "Data point 2"]
    }
  ],
  "generated_at": "2025-01-30T..."
}
```

### 4. Body Patterns Endpoint
```
GET /api/ai/body-patterns/{user_id}
```
Returns:
```json
{
  "patterns": {
    "tendencies": [
      "Get migraines 48-72 hours after high stress events",
      "Sleep quality decreases when screen time exceeds 8 hours"
    ],
    "positiveResponses": [
      "Sleep quality improves with 30min morning walks",
      "Energy levels increase with regular meal times"
    ]
  },
  "lastUpdated": "2025-01-30T...",
  "dataPoints": 150
}
```

## Frontend Implementation Steps

### Step 1: Create the Hooks

#### 1.1 useAIPredictiveAlert Hook
Create `src/hooks/useAIPredictiveAlert.ts`:

```typescript
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface AIAlert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  timeframe: string;
  confidence: number;
  actionUrl: string;
  preventionTip?: string;
}

export function useAIPredictiveAlert() {
  const { user } = useAuth();
  const [alert, setAlert] = useState<AIAlert | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchAlert = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/dashboard-alert/${user.id}`
        );
        
        if (!response.ok) throw new Error('Failed to fetch alert');
        
        const data = await response.json();
        
        if (data.alert) {
          setAlert(data.alert);
          setLastUpdate(new Date());
        } else {
          setAlert(null);
        }
      } catch (error) {
        console.error('Error fetching AI alert:', error);
        setAlert(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlert();
    const interval = setInterval(fetchAlert, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user?.id]);

  return { alert, isLoading, lastUpdate };
}
```

#### 1.2 useAIPredictions Hook
Create `src/hooks/useAIPredictions.ts`:

```typescript
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export interface AIPrediction {
  id: string;
  type: 'immediate' | 'seasonal' | 'longterm';
  severity: 'info' | 'warning' | 'alert';
  title: string;
  description: string;
  pattern: string;
  confidence: number;
  preventionProtocols: string[];
  category: string;
  reasoning?: string;
  dataPoints?: string[];
  gradient?: string;
  generated_at: string;
}

export function useAIPredictions() {
  const { user } = useAuth();
  const [predictions, setPredictions] = useState<AIPrediction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchPredictions = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/predictions/${user.id}`
        );

        if (!response.ok) throw new Error('Failed to fetch predictions');

        const data = await response.json();
        setPredictions(data.predictions || []);
      } catch (err) {
        setError(err as Error);
        console.error('Error fetching AI predictions:', err);
        setPredictions([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPredictions();
    const interval = setInterval(fetchPredictions, 60 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user?.id]);

  return { predictions, isLoading, error };
}
```

#### 1.3 useAIPatternQuestions Hook
Create `src/hooks/useAIPatternQuestions.ts`:

```typescript
export interface AIPatternQuestion {
  id: string;
  question: string;
  category: 'sleep' | 'energy' | 'mood' | 'physical' | 'other';
  answer: string;
  deepDive: string[];
  connections: string[];
  relevanceScore: number;
  basedOn: string[];
}

export function useAIPatternQuestions() {
  const { user } = useAuth();
  const [questions, setQuestions] = useState<AIPatternQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const generateQuestions = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/pattern-questions/${user.id}`
        );

        if (!response.ok) throw new Error('Failed to generate questions');

        const data = await response.json();
        const sortedQuestions = (data.questions || []).sort(
          (a: any, b: any) => b.relevanceScore - a.relevanceScore
        );
        setQuestions(sortedQuestions);
      } catch (error) {
        console.error('Error generating pattern questions:', error);
        setQuestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    generateQuestions();
  }, [user?.id]);

  return { questions, isLoading };
}
```

#### 1.4 useAIBodyPatterns Hook
Create `src/hooks/useAIBodyPatterns.ts`:

```typescript
interface BodyPatterns {
  tendencies: string[];
  positiveResponses: string[];
}

export function useAIBodyPatterns() {
  const { user } = useAuth();
  const [patterns, setPatterns] = useState<BodyPatterns | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchPatterns = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/body-patterns/${user.id}`
        );

        if (!response.ok) throw new Error('Failed to fetch body patterns');

        const data = await response.json();
        setPatterns(data.patterns);
      } catch (error) {
        console.error('Error fetching body patterns:', error);
        setPatterns(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPatterns();
  }, [user?.id]);

  return { patterns, isLoading };
}
```

### Step 2: Update Dashboard Component

In your dashboard page, replace the static alert with the AI-powered one:

```typescript
import { useAIPredictiveAlert } from '@/hooks/useAIPredictiveAlert';
import { AlertTriangle, Zap, TrendingUp, Shield } from 'lucide-react';

// Inside your Dashboard component
const { alert: aiAlert, isLoading: alertLoading } = useAIPredictiveAlert();

// In the render:
{alertLoading ? (
  <AlertLoadingSkeleton />
) : aiAlert ? (
  <AIAlertCard alert={aiAlert} />
) : (
  <NoAlertsCard />
)}
```

### Step 3: Update Predictive Insights Page

Update your predictive insights page to use the AI hooks:

```typescript
import { useAIPredictions } from '@/hooks/useAIPredictions';
import { useAIPatternQuestions } from '@/hooks/useAIPatternQuestions';
import { useAIBodyPatterns } from '@/hooks/useAIBodyPatterns';

export default function PredictiveInsightsPage() {
  const { predictions, isLoading: predictionsLoading } = useAIPredictions();
  const { questions, isLoading: questionsLoading } = useAIPatternQuestions();
  const { patterns: bodyPatterns, isLoading: patternsLoading } = useAIBodyPatterns();
  
  // Filter predictions by type
  const immediatePredictions = predictions.filter(p => p.type === 'immediate');
  const seasonalPredictions = predictions.filter(p => p.type === 'seasonal');
  const longtermPredictions = predictions.filter(p => p.type === 'longterm');
  
  // Render your UI with the AI data
}
```

### Step 4: Create Component Files

Create these component files in your project:

1. `src/components/predictive/AIAlertCard.tsx`
2. `src/components/predictive/PredictionCard.tsx`
3. `src/components/predictive/PatternQuestionCard.tsx`
4. `src/components/predictive/PatternDeepDive.tsx`
5. `src/components/predictive/PredictionsLoadingSkeleton.tsx`
6. `src/components/predictive/EmptyPredictionsState.tsx`

### Step 5: Add Caching Layer

Create `src/lib/aiCache.ts`:

```typescript
class AICache {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly TTL = 30 * 60 * 1000; // 30 minutes

  async get<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    const cached = this.cache.get(key);
    const now = Date.now();
    
    if (cached && now - cached.timestamp < (ttl || this.TTL)) {
      return cached.data as T;
    }

    try {
      const data = await fetcher();
      this.cache.set(key, { data, timestamp: now });
      return data;
    } catch (error) {
      if (cached) {
        console.warn('Using stale cache due to fetch error:', error);
        return cached.data as T;
      }
      throw error;
    }
  }

  invalidate(pattern?: string) {
    if (pattern) {
      for (const key of this.cache.keys()) {
        if (key.includes(pattern)) {
          this.cache.delete(key);
        }
      }
    } else {
      this.cache.clear();
    }
  }
}

export const aiCache = new AICache();
```

## Testing the Implementation

1. **Test Dashboard Alert**:
   ```bash
   curl http://localhost:8000/api/ai/dashboard-alert/YOUR_USER_ID
   ```

2. **Test Predictions**:
   ```bash
   curl http://localhost:8000/api/ai/predictions/YOUR_USER_ID
   ```

3. **Test Pattern Questions**:
   ```bash
   curl http://localhost:8000/api/ai/pattern-questions/YOUR_USER_ID
   ```

4. **Test Body Patterns**:
   ```bash
   curl http://localhost:8000/api/ai/body-patterns/YOUR_USER_ID
   ```

## Environment Variables

Make sure your frontend has:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Next Steps

1. Run the database migration to create the AI tables
2. Test each endpoint with your user ID
3. Implement the frontend hooks
4. Update your dashboard and predictive insights pages
5. Test the full integration

The backend is now ready and waiting for the frontend implementation!