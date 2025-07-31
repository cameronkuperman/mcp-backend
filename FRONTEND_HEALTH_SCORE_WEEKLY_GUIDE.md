# Frontend Health Score Weekly Comparison Guide

## Overview
The backend now automatically calculates health scores for all users every Monday at midnight UTC. Scores are kept for 2 weeks, allowing you to show comparisons with the previous week.

## API Changes

### GET `/api/health-score/{user_id}`
The response now includes data that enables weekly comparisons:

```json
{
  "score": 76,
  "actions": [
    {"icon": "💧", "text": "Increase water intake by 500ml today"},
    {"icon": "🧘", "text": "10-minute meditation before bed"},
    {"icon": "🚶", "text": "Take a 15-minute walk after lunch"}
  ],
  "reasoning": "Score reflects good tracking consistency with mild symptom activity",
  "generated_at": "2025-01-27T00:00:00Z",  // This Monday
  "expires_at": "2025-01-28T00:00:00Z",
  "cached": true
}
```

## Getting Previous Week's Score

To show week-over-week comparison, you'll need to query Supabase directly:

```javascript
// In your HealthScore component
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const getPreviousWeekScore = async (userId) => {
  // Get last Monday's date
  const today = new Date();
  const currentMonday = new Date(today);
  currentMonday.setDate(today.getDate() - today.getDay() + 1);
  currentMonday.setHours(0, 0, 0, 0);
  
  const lastMonday = new Date(currentMonday);
  lastMonday.setDate(lastMonday.getDate() - 7);
  
  const { data, error } = await supabase
    .from('health_scores')
    .select('score, created_at')
    .eq('user_id', userId)
    .gte('created_at', lastMonday.toISOString())
    .lt('created_at', currentMonday.toISOString())
    .order('created_at', { ascending: false })
    .limit(1);
    
  return data?.[0]?.score || null;
};
```

## Enhanced React Component

```jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const HealthScoreWithComparison = () => {
  const { userId } = useAuth();
  const [currentScore, setCurrentScore] = useState(null);
  const [previousScore, setPreviousScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trend, setTrend] = useState(null); // 'up', 'down', 'same', or null

  useEffect(() => {
    if (userId) {
      fetchHealthData();
    }
  }, [userId]);

  const fetchHealthData = async () => {
    setLoading(true);
    try {
      // Fetch current score
      const currentResponse = await fetch(`/api/health-score/${userId}`);
      const currentData = await currentResponse.json();
      setCurrentScore(currentData);

      // Fetch previous week's score
      const prevScore = await getPreviousWeekScore(userId);
      setPreviousScore(prevScore);

      // Calculate trend
      if (prevScore !== null && currentData.score) {
        if (currentData.score > prevScore) setTrend('up');
        else if (currentData.score < prevScore) setTrend('down');
        else setTrend('same');
      }
    } catch (error) {
      console.error('Error fetching health data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPreviousWeekScore = async (userId) => {
    const today = new Date();
    const currentMonday = new Date(today);
    currentMonday.setDate(today.getDate() - today.getDay() + 1);
    currentMonday.setHours(0, 0, 0, 0);
    
    const lastMonday = new Date(currentMonday);
    lastMonday.setDate(lastMonday.getDate() - 7);
    
    const { data, error } = await supabase
      .from('health_scores')
      .select('score')
      .eq('user_id', userId)
      .gte('created_at', lastMonday.toISOString())
      .lt('created_at', currentMonday.toISOString())
      .order('created_at', { ascending: false })
      .limit(1);
      
    return data?.[0]?.score || null;
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    if (trend === 'same') return '➡️';
    return '';
  };

  const getTrendColor = () => {
    if (trend === 'up') return '#10B981';
    if (trend === 'down') return '#EF4444';
    return '#6B7280';
  };

  const getScoreDifference = () => {
    if (previousScore === null || !currentScore) return null;
    return currentScore.score - previousScore;
  };

  if (loading) {
    return <div className="loading">Loading health score...</div>;
  }

  if (!currentScore) {
    return <div className="error">Unable to load health score</div>;
  }

  return (
    <div className="health-score-container">
      {/* Main Score */}
      <div className="score-section">
        <h2>Your Health Score</h2>
        <div className="score-display">
          <div className="score-number">{currentScore.score}</div>
          <div className="score-total">/100</div>
        </div>

        {/* Weekly Comparison */}
        {previousScore !== null && (
          <div className="weekly-comparison">
            <div className="trend-indicator" style={{ color: getTrendColor() }}>
              <span className="trend-icon">{getTrendIcon()}</span>
              <span className="trend-text">
                {trend === 'up' && `+${getScoreDifference()} from last week`}
                {trend === 'down' && `${getScoreDifference()} from last week`}
                {trend === 'same' && 'Same as last week'}
              </span>
            </div>
            <div className="comparison-details">
              Last week: {previousScore} → This week: {currentScore.score}
            </div>
          </div>
        )}

        {currentScore.reasoning && (
          <p className="score-reasoning">{currentScore.reasoning}</p>
        )}
      </div>

      {/* Today's Actions */}
      <div className="actions-section">
        <h3>Today's Actions</h3>
        <div className="actions-list">
          {currentScore.actions.map((action, index) => (
            <ActionItem key={index} action={action} />
          ))}
        </div>
      </div>

      {/* Score History Chart (Optional) */}
      <ScoreHistoryMini userId={userId} />
    </div>
  );
};

// Mini chart component showing 2-week trend
const ScoreHistoryMini = ({ userId }) => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchScoreHistory();
  }, [userId]);

  const fetchScoreHistory = async () => {
    const twoWeeksAgo = new Date();
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14);

    const { data } = await supabase
      .from('health_scores')
      .select('score, created_at')
      .eq('user_id', userId)
      .gte('created_at', twoWeeksAgo.toISOString())
      .order('created_at', { ascending: true });

    if (data) {
      setHistory(data);
    }
  };

  if (history.length < 2) return null;

  return (
    <div className="score-history-mini">
      <h4>2-Week Trend</h4>
      <div className="mini-chart">
        {history.map((entry, index) => (
          <div key={index} className="chart-bar">
            <div 
              className="bar-fill" 
              style={{ height: `${entry.score}%` }}
            />
            <span className="bar-label">
              {new Date(entry.created_at).toLocaleDateString('en', { 
                month: 'short', 
                day: 'numeric' 
              })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const ActionItem = ({ action }) => {
  const [completed, setCompleted] = useState(false);

  return (
    <div className={`action-item ${completed ? 'completed' : ''}`}>
      <span className="action-icon">{action.icon}</span>
      <span className="action-text">{action.text}</span>
      <input 
        type="checkbox" 
        checked={completed}
        onChange={(e) => setCompleted(e.target.checked)}
      />
    </div>
  );
};

export default HealthScoreWithComparison;
```

