# Weekly Intelligence Implementation Guide
## Production-Grade Architecture for 500K+ Users

### 🎯 Core Architecture Principles
Following META/Google/YouTube patterns for scalability and user experience.

## 1. Weekly Brief Notification System

### Trigger Logic (META-inspired)
```typescript
// Notification appears on first login after weekly job completes
// Following Instagram's "Stories" pattern - once per cycle, dismissible

interface NotificationState {
  briefId: string;
  weekOf: string;
  generatedAt: timestamp;
  firstShownAt: timestamp | null;
  dismissedAt: timestamp | null;
  engagementTime: number; // seconds viewed before dismiss
  impressions: number; // times it attempted to show
}
```

### Implementation Strategy
1. **Job Completion Marker**: Store in Redis/cache when job completes for each user
2. **First Login Detection**: Check on dashboard mount if new brief exists
3. **Impression Tracking**: Following Facebook's approach:
   - Visibility > 0ms = impression
   - Visibility > 3s = engaged view
   - Scroll > 50% = meaningful engagement

### Settings Schema Addition
```sql
ALTER TABLE user_preferences ADD COLUMN 
  weekly_brief_enabled BOOLEAN DEFAULT true,
  weekly_brief_frequency ENUM('weekly', 'biweekly', 'monthly', 'never') DEFAULT 'weekly',
  last_brief_dismissed_at TIMESTAMP,
  total_briefs_dismissed INT DEFAULT 0,
  avg_engagement_time FLOAT DEFAULT 0;
```

## 2. Scalability Architecture (Google Cloud Patterns)

### Loading Strategy - Progressive Enhancement
```javascript
// Following YouTube's approach - load critical, then enhance
const IntelligencePage = () => {
  // Phase 1: Critical data (< 1s)
  const velocity = useHealthVelocity({ cache: 'stale-while-revalidate' });
  
  // Phase 2: Enhanced data (< 3s)
  const systems = useBodySystems({ lazy: true });
  const timeline = useMasterTimeline({ lazy: true });
  
  // Phase 3: Rich data (background)
  const patterns = usePatterns({ prefetch: 'intent' });
  const comparative = useComparative({ background: true });
}
```

### Caching Strategy (Cloudflare/Fastly patterns)
```yaml
Cache Layers:
  L1: Browser Cache (5 min for intelligence data)
  L2: CDN Edge (1 hour, stale-while-revalidate)
  L3: Redis (1 day, with warm-up jobs)
  L4: Database (persistent, weekly generation)

Cache Keys:
  - user:{userId}:intelligence:week:{weekOf}
  - user:{userId}:velocity:{timeRange}
  - user:{userId}:patterns:v2
```

## 3. Job Failure Recovery System

### Multi-Level Retry Strategy (AWS SQS patterns)
```python
# In weekly_intelligence_job.py additions
class JobRetryStrategy:
    MAX_RETRIES = 3
    BACKOFF_MULTIPLIER = 2
    
    async def execute_with_retry(self, user_id: str):
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await generate_user_intelligence(user_id)
                if result['summary']['success_rate'] > 80:
                    return result
                raise PartialFailure(result)
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    await self.dead_letter_queue(user_id, e)
                    await self.fallback_generation(user_id)
                else:
                    await asyncio.sleep(2 ** attempt * self.BACKOFF_MULTIPLIER)
        
    async def fallback_generation(self, user_id: str):
        # Generate minimal intelligence with cached data
        # Mark as "partial" in UI
        pass
```

### Verification System
```python
# Add to services/job_verification.py
async def verify_intelligence_generation(user_id: str, week_of: str):
    checks = {
        'brief_exists': check_brief_exists(user_id, week_of),
        'insights_count': count_insights(user_id, week_of) >= 3,
        'patterns_found': check_patterns(user_id, week_of),
        'freshness': check_generation_time(user_id, week_of) < 7_days
    }
    
    health_score = sum(checks.values()) / len(checks)
    if health_score < 0.8:
        await trigger_regeneration(user_id)
```

## 4. Performance Optimization

### Request Coalescing (YouTube-style)
```javascript
// Batch multiple component requests into single API call
const useIntelligenceBatch = () => {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    // Coalesce all intelligence requests
    const batchRequest = Promise.all([
      fetchVelocity(),
      fetchSystems(),
      fetchTimeline()
    ].map(p => p.catch(e => ({ error: e }))));
    
    // Return partial success
    batchRequest.then(results => {
      setData(results.filter(r => !r.error));
    });
  }, []);
};
```

