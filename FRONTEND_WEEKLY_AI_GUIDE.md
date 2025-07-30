# Frontend Guide: Weekly AI Predictions & Health Intelligence System

## Overview

The system provides two types of AI-powered features:

### 1. Weekly AI Predictions (Existing)
- Generates predictions **once a week** (default: Wednesday 5 PM)
- Generates **initial predictions** when user first downloads the app
- Stores predictions in Supabase for fast retrieval
- Users can customize their generation day/time

### 2. Health Intelligence Analysis (NEW)
- **Key Insights**: Actionable patterns from health data
- **Health Predictions**: Wellness events likely to occur
- **Shadow Patterns**: Health topics usually mentioned but missing this week
- **Strategic Moves**: Personalized recommendations based on weekly activity

## Health Intelligence API Endpoints

### Generate Individual Components

```
POST /api/generate-insights/{user_id}
POST /api/generate-predictions/{user_id}  
POST /api/generate-shadow-patterns/{user_id}
POST /api/generate-strategies/{user_id}
```

Each endpoint generates its specific component for the current week.

### Retrieve Individual Components

```
GET /api/insights/{user_id}?week_of=2025-01-27
GET /api/predictions/{user_id}?week_of=2025-01-27
GET /api/shadow-patterns/{user_id}?week_of=2025-01-27
GET /api/strategies/{user_id}?week_of=2025-01-27
```

The `week_of` parameter is optional - defaults to current week.

### Generate Complete Analysis

```
POST /api/generate-weekly-analysis
Body: {
  "user_id": "uuid",
  "force_refresh": false,
  "include_predictions": true,
  "include_patterns": true,
  "include_strategies": true
}
```

### Get Complete Analysis

```
GET /api/health-analysis/{user_id}?week_of=2025-01-27
```

## Weekly AI Predictions Endpoints

### 1. Generate Initial Predictions (Onboarding)
```
POST /api/ai/generate-initial/{user_id}
```
Call this **once** during user onboarding/signup.

Response:
```json
{
  "status": "success",
  "prediction_id": "uuid",
  "message": "Initial predictions generated successfully"
}
```

### 2. Get Weekly Predictions (Main Endpoint)
```
GET /api/ai/weekly/{user_id}
```
Returns the current week's stored predictions.

Response:
```json
{
  "status": "success",
  "predictions": {
    "id": "uuid",
    "dashboard_alert": { /* alert object */ },
    "predictions": [ /* array of predictions */ ],
    "pattern_questions": [ /* array of questions */ ],
    "body_patterns": { /* tendencies and positiveResponses */ },
    "generated_at": "2025-01-30T17:00:00Z",
    "data_quality_score": 85,
    "is_current": true,
    "viewed_at": "2025-01-30T18:00:00Z"
  }
}
```

Status codes:
- `success`: Predictions available
- `needs_initial`: User needs initial generation
- `not_found`: No predictions yet (will generate on schedule)

### 3. Get Dashboard Alert Only
```
GET /api/ai/weekly/{user_id}/alert
```
Lightweight endpoint for dashboard - returns just the alert.

### 4. User Preferences
```
GET /api/ai/preferences/{user_id}
PUT /api/ai/preferences/{user_id}
```

Preferences object:
```json
{
  "weekly_generation_enabled": true,
  "preferred_day_of_week": 3,  // 0=Sunday, 3=Wednesday
  "preferred_hour": 17,        // 24-hour format
  "timezone": "America/New_York"
}
```

### 5. Manual Regeneration
```
POST /api/ai/regenerate/{user_id}
```
Allows user to manually trigger new predictions (rate limited: once per day).

## Health Intelligence Implementation Guide

### Display Components on Page Load

To show health intelligence components immediately when user opens the app:

