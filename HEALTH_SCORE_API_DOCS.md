# Health Score API Documentation

## Overview
The Health Score API provides an AI-driven wellness score (0-100) with 3 personalized daily actions. The AI analyzes your recent health data and generates a score starting from a base of 80.

## Endpoint

### GET `/api/health-score/{user_id}`

Retrieves or calculates the user's weekly health score with personalized actions and week-over-week comparison.

#### Parameters
- `user_id` (path, required): The user's ID
- `force_refresh` (query, optional): Set to `true` to bypass cache and generate new score

#### Response Format
```json
{
  "score": 76,
  "previous_score": 72,
  "trend": "up",
  "actions": [
    {
      "icon": "💧",
      "text": "Stay hydrated"
    },
    {
      "icon": "🧘",
      "text": "Meditate 10 mins"
    },
    {
      "icon": "🚶",
      "text": "Walk after lunch"
    }
  ],
  "reasoning": "Score reflects good tracking consistency with mild symptom activity",
  "generated_at": "2025-01-31T14:30:00Z",
  "week_of": "2025-01-27T00:00:00Z",
  "cached": false
}
```

#### Response Fields
- `score`: Number between 0-100 (everyone starts at base 80)
- `previous_score`: Last week's score (null if no previous week data)
- `trend`: Week-over-week trend ("up", "down", "same", or null)
- `actions`: Array of exactly 3 personalized actions (2-10 words each)
  - `icon`: Emoji representing the action type
  - `text`: Specific, actionable instruction
- `reasoning`: Brief explanation of why this score was given
- `generated_at`: ISO timestamp when score was calculated
- `week_of`: ISO timestamp of Monday for this week's score
- `cached`: Boolean indicating if this is a cached result

## How It Works

1. **Data Collection**: The AI looks at:
   - Recent symptom reports (last 7 days)
   - Health tracking consistency
   - Oracle chat engagement
   - Quick scan results and confidence scores
   - Medical profile (if available)

2. **Score Calculation**: 
   - Base score: 80 (good baseline health)
   - AI adjusts based on patterns it observes
   - No rigid formula - AI interprets the overall picture

3. **Personalized Actions**:
   - Mix of general wellness tips and personalized recommendations
   - Based on user's specific symptoms and patterns
   - Tailored to current time of day
   - Concise format: 2-10 words maximum
   - Always achievable within the same day

4. **Weekly Persistence**:
   - Scores stored for entire week (Monday to Sunday)
   - New score generated only if none exists for current week
   - Previous week's score included for comparison
   - Use `force_refresh=true` to regenerate within the week

## Frontend Implementation Tips

### Basic Usage
```javascript
// Fetch health score
const response = await fetch(`/api/health-score/${userId}`);
const data = await response.json();

// Display score
console.log(`Your health score: ${data.score}/100`);

// Display actions
data.actions.forEach(action => {
  console.log(`${action.icon} ${action.text}`);
});
```

### Display Suggestions

1. **Score Display**:
   - Show as large number with /100
   - Consider color coding:
     - 90-100: Excellent (green)
     - 75-89: Good (blue)
     - 60-74: Fair (yellow)
     - Below 60: Needs attention (orange)

2. **Actions Display**:
   - Show as cards or list items
   - Keep emoji icons visible
   - Make text prominent and readable
   - Consider adding checkboxes for completion tracking

3. **Refresh Logic**:
   - Check `expires_at` to show when next update available
   - Add manual refresh button that sets `force_refresh=true`
   - Show "cached" indicator if `cached: true`

### Example UI Structure
```
┌─────────────────────────────────┐
│         Health Score            │
│                                 │
│            76/100               │
│         ━━━━━━━━━━              │
│                                 │
│    Today's Actions:             │
│                                 │
│  💧 Increase water intake       │
│     by 500ml today              │
│                                 │
│  🧘 10-minute meditation        │
│     before bed                  │
│                                 │
│  🚶 Take a 15-minute walk       │
│     after lunch                 │
│                                 │
│  [Refresh Score]                │
└─────────────────────────────────┘
```

## Error Handling

### Possible Errors
- `404`: User not found
- `500`: Server error (returns default score 80 with generic actions)

### Fallback Behavior
If AI fails to generate score, the API returns:
```json
{
  "score": 80,
  "actions": [
    {"icon": "💧", "text": "Stay hydrated throughout the day"},
    {"icon": "🏃", "text": "Get 30 minutes of physical activity"},
    {"icon": "🧘", "text": "Practice stress reduction techniques"}
  ],
  "reasoning": "Unable to calculate personalized score"
}
```

## Notes

- Scores persist for entire week (Monday to Sunday)
- New scores only generated if none exists for current week
- Background job generates scores for all users on Mondays
- The AI model used is `moonshotai/kimi-k2`
- Actions are personalized based on user's health data
- Actions are concise (2-10 words) and time-aware
- No medical advice - only wellness suggestions