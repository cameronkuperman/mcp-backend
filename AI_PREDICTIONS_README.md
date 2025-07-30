# AI Predictions Feature

## Overview

The AI Predictions feature transforms static health alerts into dynamic, personalized predictions based on each user's actual health data patterns. It provides:

- **Dashboard Alerts**: Real-time health alerts based on pattern detection
- **Multi-timeframe Predictions**: Immediate (7 days), seasonal (3 months), and long-term health predictions
- **Pattern Questions**: AI-generated questions about unique health patterns
- **Body Patterns**: Personalized insights about triggers and positive responses

## Quick Start

### 1. Run the Migration
```bash
psql $DATABASE_URL < migrations/004_ai_predictions_tables.sql
```

### 2. Start the Server
```bash
python run_oracle.py
```

### 3. Test the Endpoints
```bash
# Quick test with curl
./test_ai_endpoints.sh YOUR_USER_ID

# Or comprehensive Python test
python test_ai_predictions.py --create-data
```

## API Endpoints

### Dashboard Alert
```
GET /api/ai/dashboard-alert/{user_id}
```
Returns the most important predictive alert for the user's dashboard.

### Predictions
```
GET /api/ai/predictions/{user_id}
```
Returns comprehensive predictions across multiple timeframes.

### Pattern Questions
```
GET /api/ai/pattern-questions/{user_id}
```
Generates personalized questions about the user's health patterns.

### Body Patterns
```
GET /api/ai/body-patterns/{user_id}
```
Analyzes and returns the user's unique body patterns and responses.

## Frontend Integration

See `FRONTEND_AI_PREDICTIONS_GUIDE.md` for complete frontend implementation instructions including:
- React hooks
- TypeScript interfaces
- Component examples
- Caching strategies

## Architecture

```
User Health Data
      ↓
Data Gathering Layer (utils/data_gathering.py)
      ↓
AI Analysis Engine (services/ai_health_analyzer.py)
      ↓
API Endpoints (api/ai_predictions.py)
      ↓
Frontend Hooks & Components
```

## Configuration

The system uses DeepSeek V3 (`deepseek/deepseek-chat`) by default, as recommended in CLAUDE.md. You can override the model per endpoint if needed.

## Data Requirements

- **Minimum for Alerts**: 5 health entries
- **Minimum for Predictions**: 10 health entries
- **Optimal Performance**: 30+ days of consistent data

## Error Handling

All endpoints handle errors gracefully:
- Insufficient data returns helpful onboarding messages
- API failures fall back to cached data when available
- No sensitive information is exposed in error messages

## Performance

- Dashboard alerts cache for 30 minutes
- Predictions cache for 1 hour
- Database queries are optimized with proper indexes
- AI calls have 15-minute timeout for complex analysis

## Security

- Row Level Security (RLS) on all tables
- User ID validation on every request
- No PII in logs or error messages
- Service role required for data insertion

## Monitoring

Track these metrics:
- Alert generation rate
- Prediction accuracy (via outcome tracking)
- API response times
- User engagement rates

## Troubleshooting

### No Predictions Generated
- Check if user has sufficient data (10+ entries)
- Verify user ID is correct
- Check API logs for errors

### Slow Response Times
- Monitor AI model response times
- Check database query performance
- Consider increasing cache TTL

### Invalid JSON Responses
- Verify AI model is returning proper JSON
- Check json_parser.py for extraction issues
- Monitor model-specific quirks

## Contributing

When adding new features:
1. Add endpoints to `api/ai_predictions.py`
2. Update data gathering in `utils/data_gathering.py`
3. Add tests to `test_ai_predictions.py`
4. Update frontend guide
5. Document any new dependencies

## Support

For issues or questions:
1. Check the logs: `mcp-backend.log`
2. Run the test suite
3. Verify database migrations
4. Check model availability on OpenRouter

---

Built with 🤖 AI-powered intelligence for personalized health insights.