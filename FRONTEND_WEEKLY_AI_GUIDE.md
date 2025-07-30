# Frontend Guide: Weekly AI Predictions System

## Overview

The AI predictions system now works **proactively**:
- Generates predictions **once a week** (default: Wednesday 5 PM)
- Generates **initial predictions** when user first downloads the app
- Stores predictions in Supabase for fast retrieval
- Users can customize their generation day/time

## New API Endpoints

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