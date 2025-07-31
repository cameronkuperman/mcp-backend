# AI Predictions API Documentation

## Overview
The AI Predictions API provides intelligent health insights and predictions based on user data. All endpoints support smart caching to improve performance and reduce AI generation costs.

## Endpoints

### 1. Dashboard Alert
**GET** `/api/ai/dashboard-alert/{user_id}`

Get the single most important alert for the dashboard.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration of prediction (default: false)

#### Response
```json
{
  "alert": {
    "id": "uuid",
    "severity": "info|warning|critical",
    "title": "Alert title",
    "description": "Alert description",
    "timeframe": "General timeframe",
    "confidence": 60-90,
    "preventionTip": "Immediate action to take",
    "actionUrl": "/predictive-insights?focus=uuid",
    "generated_at": "2025-01-31T..."
  },
  "status": "success|cached|no_patterns",
  "expires_at": "2025-02-07T..."
}
```

### 2. Immediate Predictions
**GET** `/api/ai/predictions/immediate/{user_id}`

Generate predictions for the next 7 days.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration (default: false)

#### Response
```json
{
  "predictions": [
    {
      "id": "uuid",
      "title": "Risk/pattern title",
      "subtitle": "Brief description",
      "pattern": "The pattern detected",
      "trigger_combo": "What combination of factors",
      "historical_accuracy": "82%",
      "confidence": 82,
      "prevention_protocol": ["Action steps"],
      "type": "immediate",
      "gradient": "from-yellow-600/10 to-orange-600/10"
    }
  ],
  "data_quality_score": 75,
  "status": "success|cached",
  "expires_at": "2025-02-07T..."
}
```

### 3. Seasonal Predictions
**GET** `/api/ai/predictions/seasonal/{user_id}`

Generate seasonal predictions for the next 3 months.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration (default: false)

#### Response
```json
{
  "predictions": [
    {
      "id": "uuid",
      "title": "Seasonal pattern title",
      "subtitle": "Brief description",
      "pattern": "What seasonal pattern affects them",
      "timeframe": "February-March",
      "confidence": 75,
      "prevention_protocol": ["Prevention steps"],
      "historical_context": "Common pattern description"
    }
  ],
  "current_season": "winter",
  "next_season_transition": "2025-03-20",
  "status": "success|cached"
}
```

### 4. Long-term Trajectory
**GET** `/api/ai/predictions/longterm/{user_id}`

Generate long-term health trajectory assessments.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration (default: false)

#### Response
```json
{
  "assessments": [
    {
      "id": "uuid",
      "condition": "Health area being assessed",
      "current_status": "Current state description",
      "risk_factors": ["List of risk factors"],
      "trajectory": {
        "current_path": {
          "description": "Where they're headed now",
          "risk_level": "low|moderate|high",
          "projected_outcome": "Likely outcome if unchanged"
        },
        "optimized_path": {
          "description": "Where they could be",
          "risk_level": "low|moderate",
          "requirements": ["What it takes to get there"]
        }
      },
      "prevention_strategy": ["Long-term strategies"],
      "confidence": 78,
      "data_basis": "What this assessment is based on"
    }
  ],
  "overall_health_trajectory": "positive|stable_with_improvement_potential|needs_attention",
  "key_focus_areas": ["cardiovascular_health"],
  "status": "success|cached"
}
```

### 5. Body Patterns
**GET** `/api/ai/patterns/{user_id}`

Generate personalized body pattern insights using Kimi K2 AI model.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration (default: false)

#### Response
```json
{
  "tendencies": [
    "Get migraines 48-72 hours after high stress events",
    "Feel anxious on Sunday evenings (work anticipation)",
    "Sleep poorly during full moons (light sensitivity)"
  ],
  "positive_responses": [
    "Consistent sleep schedule (±30 min)",
    "Regular meal timing",
    "Moderate exercise (not intense)"
  ],
  "pattern_metadata": {
    "total_patterns_analyzed": 150,
    "confidence_level": "high",
    "data_span_days": 90,
    "generated_at": "2025-01-31T..."
  },
  "status": "success|cached"
}
```

### 6. Pattern Questions
**GET** `/api/ai/questions/{user_id}`

Generate personalized questions about health patterns.

#### Parameters
- `user_id` (path): User ID
- `force_refresh` (query, optional): Force regeneration (default: false)

#### Response
```json
{
  "questions": [
    {
      "id": "uuid",
      "question": "Why do I get Sunday anxiety?",
      "category": "mood",
      "icon": "brain",
      "brief_answer": "Your Sunday anxiety stems from work week anticipation.",
      "deep_dive": {
        "detailed_insights": ["Specific insights"],
        "connected_patterns": ["Related patterns"],
        "actionable_advice": ["Action steps"]
      },
      "relevance_score": 92,
      "based_on": ["mood_logs", "sleep_data"]
    }
  ],
  "total_questions": 4,
  "categories_covered": ["mood", "sleep", "energy"],
  "status": "success|cached"
}
```

## Smart Caching

All endpoints support smart caching with automatic expiry:

- **Dashboard alerts**: 7 days
- **Immediate predictions**: 7 days  
- **Seasonal predictions**: 30 days (regenerate after 14 days)
- **Long-term assessments**: 90 days (regenerate after 30 days)
- **Body patterns**: 14 days (regenerate after 7 days)
- **Pattern questions**: 14 days (regenerate after 7 days)

### Force Refresh
Add `?force_refresh=true` to any endpoint to bypass cache and generate fresh predictions.

## Weekly Generation

Predictions are automatically generated weekly for users with:
- Weekly generation enabled in preferences
- Initial predictions already generated
- On their preferred day and hour

### Manual Trigger
**POST** `/api/ai/generate-weekly/{user_id}`

Manually trigger weekly prediction generation for a user.

## Error Handling

All endpoints return appropriate error responses:

```json
{
  "status": "error",
  "error": "Error message",
  "predictions": [] // or appropriate empty structure
}
```

## Data Quality

Predictions require minimum data quality scores:
- Dashboard alerts: 20
- Immediate predictions: 30
- Seasonal predictions: 20
- Long-term assessments: 40
- Body patterns: 30
- Pattern questions: 30

If insufficient data, endpoints return helpful messages guiding users to track more data.