## Additional CSS for Weekly Comparison

```css
.weekly-comparison {
  margin-top: 20px;
  padding: 15px;
  background: #F9FAFB;
  border-radius: 8px;
}

.trend-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.trend-icon {
  font-size: 24px;
  margin-right: 8px;
}

.comparison-details {
  font-size: 14px;
  color: #6B7280;
  text-align: center;
}

.score-history-mini {
  margin-top: 30px;
  padding: 20px;
  background: #F9FAFB;
  border-radius: 8px;
}

.mini-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 100px;
  margin-top: 15px;
}

.chart-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 5px;
}

.bar-fill {
  width: 100%;
  background: #3B82F6;
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
}

.bar-label {
  font-size: 11px;
  color: #6B7280;
  margin-top: 5px;
  text-align: center;
}

.action-item.completed {
  opacity: 0.6;
}

.action-item.completed .action-text {
  text-decoration: line-through;
}
```

## Implementation Tips

1. **Initial Load**: When a user first uses the feature, they won't have a previous week's score. Handle this gracefully.

2. **Timezone Considerations**: Scores are generated at UTC midnight on Mondays. Consider showing "New score available!" notifications.

3. **Caching**: The current week's score is cached for 24 hours. Previous weeks' scores don't change, so you can cache them locally.

4. **Real-time Updates**: Consider using Supabase real-time subscriptions to show when new scores are available:

```javascript
// Subscribe to new scores
const subscription = supabase
  .channel('health-scores')
  .on('postgres_changes', 
    { 
      event: 'INSERT', 
      schema: 'public', 
      table: 'health_scores',
      filter: `user_id=eq.${userId}`
    }, 
    (payload) => {
      // New score available, refresh the display
      fetchHealthData();
    }
  )
  .subscribe();
```

5. **Loading States**: Show skeleton loaders while fetching both current and previous scores.

6. **Error Handling**: Handle cases where Supabase queries fail or return no data.

## Benefits for Users

- **Progress Tracking**: Users can see if their health habits are improving
- **Motivation**: Positive trends encourage continued engagement
- **Insights**: Week-over-week changes help identify what's working
- **Automatic Updates**: Fresh scores every Monday without manual refresh