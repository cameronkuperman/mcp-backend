# Complete Frontend Intelligence Implementation Guide

## Table of Contents
1. [Supabase Database Structure](#supabase-database-structure)
2. [What Each Feature Does](#what-each-feature-does)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Frontend Implementation Patterns](#frontend-implementation-patterns)
5. [State Management Strategy](#state-management-strategy)
6. [Real-World Component Examples](#real-world-component-examples)
7. [Performance Optimization](#performance-optimization)
8. [Error Handling & Fallbacks](#error-handling--fallbacks)

---

## 1. Supabase Database Structure

### Core Intelligence Tables

#### `weekly_health_briefs`
**Purpose:** Stores the main weekly narrative health summary for each user
```sql
{
  id: UUID,                    // Unique identifier
  user_id: UUID,              // User reference
  week_of: DATE,              // Monday of the week
  greeting: JSONB,            // Personalized greeting
  main_story: JSONB,          // Primary health narrative
  discoveries: JSONB,         // New findings about health
  experiments: JSONB,         // Suggested health experiments
  spotlight: JSONB,           // Featured body system focus
  week_stats: JSONB,          // Quantified week metrics
  looking_ahead: JSONB,       // Next week preview
  created_at: TIMESTAMP,      // When generated
  last_opened_at: TIMESTAMP   // Engagement tracking
}
```

**JSONB Structure Example:**
```json
{
  "main_story": {
    "title": "Your Energy Renaissance Week",
    "narrative": "This week marked a turning point...",
    "key_moments": ["Monday's breakthrough", "Thursday's pattern"],
    "confidence": 0.85
  }
}
```

#### `intelligence_cache`
**Purpose:** Caches all computed intelligence data for fast retrieval
```sql
{
  id: UUID,
  user_id: UUID,
  cache_key: VARCHAR(255),    // e.g., "velocity_7D", "patterns_current"
  data: JSONB,                // Cached computation result
  generated_at: TIMESTAMP,
  expires_at: TIMESTAMP       // Auto-cleanup after expiry
}
```

**Cache Keys:**
- `brief_{week_of}` - Weekly brief data
- `velocity_{time_range}` - Health velocity (7D, 30D, 90D)
- `systems_{date}` - Body systems analysis
- `timeline_{range}` - Health timeline
- `patterns_{type}` - Pattern detection
- `readiness_{date}` - Doctor readiness

#### `anonymous_symptom_patterns`
**Purpose:** Stores anonymized patterns for comparative intelligence
```sql
{
  id: UUID,
  pattern_hash: VARCHAR(16),   // Anonymized pattern ID
  user_hash: VARCHAR(16),      // Anonymized user ID
  occurrence_count: INT,       // How many times seen
  last_seen: TIMESTAMP
}
```

#### `job_execution_log`
**Purpose:** Tracks background job execution for monitoring
```sql
{
  id: UUID,
  job_name: VARCHAR(100),      // "weekly_intelligence"
  status: VARCHAR(20),         // pending|running|completed|failed
  started_at: TIMESTAMP,
  completed_at: TIMESTAMP,
  users_processed: INT,
  users_successful: INT,
  success_rate: FLOAT,
  error_message: TEXT
}
```

#### `user_preferences` (Extended)
**Purpose:** User settings for intelligence features
```sql
{
  // ... existing fields ...
  weekly_brief_enabled: BOOLEAN,           // Opt-in/out
  weekly_brief_frequency: VARCHAR(20),     // "weekly"|"biweekly"
  last_brief_dismissed_at: TIMESTAMP,
  total_briefs_dismissed: INT,
  avg_engagement_time: FLOAT,              // Seconds
  intelligence_generation_enabled: BOOLEAN
}
```

---

## 2. What Each Feature Does

### Weekly Health Brief
**What it is:** A comprehensive, narrative-driven health summary generated every Monday
**Purpose:** Transform raw health data into an engaging story that users actually want to read
**Key Features:**
- Personalized greeting based on time and user history
- Main health narrative with key moments
- Discoveries section highlighting new patterns
- Health experiments to try
- Body system spotlight
- Week statistics
- Looking ahead preview

### Health Velocity
**What it is:** Real-time measurement of health trajectory and momentum
**Purpose:** Show if health is improving, declining, or stable with actionable insights
**Key Metrics:**
- Score (0-100): Overall health momentum
- Trend: Direction of change
- Momentum: Rate of change
- Sparkline: Visual representation
- Recommendations: What to do next

### Body Systems Analysis
**What it is:** Evaluation of 7 major body systems based on symptoms
**Purpose:** Identify which body systems need attention
**Systems Tracked:**
- Head (neurological, cognitive)
- Chest (cardiovascular, respiratory)
- Digestive
- Arms (musculoskeletal upper)
- Legs (musculoskeletal lower)
- Skin (dermatological)
- Mental (psychological, emotional)

### Health Timeline
**What it is:** Chronological view of health events and milestones
**Purpose:** Understand health progression over time
**Features:**
- Event categorization
- Severity indicators
- Pattern connections
- Milestone tracking

### Pattern Detection
**What it is:** AI-identified recurring health patterns
**Purpose:** Surface hidden connections in symptoms
**Types:**
- Temporal patterns (time-based)
- Trigger patterns (cause-effect)
- Cluster patterns (co-occurring symptoms)
- Improvement patterns

### Doctor Readiness Score
**What it is:** Preparation level for medical appointments
**Purpose:** Ensure productive doctor visits
**Components:**
- Documentation completeness
- Symptom clarity
- Question preparation
- Timeline accuracy

### Comparative Intelligence
**What it is:** Anonymous comparison with similar users
**Purpose:** Context for symptoms ("Is this normal?")
**Privacy:**
- All data is hashed
- No PII stored
- Pattern-based only

---

## 3. API Endpoints Reference

### Weekly Brief Endpoints
```typescript
// Generate new brief (called by job)
POST /api/health-brief/generate
Body: { user_id: string }
Response: { 
  status: "success",
  brief_id: string,
  week_of: string
}

// Get current week's brief
GET /api/health-brief/{user_id}/current
Response: {
  brief: WeeklyBrief,
  engagement: {
    opened: boolean,
    time_spent: number
  }
}

// Get specific week's brief
GET /api/health-brief/{user_id}/{week_of}
Response: WeeklyBrief

// Mark brief as opened
POST /api/health-brief/{brief_id}/opened
Response: { success: boolean }

// Dismiss brief
POST /api/health-brief/{brief_id}/dismiss
Body: { permanent: boolean }
Response: { success: boolean }
```

### Intelligence Data Endpoints
```typescript
// Health Velocity
GET /api/intelligence/health-velocity/{user_id}
Query: { time_range: "7D" | "30D" | "90D" }
Response: {
  score: number,        // 0-100
  trend: "improving" | "stable" | "declining",
  momentum: number,     // Rate of change
  sparkline: number[],  // Daily scores
  recommendations: string[]
}

// Body Systems
GET /api/intelligence/body-systems/{user_id}
Response: {
  head: SystemHealth,
  chest: SystemHealth,
  digestive: SystemHealth,
  arms: SystemHealth,
  legs: SystemHealth,
  skin: SystemHealth,
  mental: SystemHealth
}

// SystemHealth type
{
  score: number,        // 0-100
  status: "healthy" | "attention" | "concern",
  issues: string[],
  recommendations: string[]
}

// Timeline
GET /api/intelligence/timeline/{user_id}
Query: { range: "week" | "month" | "year" }
Response: {
  events: TimelineEvent[],
  milestones: Milestone[],
  patterns: Pattern[]
}

// Patterns
GET /api/intelligence/patterns/{user_id}
Response: {
  patterns: Pattern[],
  confidence: number,
  suggestions: string[]
}

// Doctor Readiness
GET /api/intelligence/doctor-readiness/{user_id}
Response: {
  score: number,        // 0-100
  checklist: ChecklistItem[],
  missing_info: string[],
  preparation_tips: string[]
}

// Comparative Intelligence
GET /api/intelligence/comparative/{user_id}/{symptom_pattern}
Response: {
  similar_users_count: number,
  percentile: number,
  typical_duration: string,
  common_outcomes: string[]
}
```

---

## 4. Frontend Implementation Patterns

### Data Fetching Strategy
```typescript
// hooks/useIntelligence.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

// Weekly Brief Hook with Smart Caching
export const useWeeklyBrief = (userId: string) => {
  const queryClient = useQueryClient();
  
  return useQuery({
    queryKey: ['weekly-brief', userId, getCurrentWeekMonday()],
    queryFn: async () => {
      // Check cache first
      const cached = await checkIntelligenceCache(userId, 'brief');
      if (cached && !isExpired(cached)) {
        return cached.data;
      }
      
      // Fetch from API
      const response = await fetch(`/api/health-brief/${userId}/current`);
      const data = await response.json();
      
      // Update cache
      await updateIntelligenceCache(userId, 'brief', data);
      
      return data;
    },
    staleTime: 1000 * 60 * 60,      // 1 hour
    cacheTime: 1000 * 60 * 60 * 24, // 24 hours
    refetchOnWindowFocus: false,
    
    // Prefetch next week's data on Sunday
    onSuccess: (data) => {
      if (new Date().getDay() === 0) { // Sunday
        queryClient.prefetchQuery(['weekly-brief', userId, getNextWeekMonday()]);
      }
    }
  });
};

// Health Velocity with Real-time Updates
export const useHealthVelocity = (userId: string, timeRange = '7D') => {
  return useQuery({
    queryKey: ['health-velocity', userId, timeRange],
    queryFn: () => fetchHealthVelocity(userId, timeRange),
    staleTime: 1000 * 60 * 5,  // 5 minutes
    refetchInterval: 1000 * 60 * 15, // Refetch every 15 minutes
    
    // Optimistic updates when user logs symptoms
    onMutate: async (newSymptom) => {
      const previousData = queryClient.getQueryData(['health-velocity', userId, timeRange]);
      
      // Optimistically update velocity
      queryClient.setQueryData(['health-velocity', userId, timeRange], old => ({
        ...old,
        score: calculateNewScore(old.score, newSymptom),
        trend: calculateNewTrend(old.trend, newSymptom)
      }));
      
      return { previousData };
    }
  });
};

// Progressive Loading for Body Systems
export const useBodySystems = (userId: string) => {
  const [systems, setSystems] = useState<Partial<BodySystems>>({});
  
  // Load critical systems first
  const criticalSystems = useQuery({
    queryKey: ['body-systems-critical', userId],
    queryFn: () => fetchCriticalSystems(userId), // Head, Chest, Mental
    staleTime: 1000 * 60 * 10
  });
  
  // Load remaining systems after critical
  const remainingSystems = useQuery({
    queryKey: ['body-systems-remaining', userId],
    queryFn: () => fetchRemainingSystems(userId),
    enabled: !!criticalSystems.data,
    staleTime: 1000 * 60 * 10
  });
  
  // Combine results
  useEffect(() => {
    setSystems({
      ...criticalSystems.data,
      ...remainingSystems.data
    });
  }, [criticalSystems.data, remainingSystems.data]);
  
  return systems;
};
```

### Supabase Realtime Subscriptions
```typescript
// hooks/useRealtimeIntelligence.ts
export const useRealtimeIntelligence = (userId: string) => {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    // Subscribe to brief updates
    const briefSubscription = supabase
      .channel(`briefs:${userId}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'weekly_health_briefs',
        filter: `user_id=eq.${userId}`
      }, (payload) => {
        // New brief available
        queryClient.invalidateQueries(['weekly-brief', userId]);
        
        // Show notification
        showNotification('Your weekly health brief is ready!');
      })
      .subscribe();
    
    // Subscribe to job completion
    const jobSubscription = supabase
      .channel('job_status')
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'job_execution_log',
        filter: `job_name=eq.weekly_intelligence`
      }, (payload) => {
        if (payload.new.status === 'completed') {
          // Refresh all intelligence data
          queryClient.invalidateQueries(['intelligence']);
        }
      })
      .subscribe();
    
    return () => {
      briefSubscription.unsubscribe();
      jobSubscription.unsubscribe();
    };
  }, [userId]);
};
```

---

## 5. State Management Strategy

### Zustand Store for Intelligence
```typescript
// stores/intelligenceStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface IntelligenceState {
  // Brief Management
  currentBrief: WeeklyBrief | null;
  briefDismissed: boolean;
  briefEngagementStart: number | null;
  
  // User Preferences
  briefEnabled: boolean;
  autoShowBrief: boolean;
  preferredViewMode: 'narrative' | 'data';
  
  // Actions
  setBrief: (brief: WeeklyBrief) => void;
  dismissBrief: (permanent?: boolean) => void;
  trackEngagement: () => void;
  updatePreferences: (prefs: Partial<Preferences>) => void;
  
  // Intelligence Cache
  velocityCache: Map<string, HealthVelocity>;
  systemsCache: Map<string, BodySystems>;
  updateCache: (type: string, data: any) => void;
}

