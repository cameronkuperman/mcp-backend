# Frontend Health Score Implementation

## React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext'; // Your auth context

const HealthScore = () => {
  const { userId } = useAuth();
  const [scoreData, setScoreData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHealthScore();
  }, [userId]);

  const fetchHealthScore = async (forceRefresh = false) => {
    if (!userId) return;
    
    setLoading(true);
    try {
      const url = forceRefresh 
        ? `/api/health-score/${userId}?force_refresh=true`
        : `/api/health-score/${userId}`;
        
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch health score');
      }
      
      const data = await response.json();
      setScoreData(data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching health score:', err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#10B981'; // green
    if (score >= 75) return '#3B82F6'; // blue
    if (score >= 60) return '#F59E0B'; // yellow
    return '#EF4444'; // red
  };

  const getScoreCategory = (score) => {
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 60) return 'Fair';
    return 'Needs Attention';
  };

  if (loading) {
    return (
      <div className="health-score-container">
        <div className="loading-spinner">Loading health score...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="health-score-container">
        <div className="error-message">
          Unable to load health score
          <button onClick={() => fetchHealthScore()}>Retry</button>
        </div>
      </div>
    );
  }

  if (!scoreData) {
    return null;
  }

  return (
    <div className="health-score-container">
      {/* Score Display */}
      <div className="score-section">
        <h2>Your Health Score</h2>
        <div className="score-circle" style={{ borderColor: getScoreColor(scoreData.score) }}>
          <div className="score-number">{scoreData.score}</div>
          <div className="score-total">/100</div>
        </div>
        <div className="score-category" style={{ color: getScoreColor(scoreData.score) }}>
          {getScoreCategory(scoreData.score)}
        </div>
        {scoreData.reasoning && (
          <p className="score-reasoning">{scoreData.reasoning}</p>
        )}
      </div>

      {/* Today's Actions */}
      <div className="actions-section">
        <h3>Today's Actions</h3>
        <div className="actions-list">
          {scoreData.actions.map((action, index) => (
            <div key={index} className="action-item">
              <span className="action-icon">{action.icon}</span>
              <span className="action-text">{action.text}</span>
              <input type="checkbox" className="action-checkbox" />
            </div>
          ))}
        </div>
      </div>

      {/* Refresh Info */}
      <div className="refresh-section">
        {scoreData.cached && (
          <p className="cached-indicator">
            <span className="dot-indicator"></span>
            Cached result
          </p>
        )}
        <button 
          onClick={() => fetchHealthScore(true)}
          className="refresh-button"
        >
          Refresh Score
        </button>
        {scoreData.expires_at && (
          <p className="expires-text">
            Next update: {new Date(scoreData.expires_at).toLocaleString()}
          </p>
        )}
      </div>
    </div>

    
  );
};

export default HealthScore;
```

## CSS Styling

```css
.health-score-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
}

.score-section {
  text-align: center;
  margin-bottom: 30px;
}

.score-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  border: 8px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 20px auto;
  transition: border-color 0.3s ease;
}

.score-number {
  font-size: 48px;
  font-weight: bold;
  line-height: 1;
}

.score-total {
  font-size: 20px;
  color: #6B7280;
}

.score-category {
  font-size: 20px;
  font-weight: 600;
  margin-top: 10px;
}

.score-reasoning {
  color: #6B7280;
  margin-top: 10px;
  font-size: 14px;
}

.actions-section {
  margin-bottom: 30px;
}

.actions-section h3 {
  margin-bottom: 15px;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-item {
  display: flex;
  align-items: center;
  background: #F9FAFB;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
}

.action-icon {
  font-size: 24px;
  margin-right: 12px;
}

.action-text {
  flex: 1;
  font-size: 14px;
}

.action-checkbox {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.refresh-section {
  text-align: center;
}

.cached-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  font-size: 14px;
  margin-bottom: 10px;
}

.dot-indicator {
  width: 8px;
  height: 8px;
  background: #10B981;
  border-radius: 50%;
  margin-right: 8px;
}

.refresh-button {
  background: #3B82F6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.refresh-button:hover {
  background: #2563EB;
}

.expires-text {
  color: #6B7280;
  font-size: 12px;
  margin-top: 10px;
}

.loading-spinner {
  text-align: center;
  padding: 40px;
  color: #6B7280;
}

.error-message {
  text-align: center;
  padding: 40px;
  color: #EF4444;
}

.error-message button {
  margin-top: 10px;
  background: #EF4444;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
```

## TypeScript Types

```typescript
interface HealthScoreAction {
  icon: string;
  text: string;
}

interface HealthScoreResponse {
  score: number;
  actions: HealthScoreAction[];
  reasoning?: string;
  generated_at: string;
  expires_at: string;
  cached: boolean;
}
```

## Usage in Your App

```jsx
// In your main dashboard or health page
import HealthScore from './components/HealthScore';

function Dashboard() {
  return (
    <div className="dashboard">
      <h1>Health Dashboard</h1>
      <HealthScore />
      {/* Other dashboard components */}
    </div>
  );
}
```

## API Integration Notes

1. **Authentication**: Make sure to include your auth headers if required
2. **Error Handling**: The component handles basic errors, but you may want to add more specific error types
3. **Caching**: The API caches results for 24 hours. Use `force_refresh=true` to get a new score
4. **Weekly Reset**: Scores automatically reset every Monday at midnight UTC

## Example API Response

```json
{
  "score": 76,
  "actions": [
    {
      "icon": "💧",
      "text": "Increase water intake by 500ml today"
    },
    {
      "icon": "🧘",
      "text": "10-minute meditation before bed"
    },
    {
      "icon": "🚶",
      "text": "Take a 15-minute walk after lunch"
    }
  ],
  "reasoning": "Score reflects good tracking consistency with mild symptom activity",
  "generated_at": "2025-01-31T14:30:00Z",
  "expires_at": "2025-02-01T14:30:00Z",
  "cached": false
}
```