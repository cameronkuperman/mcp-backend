# Comprehensive Analytics & Evaluation System Prompt

## Context
Design and implement a medical-grade analytics system that tracks user engagement, health outcomes, and product effectiveness while maintaining HIPAA compliance and user privacy. This system should provide actionable insights for both product improvement and user health optimization.

## Core Analytics Philosophy
Following Google Analytics 4's event-driven model and Apple Health's privacy-first approach, create an analytics system that answers: "Is our product actually improving user health outcomes?"

## Implementation Framework

### 1. Health Outcome Tracking
```javascript
// Track actual health improvements, not just engagement
const HealthOutcomeAnalytics = {
  // Symptom trajectory tracking
  symptomImprovement: {
    baseline: captureSymptomSeverityAtOnboarding(),
    weekly: trackWeeklySymptomScores(),
    delta: calculateImprovementRate(),
    correlation: correlateWithActionsToken()
  },
  
  // Intervention effectiveness
  interventionSuccess: {
    recommended: trackRecommendationsGiven(),
    attempted: trackRecommendationsAttempted(),
    completed: trackRecommendationsCompleted(),
    outcome: measureSymptomChangePostIntervention()
  },
  
  // Pattern discovery value
  patternUtility: {
    discovered: countPatternsIdentified(),
    actioned: countPatternsActedUpon(),
    resolved: countPatternsEliminated()
  }
};
```

### 2. Engagement Quality Metrics
Beyond simple page views, measure meaningful engagement:

```typescript
interface QualityEngagement {
  // Depth metrics
  intelligenceDepth: number; // How many layers deep users explore
  insightActions: number; // Insights that led to behavior change
  patternRecognition: number; // User confirms AI-found patterns
  
  // Continuity metrics  
  streaks: number; // Consecutive weeks of tracking
  dataCompleteness: number; // % of health data provided
  reportGeneration: number; // Doctor reports created
  
  // Value metrics
  ahaModments: number; // Significant discoveries
  behaviorChanges: number; // Documented lifestyle modifications
  healthConfidence: number; // Self-reported confidence score
}
```

### 3. Predictive Analytics Pipeline
```python
# Use historical data to predict and prevent health issues
class PredictiveHealthAnalytics:
    def identify_at_risk_users(self):
        # Users showing concerning patterns
        return users.filter(
            velocity_score < 40,
            symptoms_increasing = True,
            engagement_dropping = True
        )
    
    def predict_churn_risk(self):
        # Health app abandonment prediction
        features = [
            'days_since_last_symptom_log',
            'brief_dismissal_rate',
            'unactioned_recommendations',
            'symptom_improvement_rate'
        ]
        return ml_model.predict_churn(features)
    
    def forecast_health_trajectory(self):
        # 30-day health outcome prediction
        return time_series_model.forecast(
            historical_symptoms,
            intervention_history,
            engagement_patterns
        )
```

### 4. A/B Testing Framework for Health Features
```javascript
// Medical-grade A/B testing with safety controls
const HealthFeatureExperiment = {
  setup: {
    hypothesis: "Narrative briefs improve symptom tracking compliance",
    control: "Bullet-point summaries",
    treatment: "Story-based narratives",
    success_metric: "symptom_logging_frequency",
    safety_metric: "user_reported_confusion",
    minimum_sample: 1000,
    duration: "2 weeks"
  },
  
  safety: {
    // Stop experiment if harm detected
    stopConditions: [
      "safety_metric > threshold",
      "urgent_symptoms_missed > 0",
      "user_complaints > 5"
    ],
    
    // Ensure medical safety
    exclusions: [
      "users_with_serious_conditions",
      "users_in_crisis",
      "users_under_18"
    ]
  }
};
```

### 5. Privacy-First Architecture
```typescript
// Following Apple's differential privacy approach
const PrivacyPreservingAnalytics = {
  // Aggregate without identifying
  aggregation: {
    method: "differential_privacy",
    epsilon: 1.0, // Privacy budget
    noise_addition: "laplacian",
    minimum_cohort_size: 100
  },
  
  // Hash all identifiers
  anonymization: {
    user_id: sha256(user_id + salt),
    session_id: sha256(session_id + rotating_salt),
    ip_address: "never_collected",
    location: "region_only"
  },
  
  // Data retention
  retention: {
    raw_events: "7 days",
    aggregated_data: "2 years",
    user_identified_data: "until_deletion_requested"
  }
};
```

### 6. Real-Time Dashboards
```sql
-- Executive dashboard queries
CREATE MATERIALIZED VIEW health_outcomes_dashboard AS
SELECT 
  DATE_TRUNC('week', created_at) as week,
  COUNT(DISTINCT user_id) as active_users,
  AVG(health_velocity_score) as avg_velocity,
  SUM(CASE WHEN velocity_delta > 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as improving_rate,
  AVG(symptoms_tracked) as avg_symptoms_per_user,
  AVG(recommendations_actioned) as action_rate,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY engagement_time) as median_engagement
FROM user_health_metrics
GROUP BY week
WITH DATA;

-- Refresh every hour
CREATE OR REPLACE FUNCTION refresh_dashboard()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY health_outcomes_dashboard;
END;
$$ LANGUAGE plpgsql;
```

### 7. Cohort Analysis
```javascript
// Understand different user segments
const CohortAnalysis = {
  segments: {
    power_users: "daily_active AND symptoms_tracked > 5",
    at_risk: "velocity_score < 40 AND engagement_dropping",
    improved: "velocity_delta > 20 AND sustained_4_weeks",
    new_users: "account_age < 7_days",
    chronic: "condition_duration > 180_days"
  },
  
  metrics_by_cohort: {
    retention: calculateRetentionCurve(cohort),
    improvement: measureHealthOutcomes(cohort),
    feature_adoption: trackFeatureUsage(cohort),
    satisfaction: getNPS(cohort)
  }
};
```

### 8. Alert System for Concerning Patterns
```python
# Proactive monitoring for user safety
class HealthAlertSystem:
    alerts = [
        {
            "name": "sudden_deterioration",
            "condition": "velocity_drop > 30 in 7 days",
            "action": "prompt_user_check_in"
        },
        {
            "name": "abandoned_serious_symptoms",
            "condition": "high_severity_logged AND no_followup_48h",
            "action": "send_gentle_reminder"
        },
        {
            "name": "pattern_success",
            "condition": "pattern_eliminated AND sustained_2_weeks",
            "action": "celebrate_achievement"
        }
    ]
```

## Expected Implementation Outcomes

1. **Product Metrics**: Know exactly which features drive health improvements
2. **User Success**: Identify and replicate successful health journeys
3. **Risk Mitigation**: Catch and prevent user health deterioration
4. **Feature Validation**: Prove which AI insights actually help
5. **Compliance**: HIPAA-compliant, GDPR-ready analytics

## Extension Considerations
- Integration with Apple HealthKit / Google Fit
- Clinical trial data collection capabilities
- Population health insights for research
- Predictive risk scoring for insurance partnerships
- Anonymous benchmarking against similar users