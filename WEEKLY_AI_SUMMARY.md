# Weekly AI Predictions - Implementation Summary

## 🎯 What Was Built

A **proactive AI predictions system** that:
- Generates predictions **automatically once a week** (default: Wednesday 5 PM)
- Generates **initial predictions** when user first downloads the app
- Stores predictions in Supabase for **instant retrieval** (no waiting)
- Allows users to **customize** their preferred day/time
- Includes **manual regeneration** (rate limited to once per day)

## 🏗️ Architecture

### Database Tables (Migration: `005_weekly_ai_predictions.sql`)
1. **weekly_ai_predictions**: Stores all generated predictions
2. **user_ai_preferences**: User's scheduling preferences

### Background Jobs
- **Weekly Generation**: Runs every Wednesday at 5 PM UTC by default
- **Hourly Check**: Processes users based on their timezone preferences
- **Initial Generation**: Triggered during user onboarding

### API Endpoints
1. `POST /api/ai/generate-initial/{user_id}` - First-time generation
2. `GET /api/ai/weekly/{user_id}` - Get stored predictions
3. `GET /api/ai/weekly/{user_id}/alert` - Dashboard alert only
4. `GET/PUT /api/ai/preferences/{user_id}` - User preferences
5. `POST /api/ai/regenerate/{user_id}` - Manual refresh

## 📊 How It Works

### Flow for New Users:
```
User Signs Up
     ↓
App calls /api/ai/generate-initial/{user_id}
     ↓
Backend generates all 4 AI features
     ↓
Stores in weekly_ai_predictions table
     ↓
Frontend fetches via /api/ai/weekly/{user_id}
```

### Weekly Flow:
```
Wednesday 5 PM (or user's preferred time)
     ↓
Background job runs
     ↓
For each active user:
  - Generate dashboard alert
  - Generate predictions
  - Generate pattern questions
  - Generate body patterns
     ↓
Store in database
     ↓
Users see new predictions next time they open app
```

## 🚀 Deployment Steps

1. **Run the migration**:
   ```bash
   psql $DATABASE_URL < migrations/005_weekly_ai_predictions.sql
   ```

2. **Test locally**:
   ```bash
   python run_oracle.py
   python test_weekly_ai.py --initial
   ```

3. **Deploy to Railway**:
   ```bash
   git add .
   git commit -m "Add weekly AI predictions system"
   git push
   ```

## 📱 Frontend Integration

### Key Changes:
1. **Onboarding**: Call generate-initial endpoint
2. **Dashboard**: Fetch stored alert (no generation delay)
3. **Insights Page**: Fetch all stored predictions
4. **Settings**: Add preferences UI

### Example Hook:
```typescript
const { predictions, isLoading } = useWeeklyAIPredictions();
// Returns stored predictions instantly
```

## ⏰ Scheduling Details

### Default Schedule:
- **Generation Day**: Wednesday (customizable)
- **Generation Time**: 5 PM user's timezone (customizable)
- **Frequency**: Once per week

### Customization:
Users can change their schedule via preferences:
- Any day of the week
- Any hour (0-23)
- Respects user's timezone

### Rate Limiting:
- Automatic generation: Once per week
- Manual regeneration: Once per day

## 📈 Benefits

1. **Performance**: No waiting for AI on page load
2. **Cost Efficiency**: ~7x reduction in AI calls
3. **Reliability**: Background jobs ensure predictions are ready
4. **Flexibility**: Users control when predictions generate
5. **Consistency**: Fresh insights every week

## 🧪 Testing

```bash
# Test initial generation
python test_weekly_ai.py --initial

# Test fetching predictions
python test_weekly_ai.py --weekly

# Test preferences
python test_weekly_ai.py --prefs

# Test manual regeneration
python test_weekly_ai.py --regenerate
```

## 📊 Monitoring

Track these metrics:
- Weekly generation success rate
- Average generation time
- User preference patterns
- Manual regeneration frequency

## 🔍 Troubleshooting

### No predictions showing?
1. Check if initial generation completed
2. Verify user has sufficient data
3. Check generation logs in `weekly_ai_predictions` table

### Generation failing?
1. Check `error_message` in database
2. Verify API keys are set
3. Check if user has enough health data

### Wrong timezone?
- Update user preferences with correct timezone
- Generation will adjust on next cycle

---

The system is now **fully implemented** and ready for production use!