export const useIntelligenceStore = create<IntelligenceState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentBrief: null,
      briefDismissed: false,
      briefEngagementStart: null,
      briefEnabled: true,
      autoShowBrief: true,
      preferredViewMode: 'narrative',
      velocityCache: new Map(),
      systemsCache: new Map(),
      
      // Actions
      setBrief: (brief) => set({ 
        currentBrief: brief,
        briefDismissed: false,
        briefEngagementStart: Date.now()
      }),
      
      dismissBrief: async (permanent = false) => {
        const engagementTime = Date.now() - (get().briefEngagementStart || Date.now());
        
        // Track dismissal
        await trackEvent('brief_dismissed', {
          engagement_time: engagementTime,
          permanent
        });
        
        // Update database if permanent
        if (permanent) {
          await updateUserPreferences({ weekly_brief_enabled: false });
        }
        
        set({ 
          briefDismissed: true,
          briefEngagementStart: null
        });
      },
      
      trackEngagement: () => {
        const start = get().briefEngagementStart;
        if (start) {
          const duration = Date.now() - start;
          trackEvent('brief_engagement', { duration });
        }
      },
      
      updateCache: (type, data) => {
        const cache = get()[`${type}Cache`];
        cache.set(getCacheKey(type), data);
        set({ [`${type}Cache`]: new Map(cache) });
      }
    }),
    {
      name: 'intelligence-storage',
      partialize: (state) => ({
        briefDismissed: state.briefDismissed,
        briefEnabled: state.briefEnabled,
        autoShowBrief: state.autoShowBrief,
        preferredViewMode: state.preferredViewMode
      })
    }
  )
);
```

---

## 6. Real-World Component Examples

### Weekly Brief Overlay Component
```typescript
// components/intelligence/WeeklyBriefOverlay.tsx
import { motion, AnimatePresence } from 'framer-motion';
import { useWeeklyBrief } from '@/hooks/useIntelligence';
import { useIntelligenceStore } from '@/stores/intelligenceStore';