```typescript
// src/hooks/useHealthIntelligence.ts
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface HealthIntelligence {
  insights: any[];
  predictions: any[];
  shadowPatterns: any[];
  strategies: any[];
  isLoading: boolean;
  isGenerating: boolean;
}

export function useHealthIntelligence(): HealthIntelligence {
  const { user } = useAuth();
  const [insights, setInsights] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [shadowPatterns, setShadowPatterns] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    // Load all components on mount
    loadHealthIntelligence();
  }, [user?.id]);

  const loadHealthIntelligence = async () => {
    setIsLoading(true);
    
    try {
      // Fetch all components in parallel
      const [insightsRes, predictionsRes, patternsRes, strategiesRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/insights/${user.id}`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/predictions/${user.id}`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/shadow-patterns/${user.id}`),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/strategies/${user.id}`)
      ]);

      const [insightsData, predictionsData, patternsData, strategiesData] = await Promise.all([
        insightsRes.json(),
        predictionsRes.json(),
        patternsRes.json(),
        strategiesRes.json()
      ]);

      setInsights(insightsData.insights || []);
      setPredictions(predictionsData.predictions || []);
      setShadowPatterns(patternsData.shadow_patterns || []);
      setStrategies(strategiesData.strategies || []);

      // If no data exists, generate it
      if (insightsData.insights?.length === 0 && 
          predictionsData.predictions?.length === 0 && 
          strategiesData.strategies?.length === 0) {
        await generateAllComponents();
      }
    } catch (error) {
      console.error('Error loading health intelligence:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateAllComponents = async () => {
    setIsGenerating(true);
    
    try {
      // Generate each component individually
      const generatePromises = [
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-insights/${user.id}`, { method: 'POST' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-predictions/${user.id}`, { method: 'POST' }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-shadow-patterns/${user.id}`, { method: 'POST' })
      ];

      const results = await Promise.all(generatePromises);
      
      // After insights, predictions, and patterns are generated, generate strategies
      if (results.every(r => r.ok)) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-strategies/${user.id}`, { method: 'POST' });
      }

      // Reload the data
      await loadHealthIntelligence();
    } catch (error) {
      console.error('Error generating components:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return {
    insights,
    predictions,
    shadowPatterns,
    strategies,
    isLoading,
    isGenerating
  };
}
```

### Dashboard Integration