### Skeleton Loading (Facebook pattern)
```jsx
// Show layout immediately, fill with data progressively
<IntelligenceGrid>
  <Suspense fallback={<VelocitySkeleton />}>
    <HealthVelocity />
  </Suspense>
  <Suspense fallback={<SystemsSkeleton />}>
    <BodySystems />
  </Suspense>
</IntelligenceGrid>
```

## 5. Analytics & Engagement Tracking

### Event Schema (Google Analytics 4 pattern)
```typescript
interface IntelligenceEvent {
  event_name: 'intelligence_interaction';
  event_params: {
    component: 'brief' | 'velocity' | 'patterns' | etc;
    action: 'view' | 'dismiss' | 'expand' | 'action_taken';
    engagement_time: number;
    scroll_depth: number;
    brief_week: string;
    user_segment: 'power' | 'regular' | 'new';
  };
}
```

### Engagement Metrics
```sql
CREATE TABLE intelligence_analytics (
  user_id UUID,
  week_of DATE,
  brief_view_time INT, -- seconds
  brief_scroll_depth FLOAT, -- 0-1
  patterns_clicked INT,
  recommendations_actioned INT,
  velocity_interactions INT,
  total_page_time INT,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, week_of)
);
```

## 6. Dismissal & Access Patterns

### Smart Dismissal (Instagram Stories pattern)
```typescript
const dismissalBehavior = {
  // Temporary dismiss (this week only)
  softDismiss: () => {
    localStorage.setItem(`brief_dismissed_${weekOf}`, true);
    track('brief_soft_dismissed');
  },
  
  // Permanent dismiss (disable feature)
  hardDismiss: async () => {
    await updateUserPreferences({ weekly_brief_enabled: false });
    track('brief_permanently_disabled');
    // Still generate in background for /weekly-brief access
  },
  
  // Smart re-enable (if user visits /weekly-brief after disable)
  autoReEnable: async () => {
    if (!prefs.weekly_brief_enabled && visitedBriefRoute) {
      await updateUserPreferences({ 
        weekly_brief_enabled: true,
        re_enabled_reason: 'user_visited_route' 
      });
    }
  }
};
```

## 7. Route Structure

### URL Schema
```
/dashboard                 → Weekly brief overlay (if new)
/weekly-brief             → Current week's brief (full page)
/weekly-brief/:weekOf     → Historical brief
/intelligence             → All intelligence components
/intelligence/velocity    → Deep dive into velocity
/intelligence/patterns    → Pattern exploration
```

## 8. Database Optimizations

### Indexes for Scale
```sql
-- Optimize for 500K+ users
CREATE INDEX idx_briefs_user_week ON weekly_health_briefs(user_id, week_of DESC);
CREATE INDEX idx_intelligence_cache_expires ON intelligence_cache(expires_at) 
  WHERE expires_at > NOW(); -- Partial index
CREATE INDEX idx_insights_week_confidence ON health_insights(week_of, confidence DESC);

-- Partitioning for historical data
ALTER TABLE weekly_health_briefs PARTITION BY RANGE (week_of);
CREATE TABLE weekly_health_briefs_2024_q1 PARTITION OF weekly_health_briefs
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

## 9. Error States & Fallbacks

### User-Friendly Degradation
```typescript
const IntelligenceComponent = () => {
  const { data, error, isStale } = useIntelligence();
  
  if (error && !data) {
    // Complete failure - show helpful empty state
    return <GenerateIntelligencePrompt />;
  }
  
  if (error && data) {
    // Partial failure - show stale data with warning
    return (
      <>
        <StaleDataBanner lastUpdated={data.generatedAt} />
        <IntelligenceView data={data} />
      </>
    );
  }
  
  if (isStale && data) {
    // Background refresh in progress
    return (
      <>
        <RefreshingIndicator />
        <IntelligenceView data={data} />
      </>
    );
  }
  
  return <IntelligenceView data={data} />;
};
```

## 10. Testing Strategy

### Load Testing Scenarios
```yaml
Scenarios:
  - Monday Morning Surge: 100K users login 8-9 AM
  - Batch Generation: 50K intelligence generations in 1 hour
  - Cache Miss Storm: Redis restart with 10K concurrent users
  - Partial Failure: 30% of LLM calls fail
  - Network Partition: Database becomes read-only
```

---

## Implementation Priority

### Phase 1 (Week 1)
- [ ] Weekly brief overlay with dismissal tracking
- [ ] Basic job retry mechanism
- [ ] Browser caching strategy

### Phase 2 (Week 2)
- [ ] Advanced analytics tracking
- [ ] Redis caching layer
- [ ] Progressive loading

### Phase 3 (Week 3)
- [ ] Full retry/fallback system
- [ ] Performance optimizations
- [ ] A/B testing framework