export const WeeklyBriefOverlay: React.FC = () => {
  const { userId } = useAuth();
  const { data: brief, isLoading } = useWeeklyBrief(userId);
  const { 
    briefDismissed, 
    autoShowBrief,
    dismissBrief,
    trackEngagement 
  } = useIntelligenceStore();
  
  const [showOverlay, setShowOverlay] = useState(false);
  const [scrollDepth, setScrollDepth] = useState(0);
  
  // Auto-show logic
  useEffect(() => {
    if (brief && !briefDismissed && autoShowBrief && isFirstLoginThisWeek()) {
      setShowOverlay(true);
      markBriefOpened(brief.id);
    }
  }, [brief, briefDismissed, autoShowBrief]);
  
  // Track scroll depth
  useEffect(() => {
    if (!showOverlay) return;
    
    const handleScroll = (e: Event) => {
      const element = e.target as HTMLElement;
      const depth = (element.scrollTop / element.scrollHeight) * 100;
      setScrollDepth(Math.max(scrollDepth, depth));
    };
    
    const container = document.getElementById('brief-content');
    container?.addEventListener('scroll', handleScroll);
    
    return () => container?.removeEventListener('scroll', handleScroll);
  }, [showOverlay, scrollDepth]);
  
  // Track engagement on unmount
  useEffect(() => {
    return () => {
      if (showOverlay) {
        trackEngagement();
      }
    };
  }, [showOverlay]);
  
  const handleDismiss = (permanent = false) => {
    // Track detailed engagement
    trackEvent('brief_interaction', {
      scroll_depth: scrollDepth,
      sections_viewed: getSectionsViewed(),
      time_spent: getTimeSpent(),
      permanent_dismiss: permanent
    });
    
    dismissBrief(permanent);
    setShowOverlay(false);
  };
  
  if (!brief || isLoading) return null;
  
  return (
    <AnimatePresence>
      {showOverlay && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="absolute inset-4 md:inset-8 lg:inset-16 
                       bg-white dark:bg-gray-900 rounded-2xl 
                       shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 bg-gradient-to-r 
                          from-blue-600 to-purple-600 p-6 text-white">
              <div className="flex justify-between items-center">
                <div>
                  <h1 className="text-3xl font-bold">
                    {brief.greeting.title}
                  </h1>
                  <p className="mt-2 opacity-90">
                    Week of {formatDate(brief.week_of)}
                  </p>
                </div>
                
                <button
                  onClick={() => handleDismiss(false)}
                  className="p-2 hover:bg-white/20 rounded-lg transition"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div 
              id="brief-content"
              className="h-[calc(100%-200px)] overflow-y-auto p-6 space-y-8"
            >
              {/* Main Story */}
              <BriefSection
                icon={<BookOpen />}
                title={brief.main_story.title}
                content={brief.main_story.narrative}
                highlights={brief.main_story.key_moments}
              />
              
              {/* Discoveries */}
              <BriefSection
                icon={<Sparkles />}
                title="This Week's Discoveries"
                items={brief.discoveries.items}
              />
              
              {/* Experiments */}
              <BriefSection
                icon={<Flask />}
                title="Health Experiments to Try"
                experiments={brief.experiments.suggestions}
              />
              
              {/* Body System Spotlight */}
              <BriefSection
                icon={<Heart />}
                title={`Spotlight: ${brief.spotlight.system}`}
                content={brief.spotlight.analysis}
                score={brief.spotlight.score}
              />
              
              {/* Week Stats */}
              <WeekStats stats={brief.week_stats} />
              
              {/* Looking Ahead */}
              <BriefSection
                icon={<ArrowRight />}
                title="Looking Ahead"
                content={brief.looking_ahead.preview}
                recommendations={brief.looking_ahead.recommendations}
              />
            </div>
            
            {/* Footer Actions */}
            <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800 
                          p-4 flex justify-between items-center">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      handleDismiss(true);
                    }
                  }}
                />
                <span className="text-sm text-gray-600">
                  Don't show weekly briefs anymore
                </span>
              </label>
              
              <div className="flex space-x-2">
                <button
                  onClick={() => shareBreif(brief)}
                  className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
                >
                  Share
                </button>
                <button
                  onClick={() => handleDismiss(false)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg 
                           hover:bg-blue-700"
                >
                  Got it, thanks!
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
```

### Health Velocity Dashboard Widget
```typescript
// components/intelligence/HealthVelocityWidget.tsx
import { Line } from 'react-chartjs-2';
import { useHealthVelocity } from '@/hooks/useIntelligence';

export const HealthVelocityWidget: React.FC = () => {
  const { userId } = useAuth();
  const [timeRange, setTimeRange] = useState('7D');
  const { data, isLoading, error } = useHealthVelocity(userId, timeRange);
  
  if (isLoading) return <VelocitySkeleton />;
  if (error) return <VelocityError onRetry={() => refetch()} />;
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };
  
  const getTrendIcon = (trend: string) => {
    switch(trend) {
      case 'improving': return <TrendingUp className="text-green-500" />;
      case 'declining': return <TrendingDown className="text-red-500" />;
      default: return <Minus className="text-gray-500" />;
    }
  };
  
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">Health Velocity</h3>
          <p className="text-sm text-gray-500">
            Your health momentum over time
          </p>
        </div>
        
        {/* Time Range Selector */}
        <div className="flex space-x-1">
          {['7D', '30D', '90D'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-sm rounded-lg transition
                ${timeRange === range 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 hover:bg-gray-300'}`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>
      
      {/* Score Display */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className={`text-4xl font-bold ${getScoreColor(data.score)}`}>
            {data.score}
          </div>
          <div className="flex items-center space-x-2">
            {getTrendIcon(data.trend)}
            <span className="text-sm font-medium">
              {data.trend}
            </span>
          </div>
        </div>
        
        {/* Momentum Indicator */}
        <div className="text-right">
          <div className="text-sm text-gray-500">Momentum</div>
          <div className="text-lg font-semibold">
            {data.momentum > 0 ? '+' : ''}{data.momentum}%
          </div>
        </div>
      </div>
      
      {/* Sparkline Chart */}
      <div className="h-32 mb-4">
        <Line
          data={{
            labels: generateDateLabels(timeRange),
            datasets: [{
              data: data.sparkline,
              borderColor: 'rgb(59, 130, 246)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              tension: 0.4,
              fill: true
            }]
          }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  title: (context) => formatDate(context[0].label),
                  label: (context) => `Score: ${context.parsed.y}`
                }
              }
            },
            scales: {
              x: { display: false },
              y: { 
                display: false,
                min: 0,
                max: 100
              }
            }
          }}
        />
      </div>
      
      {/* Recommendations */}
      <div className="border-t pt-4">
        <h4 className="text-sm font-semibold mb-2">Recommendations</h4>
        <ul className="space-y-2">
          {data.recommendations.slice(0, 3).map((rec, i) => (
            <li key={i} className="flex items-start space-x-2">
              <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
              <span className="text-sm text-gray-600">{rec}</span>
            </li>
          ))}
        </ul>
      </div>
      
      {/* View Details Link */}
      <button className="mt-4 text-sm text-blue-600 hover:text-blue-700">
        View detailed analysis →
      </button>
    </div>
  );
};
```

### Body Systems Grid Component
```typescript
// components/intelligence/BodySystemsGrid.tsx
export const BodySystemsGrid: React.FC = () => {
  const { userId } = useAuth();
  const systems = useBodySystems(userId);
  
  const getSystemIcon = (system: string) => {
    const icons = {
      head: Brain,
      chest: Heart,
      digestive: Stomach,
      arms: Hand,
      legs: Footprints,
      skin: Shield,
      mental: Mind
    };
    return icons[system];
  };
  
  const getStatusColor = (status: string) => {
    switch(status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'attention': return 'bg-yellow-100 text-yellow-800';
      case 'concern': return 'bg-red-100 text-red-800';
    }
  };
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Object.entries(systems).map(([name, data]) => {
        const Icon = getSystemIcon(name);
        
        return (
          <motion.div
            key={name}
            whileHover={{ scale: 1.05 }}
            className="bg-white dark:bg-gray-800 rounded-xl p-4 
                     shadow-md hover:shadow-lg transition cursor-pointer"
            onClick={() => openSystemDetails(name, data)}
          >
            {/* Icon & Score */}
            <div className="flex justify-between items-start mb-3">
              <Icon className="w-8 h-8 text-gray-600" />
              <div className="text-2xl font-bold">
                {data.score}
              </div>
            </div>
            
            {/* System Name */}
            <h4 className="font-semibold capitalize mb-2">{name}</h4>
            
            {/* Status Badge */}
            <span className={`inline-block px-2 py-1 text-xs rounded-full
              ${getStatusColor(data.status)}`}>
              {data.status}
            </span>
            
            {/* Issues Count */}
            {data.issues.length > 0 && (
              <div className="mt-2 text-xs text-gray-500">
                {data.issues.length} issue{data.issues.length > 1 ? 's' : ''}
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
};
```

---

## 7. Performance Optimization

### Lazy Loading Intelligence Components
```typescript
// Lazy load heavy components
const WeeklyBriefOverlay = lazy(() => 
  import('./components/intelligence/WeeklyBriefOverlay')
);

const BodySystemsGrid = lazy(() => 
  import('./components/intelligence/BodySystemsGrid')
);

// Use with Suspense
<Suspense fallback={<IntelligenceSkeleton />}>
  <WeeklyBriefOverlay />
</Suspense>
```

### Virtualization for Timeline
```typescript
import { FixedSizeList } from 'react-window';

export const HealthTimeline: React.FC = () => {
  const { data: timeline } = useTimeline(userId);
  
  const Row = ({ index, style }) => (
    <div style={style}>
      <TimelineEvent event={timeline.events[index]} />
    </div>
  );
  
  return (
    <FixedSizeList
      height={600}
      itemCount={timeline.events.length}
      itemSize={120}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

### Prefetching Strategy
```typescript
// Prefetch intelligence data based on user behavior
export const usePrefetchIntelligence = () => {
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  
  // Prefetch on dashboard mount
  useEffect(() => {
    // Prefetch critical data
    queryClient.prefetchQuery(
      ['health-velocity', userId, '7D'],
      () => fetchHealthVelocity(userId, '7D')
    );
    
    queryClient.prefetchQuery(
      ['body-systems-critical', userId],
      () => fetchCriticalSystems(userId)
    );
    
    // Prefetch weekly brief if it's Monday-Wednesday
    const day = new Date().getDay();
    if (day >= 1 && day <= 3) {
      queryClient.prefetchQuery(
        ['weekly-brief', userId, getCurrentWeekMonday()],
        () => fetchWeeklyBrief(userId)
      );
    }
  }, []);
  
  // Prefetch on hover
  const prefetchOnHover = (feature: string) => {
    switch(feature) {
      case 'timeline':
        queryClient.prefetchQuery(['timeline', userId, 'month']);
        break;
      case 'patterns':
        queryClient.prefetchQuery(['patterns', userId]);
        break;
      case 'doctor':
        queryClient.prefetchQuery(['doctor-readiness', userId]);
        break;
    }
  };
  
  return { prefetchOnHover };
};
```

---

## 8. Error Handling & Fallbacks

### Graceful Degradation
```typescript
export const IntelligenceFeature: React.FC = () => {
  const { data, error, isLoading } = useIntelligence();
  
  // Fallback to cached data on error
  const fallbackData = useMemo(() => {
    if (error) {
      return getCachedIntelligence();
    }
    return null;
  }, [error]);
  
  // Show offline-first UI
  if (error && !fallbackData) {
    return (
      <OfflineIntelligence 
        message="Intelligence features temporarily unavailable"
        showRetry={true}
        onRetry={() => refetch()}
      />
    );
  }
  
  // Use fallback data with indicator
  if (error && fallbackData) {
    return (
      <>
        <StaleDataBanner />
        <IntelligenceDisplay data={fallbackData} />
      </>
    );
  }
  
  return <IntelligenceDisplay data={data} />;
};
```

### Retry Logic with Exponential Backoff
```typescript
const useIntelligenceWithRetry = (userId: string) => {
  return useQuery({
    queryKey: ['intelligence', userId],
    queryFn: () => fetchIntelligence(userId),
    retry: (failureCount, error) => {
      // Don't retry on 4xx errors
      if (error.status >= 400 && error.status < 500) {
        return false;
      }
      // Retry up to 3 times with exponential backoff
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });
};
```

---

## Summary

This guide provides everything needed to implement the intelligence features:

1. **Database Structure**: All tables with field descriptions and relationships
2. **Feature Purposes**: What each intelligence feature does and why
3. **API Reference**: Complete endpoint documentation with request/response formats
4. **Implementation Patterns**: Production-ready React/TypeScript code
5. **State Management**: Zustand store with persistence
6. **Real Components**: Full component examples with animations and interactions
7. **Performance**: Lazy loading, virtualization, and prefetching strategies
8. **Error Handling**: Graceful degradation and retry mechanisms

The system is designed to scale to 500k+ users with:
- Multi-layer caching (Browser → CDN → Redis → Database)
- Progressive loading patterns
- Batch processing with retry mechanisms
- Anonymous pattern matching for privacy
- Engagement tracking for optimization

All intelligence is generated by LLMs from first principles - no hardcoded algorithms.