```typescript
// src/components/Dashboard/HealthIntelligenceCards.tsx
import { useHealthIntelligence } from '@/hooks/useHealthIntelligence';

export function HealthIntelligenceCards() {
  const { insights, predictions, shadowPatterns, strategies, isLoading, isGenerating } = useHealthIntelligence();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white/5 rounded-xl p-6 animate-pulse">
            <div className="h-6 bg-white/10 rounded w-1/3 mb-4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-white/10 rounded"></div>
              <div className="h-4 bg-white/10 rounded w-5/6"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isGenerating) {
    return (
      <div className="bg-purple-600/20 rounded-xl p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-white">Analyzing your health data...</p>
        <p className="text-gray-400 text-sm mt-2">This may take a moment</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Key Insights */}
      <div className="bg-white/5 rounded-xl p-6">
        <h3 className="text-xl font-semibold text-white mb-4">Key Insights This Week</h3>
        <div className="space-y-3">
          {insights.map((insight, idx) => (
            <div key={idx} className={`border-l-4 pl-4 py-2 ${
              insight.insight_type === 'positive' ? 'border-green-500' :
              insight.insight_type === 'warning' ? 'border-yellow-500' :
              'border-gray-500'
            }`}>
              <h4 className="font-medium text-white">{insight.title}</h4>
              <p className="text-gray-400 text-sm">{insight.description}</p>
              <div className="text-xs text-gray-500 mt-1">
                Confidence: {insight.confidence}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Health Predictions */}
      <div className="bg-white/5 rounded-xl p-6">
        <h3 className="text-xl font-semibold text-white mb-4">Health Predictions</h3>
        <div className="space-y-3">
          {predictions.map((pred, idx) => (
            <div key={idx} className="border border-white/10 rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-medium text-white">{pred.event_description}</h4>
                <span className="text-sm text-purple-400">{pred.probability}% likely</span>
              </div>
              <p className="text-gray-400 text-sm mb-2">{pred.reasoning}</p>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">{pred.timeframe}</span>
                {pred.preventable && (
                  <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded">
                    Preventable
                  </span>
                )}
              </div>
              {pred.suggested_actions?.length > 0 && (
                <div className="mt-3 border-t border-white/10 pt-3">
                  <p className="text-xs text-gray-500 mb-1">Suggested actions:</p>
                  <ul className="list-disc list-inside text-sm text-gray-400">
                    {pred.suggested_actions.map((action, i) => (
                      <li key={i}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Shadow Patterns */}
      {shadowPatterns.length > 0 && (
        <div className="bg-yellow-500/10 rounded-xl p-6 border border-yellow-500/20">
          <h3 className="text-xl font-semibold text-yellow-400 mb-4">Not Mentioned This Week</h3>
          <p className="text-gray-400 text-sm mb-4">
            Health topics you usually track but haven't mentioned recently:
          </p>
          <div className="space-y-3">
            {shadowPatterns.map((pattern, idx) => (
              <div key={idx} className="bg-black/20 rounded-lg p-4">
                <h4 className="font-medium text-white">{pattern.pattern_name}</h4>
                <p className="text-gray-400 text-sm mt-1">{pattern.last_seen_description}</p>
                <div className="flex items-center gap-3 mt-2 text-xs">
                  <span className="text-gray-500">
                    Last mentioned: {pattern.days_missing} days ago
                  </span>
                  <span className={`px-2 py-1 rounded ${
                    pattern.significance === 'high' ? 'bg-red-500/20 text-red-400' :
                    pattern.significance === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {pattern.significance} priority
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategic Moves */}
      <div className="bg-white/5 rounded-xl p-6">
        <h3 className="text-xl font-semibold text-white mb-4">Strategic Health Moves</h3>
        <div className="space-y-3">
          {strategies.map((strategy, idx) => (
            <div key={idx} className="border border-white/10 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-white flex-1">{strategy.strategy}</h4>
                <div className="flex items-center gap-1 ml-4">
                  {Array.from({ length: Math.min(strategy.priority, 5) }).map((_, i) => (
                    <div key={i} className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  ))}
                </div>
              </div>
              <p className="text-gray-400 text-sm mb-2">{strategy.rationale}</p>
              <div className="flex items-center justify-between mt-3">
                <span className={`text-xs px-2 py-1 rounded ${
                  strategy.strategy_type === 'prevention' ? 'bg-red-500/20 text-red-400' :
                  strategy.strategy_type === 'optimization' ? 'bg-green-500/20 text-green-400' :
                  strategy.strategy_type === 'discovery' ? 'bg-blue-500/20 text-blue-400' :
                  'bg-purple-500/20 text-purple-400'
                }`}>
                  {strategy.strategy_type}
                </span>
                <span className="text-xs text-gray-500">
                  Expected: {strategy.expected_outcome}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### Add to Main Dashboard

```typescript
// src/pages/dashboard/index.tsx
import { HealthIntelligenceCards } from '@/components/Dashboard/HealthIntelligenceCards';

export default function Dashboard() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-white mb-8">Your Health Dashboard</h1>
      
      {/* Weekly AI Alert (existing) */}
      <WeeklyAIAlert />
      
      {/* Health Intelligence Components (new) */}
      <div className="mt-8">
        <h2 className="text-2xl font-semibold text-white mb-6">
          This Week's Health Intelligence
        </h2>
        <HealthIntelligenceCards />
      </div>
      
      {/* Rest of dashboard components */}
    </div>
  );
}
```

### Generate Components One by One (Progressive Loading)

For better UX, you can load and display components as they're generated:

```typescript
// src/hooks/useProgressiveHealthIntelligence.ts
export function useProgressiveHealthIntelligence() {
  const { user } = useAuth();
  const [components, setComponents] = useState({
    insights: { data: [], loading: true, generated: false },
    predictions: { data: [], loading: true, generated: false },
    shadowPatterns: { data: [], loading: true, generated: false },
    strategies: { data: [], loading: true, generated: false }
  });

  useEffect(() => {
    if (!user?.id) return;
    loadComponentsProgressively();
  }, [user?.id]);

  const loadComponentsProgressively = async () => {
    // Load insights first
    await loadComponent('insights', '/api/insights/', '/api/generate-insights/');
    
    // Then predictions
    await loadComponent('predictions', '/api/predictions/', '/api/generate-predictions/');
    
    // Then shadow patterns
    await loadComponent('shadowPatterns', '/api/shadow-patterns/', '/api/generate-shadow-patterns/');
    
    // Finally strategies (needs other components)
    await loadComponent('strategies', '/api/strategies/', '/api/generate-strategies/');
  };

  const loadComponent = async (name: string, getUrl: string, generateUrl: string) => {
    try {
      // Try to get existing data
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${getUrl}${user.id}`);
      const data = await response.json();
      
      const hasData = data[name]?.length > 0 || 
                     data[name.replace(/([A-Z])/g, '_$1').toLowerCase()]?.length > 0;
      
      if (hasData) {
        setComponents(prev => ({
          ...prev,
          [name]: { 
            data: data[name] || data[name.replace(/([A-Z])/g, '_$1').toLowerCase()], 
            loading: false, 
            generated: true 
          }
        }));
      } else {
        // Generate if no data
        const genResponse = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}${generateUrl}${user.id}`,
          { method: 'POST' }
        );
        
        if (genResponse.ok) {
          const genData = await genResponse.json();
          setComponents(prev => ({
            ...prev,
            [name]: { 
              data: genData[name] || [], 
              loading: false, 
              generated: true 
            }
          }));
        }
      }
    } catch (error) {
      console.error(`Error loading ${name}:`, error);
      setComponents(prev => ({
        ...prev,
        [name]: { ...prev[name], loading: false }
      }));
    }
  };

  return components;
}
```

## Implementation Guide

### Step 1: Update Onboarding Flow

During user signup/onboarding:

```typescript
// src/components/onboarding/SetupComplete.tsx
const completeOnboarding = async () => {
  try {
    // ... existing onboarding steps ...
    
    // Generate initial AI predictions
    setLoadingMessage("Analyzing your health profile...");
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/ai/generate-initial/${user.id}`,
      { method: 'POST' }
    );
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        // Predictions generated successfully
        toast.success("Your personalized insights are ready!");
      }
    }
    
    // Continue to dashboard
    router.push('/dashboard');
  } catch (error) {
    console.error('Onboarding error:', error);
    // Don't block onboarding if predictions fail
    router.push('/dashboard');
  }
};
```

### Step 2: Update Dashboard Hook

Replace the polling hook with one that fetches stored predictions:

```typescript
// src/hooks/useWeeklyAIPredictions.ts
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export function useWeeklyAIPredictions() {
  const { user } = useAuth();
  const [predictions, setPredictions] = useState<WeeklyPredictions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<'success' | 'needs_initial' | 'not_found'>('success');

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchPredictions = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/weekly/${user.id}`
        );
        
        const data = await response.json();
        setStatus(data.status);
        
        if (data.status === 'success' && data.predictions) {
          setPredictions(data.predictions);
        } else if (data.status === 'needs_initial') {
          // Trigger initial generation
          await generateInitialPredictions(user.id);
        }
      } catch (error) {
        console.error('Error fetching predictions:', error);
        setStatus('not_found');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPredictions();
  }, [user?.id]);

  const generateInitialPredictions = async (userId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/ai/generate-initial/${userId}`,
        { method: 'POST' }
      );
      
      if (response.ok) {
        // Reload predictions after generation
        window.location.reload();
      }
    } catch (error) {
      console.error('Error generating initial predictions:', error);
    }
  };

  return { predictions, isLoading, status };
}
```

### Step 3: Update Dashboard Alert

```typescript
// src/hooks/useWeeklyDashboardAlert.ts
export function useWeeklyDashboardAlert() {
  const { user } = useAuth();
  const [alert, setAlert] = useState<AIAlert | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user?.id) {
      setIsLoading(false);
      return;
    }

    const fetchAlert = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/ai/weekly/${user.id}/alert`
        );
        
        const data = await response.json();
        setAlert(data.alert);
      } catch (error) {
        console.error('Error fetching alert:', error);
        setAlert(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlert();
  }, [user?.id]);

  return { alert, isLoading };
}
```

### Step 4: Add Preferences UI

Create a settings component for AI preferences:

```typescript
// src/components/settings/AIPreferences.tsx
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const DAYS_OF_WEEK = [
  { value: 0, label: 'Sunday' },
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' }
];

export function AIPreferences() {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState({
    weekly_generation_enabled: true,
    preferred_day_of_week: 3,
    preferred_hour: 17,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchPreferences();
  }, [user?.id]);

  const fetchPreferences = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/ai/preferences/${user.id}`
      );
      const data = await response.json();
      if (data.preferences) {
        setPreferences(data.preferences);
      }
    } catch (error) {
      console.error('Error fetching preferences:', error);
    }
  };

  const savePreferences = async () => {
    try {
      setIsSaving(true);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/ai/preferences/${user.id}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(preferences)
        }
      );
      
      if (response.ok) {
        toast.success('Preferences saved successfully!');
      }
    } catch (error) {
      console.error('Error saving preferences:', error);
      toast.error('Failed to save preferences');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white/5 rounded-xl p-6">
      <h3 className="text-xl font-semibold text-white mb-4">
        AI Predictions Schedule
      </h3>
      
      <div className="space-y-4">
        <div>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={preferences.weekly_generation_enabled}
              onChange={(e) => setPreferences({
                ...preferences,
                weekly_generation_enabled: e.target.checked
              })}
              className="w-4 h-4 rounded"
            />
            <span className="text-gray-300">
              Generate weekly health predictions
            </span>
          </label>
        </div>

        {preferences.weekly_generation_enabled && (
          <>
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Generation Day
              </label>
              <select
                value={preferences.preferred_day_of_week}
                onChange={(e) => setPreferences({
                  ...preferences,
                  preferred_day_of_week: parseInt(e.target.value)
                })}
                className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white"
              >
                {DAYS_OF_WEEK.map(day => (
                  <option key={day.value} value={day.value}>
                    {day.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Generation Time
              </label>
              <select
                value={preferences.preferred_hour}
                onChange={(e) => setPreferences({
                  ...preferences,
                  preferred_hour: parseInt(e.target.value)
                })}
                className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white"
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>
                    {i === 0 ? '12:00 AM' : 
                     i < 12 ? `${i}:00 AM` : 
                     i === 12 ? '12:00 PM' : 
                     `${i - 12}:00 PM`}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Timezone
              </label>
              <input
                type="text"
                value={preferences.timezone}
                readOnly
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-gray-400"
              />
            </div>
          </>
        )}

        <button
          onClick={savePreferences}
          disabled={isSaving}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white rounded-lg py-2 transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
}
```

### Step 5: Add Manual Regeneration

In your predictive insights page:

```typescript
const handleRegenerate = async () => {
  try {
    setIsRegenerating(true);
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/ai/regenerate/${user.id}`,
      { method: 'POST' }
    );
    
    const data = await response.json();
    
    if (data.status === 'success') {
      toast.success('Predictions regenerated successfully!');
      // Reload the page to show new predictions
      window.location.reload();
    } else if (data.status === 'rate_limited') {
      toast.error(data.message);
    } else {
      toast.error('Failed to regenerate predictions');
    }
  } catch (error) {
    console.error('Error regenerating:', error);
    toast.error('An error occurred');
  } finally {
    setIsRegenerating(false);
  }
};

// In the UI
<button
  onClick={handleRegenerate}
  disabled={isRegenerating}
  className="text-sm text-purple-400 hover:text-purple-300"
>
  {isRegenerating ? 'Regenerating...' : 'Refresh Predictions'}
</button>
```

## Data Flow Summary

1. **User Signs Up** → Initial predictions generated
2. **Every Week** → New predictions generated automatically
3. **Dashboard Opens** → Fetches stored alert (fast)
4. **Insights Page** → Fetches all stored predictions (fast)
5. **Manual Refresh** → User can regenerate once per day

## Benefits of This Approach

1. **Fast Loading**: No waiting for AI generation on page load
2. **Cost Efficient**: AI runs once per week per user
3. **Always Fresh**: Users get new insights weekly
4. **Customizable**: Users can choose their preferred day/time
5. **Reliable**: Background jobs ensure predictions are ready

## Testing

```bash
# Test initial generation
curl -X POST http://localhost:8000/api/ai/generate-initial/test-user-123

# Get weekly predictions
curl http://localhost:8000/api/ai/weekly/test-user-123

# Get just the alert
curl http://localhost:8000/api/ai/weekly/test-user-123/alert

# Update preferences
curl -X PUT http://localhost:8000/api/ai/preferences/test-user-123 \
  -H "Content-Type: application/json" \
  -d '{
    "weekly_generation_enabled": true,
    "preferred_day_of_week": 5,
    "preferred_hour": 18,
    "timezone": "America/New_York"
  }'
```

## Migration Notes

1. Run the database migration first: `005_weekly_ai_predictions.sql`
2. The system will automatically generate predictions for active users
3. Existing users will get predictions on the next scheduled run
4. New users get predictions immediately during onboarding

## Testing Health Intelligence Endpoints

### Generate Components Individually

```bash
# Generate insights only
curl -X POST https://web-production-945c4.up.railway.app/api/generate-insights/YOUR_USER_ID

# Generate predictions only  
curl -X POST https://web-production-945c4.up.railway.app/api/generate-predictions/YOUR_USER_ID

# Generate shadow patterns only
curl -X POST https://web-production-945c4.up.railway.app/api/generate-shadow-patterns/YOUR_USER_ID

# Generate strategies only (requires other components to exist)
curl -X POST https://web-production-945c4.up.railway.app/api/generate-strategies/YOUR_USER_ID
```

### Retrieve Components

```bash
# Get insights
curl https://web-production-945c4.up.railway.app/api/insights/YOUR_USER_ID

# Get predictions
curl https://web-production-945c4.up.railway.app/api/predictions/YOUR_USER_ID

# Get shadow patterns  
curl https://web-production-945c4.up.railway.app/api/shadow-patterns/YOUR_USER_ID

# Get strategies
curl https://web-production-945c4.up.railway.app/api/strategies/YOUR_USER_ID
```

### Generate Complete Analysis

```bash
# Generate all components at once
curl -X POST https://web-production-945c4.up.railway.app/api/generate-weekly-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "force_refresh": false,
    "include_predictions": true,
    "include_patterns": true,
    "include_strategies": true
  }'
```

### Example Response Structure

```json
{
  "status": "success",
  "insights": [
    {
      "id": "uuid",
      "insight_type": "positive",
      "title": "Sleep Pattern Improvement",
      "description": "Your sleep tracking shows consistent 7-8 hour patterns this week",
      "confidence": 85,
      "created_at": "2025-01-30T10:00:00Z"
    }
  ],
  "predictions": [
    {
      "id": "uuid",
      "event_description": "Energy levels likely to improve",
      "probability": 75,
      "timeframe": "Next few days",
      "preventable": false,
      "reasoning": "Better sleep patterns typically lead to increased energy",
      "suggested_actions": ["Maintain current sleep schedule"]
    }
  ],
  "shadow_patterns": [
    {
      "id": "uuid",
      "pattern_name": "Morning exercise routine",
      "pattern_category": "exercise",
      "last_seen_description": "Usually tracked 5x per week",
      "significance": "high",
      "days_missing": 7
    }
  ],
  "strategies": [
    {
      "id": "uuid",
      "strategy": "Since you tracked knee pain twice, log activities before pain episodes",
      "strategy_type": "discovery",
      "priority": 8,
      "rationale": "Identifying triggers helps prevent future pain",
      "expected_outcome": "Better understanding of pain triggers"
    }
  ]
}