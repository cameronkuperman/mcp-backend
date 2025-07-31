# 🧠 Complete Frontend Guide: Health Intelligence System

## Table of Contents
1. [System Overview](#system-overview)
2. [API Architecture](#api-architecture)
3. [Data Flow](#data-flow)
4. [Component Structure](#component-structure)
5. [Implementation Guide](#implementation-guide)
6. [State Management](#state-management)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)
9. [UI/UX Best Practices](#uiux-best-practices)
10. [Testing Strategy](#testing-strategy)

---

## 🎯 System Overview

The Health Intelligence system analyzes user health data to provide:
- **Key Insights**: Patterns and observations from health stories
- **Health Predictions**: Future health events based on patterns
- **Shadow Patterns**: Things users usually track but haven't mentioned
- **Strategic Moves**: Actionable recommendations

### How It Works:
1. User generates a weekly health story (prerequisite)
2. AI analyzes the story + historical health data
3. Generates 4 types of intelligence components
4. Stores everything in database for quick retrieval
5. Frontend displays in organized sections

---

## 🏗️ API Architecture

### Base URL Structure
```
https://api.yourapp.com/api/
```

### Two Approaches Available:

#### 1. Unified Generation (Recommended)
```javascript
POST /api/generate-weekly-analysis
```
- Generates ALL components in one request
- More efficient for full refresh
- Single loading state
- Atomic operation (all succeed or all fail)

#### 2. Component-by-Component
```javascript
POST /api/generate-insights/{user_id}
POST /api/generate-predictions/{user_id}
POST /api/generate-shadow-patterns/{user_id}
POST /api/generate-strategies/{user_id}
```
- Generate individual components
- Good for partial updates
- More granular error handling
- Can show progressive loading

### Data Retrieval Endpoints
```javascript
GET /api/health-analysis/{user_id}?week_of=2025-01-27
GET /api/insights/{user_id}?week_of=2025-01-27
GET /api/predictions/{user_id}?week_of=2025-01-27
GET /api/shadow-patterns/{user_id}?week_of=2025-01-27
GET /api/strategies/{user_id}?week_of=2025-01-27
```

---

## 📊 Data Flow

### 1. Initial Page Load
```mermaid
User visits Intelligence page
    ↓
Check localStorage for cached data
    ↓
If cache valid (<24hrs) → Display cached
    ↓
Else → Fetch from GET /api/health-analysis/{user_id}
    ↓
Display stored data
    ↓
Check if refresh needed (>24hrs old)
    ↓
If yes → Show "Update Available" indicator
```

### 2. Manual Refresh Flow
```mermaid
User clicks "Refresh Intelligence"
    ↓
Check refresh limit (10/week)
    ↓
If allowed → POST /api/generate-weekly-analysis
    ↓
Show loading states (30-90 seconds)
    ↓
Handle response based on status
    ↓
Update UI with new data
    ↓
Update cache
    ↓
Update refresh count display
```

---

## 🧩 Component Structure

### Recommended File Structure
```
src/
├── pages/
│   └── Intelligence/
│       ├── index.tsx                    // Main page
│       ├── Intelligence.styles.ts       // Styled components
│       └── Intelligence.types.ts        // TypeScript interfaces
├── components/
│   └── Intelligence/
│       ├── InsightsSection/
│       │   ├── index.tsx
│       │   ├── InsightCard.tsx
│       │   └── InsightCard.styles.ts
│       ├── PredictionsSection/
│       │   ├── index.tsx
│       │   ├── PredictionCard.tsx
│       │   └── PredictionTimeline.tsx
│       ├── ShadowPatternsSection/
│       │   ├── index.tsx
│       │   └── PatternCard.tsx
│       ├── StrategiesSection/
│       │   ├── index.tsx
│       │   ├── StrategyCard.tsx
│       │   └── StrategyChecklist.tsx
│       └── RefreshButton/
│           ├── index.tsx
│           └── RefreshButton.styles.ts
├── hooks/
│   ├── useIntelligence.ts              // Main data hook
│   ├── useRefreshLimit.ts              // Track refresh limits
│   └── useIntelligenceCache.ts         // Cache management
├── services/
│   └── intelligence.service.ts         // API calls
├── store/
│   └── intelligence/
│       ├── intelligence.slice.ts       // Redux/Zustand slice
│       └── intelligence.types.ts       // State types
└── utils/
    ├── intelligence.utils.ts           // Helper functions
    └── dateUtils.ts                    // Week calculations
```

---

## 💻 Implementation Guide

### 1. TypeScript Interfaces
```typescript
// Intelligence.types.ts
export interface HealthInsight {
  id: string;
  insight_type: 'positive' | 'warning' | 'neutral';
  title: string;
  description: string;
  confidence: number;
  metadata?: {
    related_symptoms?: string[];
    body_parts?: string[];
  };
  created_at: string;
}

export interface HealthPrediction {
  id: string;
  event_description: string;
  probability: number;
  timeframe: string;
  preventable: boolean;
  reasoning: string;
  suggested_actions: string[];
  status?: 'active' | 'occurred' | 'prevented' | 'expired';
}

export interface ShadowPattern {
  id: string;
  pattern_name: string;
  pattern_category: string;
  last_seen_description: string;
  significance: 'high' | 'medium' | 'low';
  last_mentioned_date?: string;
  days_missing: number;
}

export interface StrategicMove {
  id: string;
  strategy: string;
  strategy_type: 'discovery' | 'pattern' | 'prevention' | 'optimization';
  priority: number;
  rationale: string;
  expected_outcome: string;
  completion_status: 'pending' | 'in_progress' | 'completed' | 'skipped';
  completed_at?: string;
}

export interface IntelligenceData {
  status: 'success' | 'no_story' | 'insufficient_data' | 'fallback' | 'error';
  story_id?: string;
  insights: HealthInsight[];
  predictions: HealthPrediction[];
  shadow_patterns: ShadowPattern[];
  strategies: StrategicMove[];
  week_of: string;
  generated_at: string;
  message?: string;
  error?: string;
}

export interface RefreshLimitInfo {
  can_refresh: boolean;
  refreshes_used: number;
  refreshes_remaining: number;
}
```

### 2. API Service Layer
```typescript
// intelligence.service.ts
import axios from 'axios';

class IntelligenceService {
  private baseURL = process.env.REACT_APP_API_URL;

  // Get current week's Monday in ISO format
  private getCurrentWeekMonday(): string {
    const today = new Date();
    const day = today.getDay();
    const diff = today.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(today.setDate(diff));
    return monday.toISOString().split('T')[0];
  }

  // Fetch existing intelligence data
  async getIntelligenceData(userId: string): Promise<IntelligenceData> {
    try {
      const weekOf = this.getCurrentWeekMonday();
      const response = await axios.get(
        `${this.baseURL}/api/health-analysis/${userId}`,
        { params: { week_of: weekOf } }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch intelligence data:', error);
      throw error;
    }
  }

  // Generate fresh intelligence (all components)
  async generateIntelligence(
    userId: string,
    forceRefresh: boolean = false
  ): Promise<IntelligenceData> {
    try {
      const response = await axios.post(
        `${this.baseURL}/api/generate-weekly-analysis`,
        {
          user_id: userId,
          force_refresh: forceRefresh,
          include_predictions: true,
          include_patterns: true,
          include_strategies: true
        },
        {
          timeout: 90000 // 90 second timeout
        }
      );
      return response.data;
    } catch (error) {
      console.error('Failed to generate intelligence:', error);
      throw error;
    }
  }

  // Generate individual components
  async generateInsights(userId: string) {
    const response = await axios.post(
      `${this.baseURL}/api/generate-insights/${userId}`
    );
    return response.data;
  }

  async generatePredictions(userId: string) {
    const response = await axios.post(
      `${this.baseURL}/api/generate-predictions/${userId}`
    );
    return response.data;
  }

  async generateShadowPatterns(userId: string) {
    const response = await axios.post(
      `${this.baseURL}/api/generate-shadow-patterns/${userId}`
    );
    return response.data;
  }

  async generateStrategies(userId: string) {
    const response = await axios.post(
      `${this.baseURL}/api/generate-strategies/${userId}`
    );
    return response.data;
  }

  // Update strategy status
  async updateStrategyStatus(
    moveId: string,
    status: string,
    userId: string
  ) {
    const response = await axios.put(
      `${this.baseURL}/api/strategic-moves/${moveId}/status`,
      null,
      { params: { status, user_id: userId } }
    );
    return response.data;
  }
}

export default new IntelligenceService();
```

### 3. Custom Hook for Intelligence
```typescript
// useIntelligence.ts
import { useState, useEffect, useCallback } from 'react';
import { useUser } from '@/hooks/useUser';
import intelligenceService from '@/services/intelligence.service';
import { useIntelligenceCache } from './useIntelligenceCache';

export const useIntelligence = () => {
  const { user } = useUser();
  const { getCached, setCached, isCacheValid } = useIntelligenceCache();
  
  const [data, setData] = useState<IntelligenceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshLimit, setRefreshLimit] = useState({
    can_refresh: true,
    refreshes_remaining: 10
  });

  // Load initial data
  useEffect(() => {
    if (!user?.id) return;

    const loadData = async () => {
      try {
        setLoading(true);
        
        // Check cache first
        const cached = getCached();
        if (cached && isCacheValid()) {
          setData(cached);
          setLoading(false);
          return;
        }

        // Fetch from API
        const response = await intelligenceService.getIntelligenceData(user.id);
        setData(response);
        setCached(response);
        
        // Extract refresh limit from response
        if (response.refreshes_remaining !== undefined) {
          setRefreshLimit({
            can_refresh: response.refreshes_remaining > 0,
            refreshes_remaining: response.refreshes_remaining
          });
        }
      } catch (err) {
        setError('Failed to load intelligence data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user?.id]);

  // Refresh intelligence data
  const refreshIntelligence = useCallback(async () => {
    if (!user?.id || !refreshLimit.can_refresh) return;

    try {
      setRefreshing(true);
      setError(null);

      const response = await intelligenceService.generateIntelligence(
        user.id,
        true // force refresh
      );

      // Handle different statuses
      switch (response.status) {
        case 'success':
          setData(response);
          setCached(response);
          setRefreshLimit(prev => ({
            can_refresh: prev.refreshes_remaining > 1,
            refreshes_remaining: Math.max(0, prev.refreshes_remaining - 1)
          }));
          break;
        
        case 'no_story':
          setError('Please generate a health story first');
          break;
        
        case 'insufficient_data':
          setError('Need more health tracking data');
          break;
        
        case 'fallback':
          setData(response);
          setCached(response);
          console.warn('Using simplified analysis');
          break;
        
        case 'error':
          setError(response.message || 'Failed to generate intelligence');
          break;
      }
    } catch (err: any) {
      if (err.response?.status === 429) {
        setError('Weekly refresh limit reached');
        setRefreshLimit({ can_refresh: false, refreshes_remaining: 0 });
      } else {
        setError('Failed to refresh intelligence');
      }
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  }, [user?.id, refreshLimit.can_refresh]);

  // Refresh individual component
  const refreshComponent = useCallback(async (
    component: 'insights' | 'predictions' | 'patterns' | 'strategies'
  ) => {
    if (!user?.id) return;

    try {
      setRefreshing(true);
      
      let response;
      switch (component) {
        case 'insights':
          response = await intelligenceService.generateInsights(user.id);
          if (response.status === 'success' && data) {
            setData({ ...data, insights: response.insights });
          }
          break;
        
        case 'predictions':
          response = await intelligenceService.generatePredictions(user.id);
          if (response.status === 'success' && data) {
            setData({ ...data, predictions: response.predictions });
          }
          break;
        
        case 'patterns':
          response = await intelligenceService.generateShadowPatterns(user.id);
          if (response.status === 'success' && data) {
            setData({ ...data, shadow_patterns: response.shadow_patterns });
          }
          break;
        
        case 'strategies':
          response = await intelligenceService.generateStrategies(user.id);
          if (response.status === 'success' && data) {
            setData({ ...data, strategies: response.strategies });
          }
          break;
      }
    } catch (err) {
      console.error(`Failed to refresh ${component}:`, err);
      setError(`Failed to update ${component}`);
    } finally {
      setRefreshing(false);
    }
  }, [user?.id, data]);

  return {
    data,
    loading,
    refreshing,
    error,
    refreshLimit,
    refreshIntelligence,
    refreshComponent,
    isDataStale: data ? 
      (new Date().getTime() - new Date(data.generated_at).getTime()) > 86400000 
      : false
  };
};
```

### 4. Main Intelligence Page Component
```typescript
// pages/Intelligence/index.tsx
import React from 'react';
import { useIntelligence } from '@/hooks/useIntelligence';
import { 
  InsightsSection,
  PredictionsSection,
  ShadowPatternsSection,
  StrategiesSection,
  RefreshButton
} from '@/components/Intelligence';
import { 
  PageContainer,
  Header,
  RefreshContainer,
  LoadingOverlay,
  ErrorBanner,
  EmptyState
} from './Intelligence.styles';

export const IntelligencePage: React.FC = () => {
  const {
    data,
    loading,
    refreshing,
    error,
    refreshLimit,
    refreshIntelligence,
    isDataStale
  } = useIntelligence();

  // Handle initial loading
  if (loading && !data) {
    return (
      <PageContainer>
        <LoadingOverlay>
          <div className="spinner" />
          <p>Loading your health intelligence...</p>
        </LoadingOverlay>
      </PageContainer>
    );
  }

  // Handle no data state
  if (!data && !loading) {
    return (
      <PageContainer>
        <EmptyState>
          <h2>No Intelligence Data Available</h2>
          <p>Generate a health story first to see your intelligence insights.</p>
          <button onClick={() => window.location.href = '/stories'}>
            Go to Stories
          </button>
        </EmptyState>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <Header>
        <div>
          <h1>Health Intelligence</h1>
          <p>AI-powered insights from your health data</p>
          {isDataStale && (
            <span className="stale-indicator">
              Updated {new Date(data?.generated_at || '').toLocaleDateString()}
            </span>
          )}
        </div>
        
        <RefreshContainer>
          <RefreshButton
            onClick={refreshIntelligence}
            loading={refreshing}
            disabled={!refreshLimit.can_refresh || refreshing}
            refreshesRemaining={refreshLimit.refreshes_remaining}
            isDataStale={isDataStale}
          />
        </RefreshContainer>
      </Header>

      {error && (
        <ErrorBanner>
          <p>{error}</p>
          <button onClick={() => setError(null)}>Dismiss</button>
        </ErrorBanner>
      )}

      {refreshing && (
        <LoadingOverlay className="refresh-overlay">
          <div className="progress-indicator">
            <p>Analyzing your health patterns...</p>
            <p className="sub-text">This may take 30-90 seconds</p>
          </div>
        </LoadingOverlay>
      )}

      {data && (
        <>
          <InsightsSection 
            insights={data.insights}
            loading={refreshing}
          />
          
          <PredictionsSection 
            predictions={data.predictions}
            loading={refreshing}
          />
          
          <ShadowPatternsSection 
            patterns={data.shadow_patterns}
            loading={refreshing}
          />
          
          <StrategiesSection 
            strategies={data.strategies}
            loading={refreshing}
            onStatusUpdate={(moveId, status) => 
              intelligenceService.updateStrategyStatus(moveId, status, user.id)
            }
          />
        </>
      )}
    </PageContainer>
  );
};
```

### 5. Refresh Button Component
```typescript
// components/Intelligence/RefreshButton/index.tsx
import React from 'react';
import { Button, RefreshIcon, LimitText } from './RefreshButton.styles';

interface RefreshButtonProps {
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
  refreshesRemaining: number;
  isDataStale: boolean;
}

export const RefreshButton: React.FC<RefreshButtonProps> = ({
  onClick,
  loading,
  disabled,
  refreshesRemaining,
  isDataStale
}) => {
  const getButtonText = () => {
    if (loading) return 'Generating Intelligence...';
    if (refreshesRemaining === 0) return 'Refresh Limit Reached';
    if (isDataStale) return 'Update Available';
    return 'Refresh Intelligence';
  };

  return (
    <div>
      <Button
        onClick={onClick}
        disabled={disabled}
        $loading={loading}
        $hasUpdate={isDataStale}
      >
        <RefreshIcon className={loading ? 'spinning' : ''} />
        {getButtonText()}
      </Button>
      
      {refreshesRemaining > 0 && refreshesRemaining < 10 && (
        <LimitText>
          {refreshesRemaining} refresh{refreshesRemaining !== 1 ? 'es' : ''} remaining this week
        </LimitText>
      )}
    </div>
  );
};
```

---

## 🗄️ State Management

### Using Redux Toolkit
```typescript
// store/intelligence/intelligence.slice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import intelligenceService from '@/services/intelligence.service';

export const fetchIntelligence = createAsyncThunk(
  'intelligence/fetch',
  async (userId: string) => {
    return await intelligenceService.getIntelligenceData(userId);
  }
);

export const refreshIntelligence = createAsyncThunk(
  'intelligence/refresh',
  async ({ userId, forceRefresh }: { userId: string; forceRefresh: boolean }) => {
    return await intelligenceService.generateIntelligence(userId, forceRefresh);
  }
);

const intelligenceSlice = createSlice({
  name: 'intelligence',
  initialState: {
    data: null as IntelligenceData | null,
    loading: false,
    refreshing: false,
    error: null as string | null,
    refreshLimit: {
      can_refresh: true,
      refreshes_remaining: 10
    }
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateStrategyStatus: (state, action) => {
      if (state.data) {
        const strategy = state.data.strategies.find(
          s => s.id === action.payload.moveId
        );
        if (strategy) {
          strategy.completion_status = action.payload.status;
        }
      }
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch intelligence
      .addCase(fetchIntelligence.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchIntelligence.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload;
      })
      .addCase(fetchIntelligence.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load intelligence';
      })
      
      // Refresh intelligence
      .addCase(refreshIntelligence.pending, (state) => {
        state.refreshing = true;
        state.error = null;
      })
      .addCase(refreshIntelligence.fulfilled, (state, action) => {
        state.refreshing = false;
        if (action.payload.status === 'success') {
          state.data = action.payload;
          state.refreshLimit.refreshes_remaining = Math.max(
            0, 
            state.refreshLimit.refreshes_remaining - 1
          );
        } else {
          state.error = action.payload.message || 'Failed to refresh';
        }
      })
      .addCase(refreshIntelligence.rejected, (state, action) => {
        state.refreshing = false;
        state.error = action.error.message || 'Failed to refresh intelligence';
      });
  }
});

export const { clearError, updateStrategyStatus } = intelligenceSlice.actions;
export default intelligenceSlice.reducer;
```

### Using Zustand (Alternative)
```typescript
// store/useIntelligenceStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import intelligenceService from '@/services/intelligence.service';

interface IntelligenceStore {
  data: IntelligenceData | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refreshLimit: {
    can_refresh: boolean;
    refreshes_remaining: number;
  };
  
  // Actions
  fetchIntelligence: (userId: string) => Promise<void>;
  refreshIntelligence: (userId: string) => Promise<void>;
  clearError: () => void;
  updateStrategyStatus: (moveId: string, status: string) => void;
}

export const useIntelligenceStore = create<IntelligenceStore>()(
  devtools(
    persist(
      (set, get) => ({
        data: null,
        loading: false,
        refreshing: false,
        error: null,
        refreshLimit: {
          can_refresh: true,
          refreshes_remaining: 10
        },

        fetchIntelligence: async (userId) => {
          set({ loading: true, error: null });
          try {
            const data = await intelligenceService.getIntelligenceData(userId);
            set({ data, loading: false });
          } catch (error) {
            set({ 
              error: 'Failed to load intelligence', 
              loading: false 
            });
          }
        },

        refreshIntelligence: async (userId) => {
          const { refreshLimit } = get();
          if (!refreshLimit.can_refresh) return;

          set({ refreshing: true, error: null });
          try {
            const data = await intelligenceService.generateIntelligence(userId, true);
            
            if (data.status === 'success') {
              set({
                data,
                refreshing: false,
                refreshLimit: {
                  ...refreshLimit,
                  refreshes_remaining: Math.max(0, refreshLimit.refreshes_remaining - 1)
                }
              });
            } else {
              set({
                error: data.message || 'Failed to refresh',
                refreshing: false
              });
            }
          } catch (error) {
            set({ 
              error: 'Failed to refresh intelligence', 
              refreshing: false 
            });
          }
        },

        clearError: () => set({ error: null }),

        updateStrategyStatus: (moveId, status) => {
          const { data } = get();
          if (!data) return;

          const updatedStrategies = data.strategies.map(strategy =>
            strategy.id === moveId 
              ? { ...strategy, completion_status: status }
              : strategy
          );

          set({
            data: { ...data, strategies: updatedStrategies }
          });
        }
      }),
      {
        name: 'intelligence-storage',
        partialize: (state) => ({ 
          data: state.data,
          refreshLimit: state.refreshLimit 
        })
      }
    )
  )
);
```

---

## 🚨 Error Handling

### Comprehensive Error Handling
```typescript
// utils/intelligence.utils.ts
export const handleIntelligenceError = (error: any): string => {
  // API error responses
  if (error.response) {
    switch (error.response.status) {
      case 404:
        return 'No health story found. Please generate a story first.';
      case 429:
        return 'Weekly refresh limit reached. Try again next week.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return error.response.data?.message || 'An error occurred';
    }
  }
  
  // Network errors
  if (error.request) {
    return 'Network error. Please check your connection.';
  }
  
  // Timeout errors
  if (error.code === 'ECONNABORTED') {
    return 'Request timed out. Intelligence generation can take up to 90 seconds.';
  }
  
  return 'An unexpected error occurred';
};

// Retry logic for failed requests
export const retryWithBackoff = async (
  fn: () => Promise<any>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<any> => {
  try {
    return await fn();
  } catch (error) {
    if (maxRetries <= 0) throw error;
    
    await new Promise(resolve => setTimeout(resolve, delay));
    return retryWithBackoff(fn, maxRetries - 1, delay * 2);
  }
};
```

### Error Boundary Component
```typescript
// components/ErrorBoundary/IntelligenceErrorBoundary.tsx
import React from 'react';

interface State {
  hasError: boolean;
  error: Error | null;
}

export class IntelligenceErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = {
    hasError: false,
    error: null
  };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Intelligence page error:', error, errorInfo);
    // Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <p>We couldn't load your health intelligence.</p>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## ⚡ Performance Optimization

### 1. Lazy Loading Components
```typescript
// pages/Intelligence/index.tsx
import React, { lazy, Suspense } from 'react';

const InsightsSection = lazy(() => 
  import('@/components/Intelligence/InsightsSection')
);
const PredictionsSection = lazy(() => 
  import('@/components/Intelligence/PredictionsSection')
);
const ShadowPatternsSection = lazy(() => 
  import('@/components/Intelligence/ShadowPatternsSection')
);
const StrategiesSection = lazy(() => 
  import('@/components/Intelligence/StrategiesSection')
);

// Use with Suspense
<Suspense fallback={<SectionLoader />}>
  <InsightsSection insights={data.insights} />
</Suspense>
```

### 2. Optimistic Updates
```typescript
// When updating strategy status
const handleStrategyStatusUpdate = async (moveId: string, newStatus: string) => {
  // Optimistically update UI
  setData(prev => ({
    ...prev,
    strategies: prev.strategies.map(s =>
      s.id === moveId ? { ...s, completion_status: newStatus } : s
    )
  }));

  try {
    await intelligenceService.updateStrategyStatus(moveId, newStatus, userId);
  } catch (error) {
    // Revert on failure
    setData(prev => ({
      ...prev,
      strategies: prev.strategies.map(s =>
        s.id === moveId ? { ...s, completion_status: s.completion_status } : s
      )
    }));
    showError('Failed to update strategy');
  }
};
```

### 3. Virtual Scrolling for Large Lists
```typescript
// For sections with many items
import { VariableSizeList } from 'react-window';

const VirtualizedStrategiesList = ({ strategies }) => {
  const getItemSize = (index: number) => {
    // Calculate height based on content
    return strategies[index].strategy.length > 100 ? 120 : 80;
  };

  return (
    <VariableSizeList
      height={600}
      itemCount={strategies.length}
      itemSize={getItemSize}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <StrategyCard strategy={strategies[index]} />
        </div>
      )}
    </VariableSizeList>
  );
};
```

### 4. Caching Strategy
```typescript
// useIntelligenceCache.ts
export const useIntelligenceCache = () => {
  const CACHE_KEY = 'health_intelligence';
  const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

  const getCached = (): IntelligenceData | null => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return null;

      const { data, timestamp, weekOf } = JSON.parse(cached);
      
      // Check if cache is for current week
      const currentWeek = getCurrentWeekMonday();
      if (weekOf !== currentWeek) {
        localStorage.removeItem(CACHE_KEY);
        return null;
      }

      return data;
    } catch {
      return null;
    }
  };

  const setCached = (data: IntelligenceData) => {
    try {
      const cacheData = {
        data,
        timestamp: Date.now(),
        weekOf: getCurrentWeekMonday()
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
    } catch (error) {
      console.error('Failed to cache intelligence data:', error);
    }
  };

  const isCacheValid = (): boolean => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return false;

      const { timestamp, weekOf } = JSON.parse(cached);
      const age = Date.now() - timestamp;
      const currentWeek = getCurrentWeekMonday();

      return age < CACHE_DURATION && weekOf === currentWeek;
    } catch {
      return false;
    }
  };

  return { getCached, setCached, isCacheValid };
};
```

---

## 🎨 UI/UX Best Practices

### 1. Loading States
```typescript
// components/Intelligence/LoadingStates.tsx
export const InsightSkeleton = () => (
  <div className="skeleton-card">
    <div className="skeleton-line w-60" />
    <div className="skeleton-line w-full" />
    <div className="skeleton-line w-80" />
  </div>
);

export const SectionLoader = ({ title }: { title: string }) => (
  <div className="section-loader">
    <h3>{title}</h3>
    <div className="skeleton-grid">
      {[1, 2, 3].map(i => <InsightSkeleton key={i} />)}
    </div>
  </div>
);
```

### 2. Empty States
```typescript
// components/Intelligence/EmptyStates.tsx
export const NoInsightsState = () => (
  <div className="empty-state">
    <Icon name="lightbulb" size={48} />
    <h3>No Insights Yet</h3>
    <p>Generate a health story to see AI-powered insights</p>
    <Button variant="primary" href="/stories">
      Create Health Story
    </Button>
  </div>
);

export const InsufficientDataState = () => (
  <div className="empty-state">
    <Icon name="chart" size={48} />
    <h3>Need More Data</h3>
    <p>Track your health for a few more days to see patterns</p>
    <Button variant="primary" href="/track">
      Track Symptoms
    </Button>
  </div>
);
```

### 3. Progressive Disclosure
```typescript
// components/Intelligence/PredictionCard.tsx
export const PredictionCard = ({ prediction }: { prediction: HealthPrediction }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className={`prediction-card ${prediction.preventable ? 'preventable' : ''}`}>
      <CardHeader>
        <h4>{prediction.event_description}</h4>
        <Badge variant={getProbabilityVariant(prediction.probability)}>
          {prediction.probability}% likely
        </Badge>
      </CardHeader>
      
      <CardBody>
        <p className="timeframe">{prediction.timeframe}</p>
        
        {prediction.preventable && (
          <Tag variant="success">Preventable</Tag>
        )}
        
        <button 
          className="expand-toggle"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Show Less' : 'Show Details'}
        </button>
        
        {expanded && (
          <ExpandedContent>
            <div className="reasoning">
              <h5>Why this might happen:</h5>
              <p>{prediction.reasoning}</p>
            </div>
            
            {prediction.suggested_actions.length > 0 && (
              <div className="actions">
                <h5>Prevention steps:</h5>
                <ol>
                  {prediction.suggested_actions.map((action, i) => (
                    <li key={i}>{action}</li>
                  ))}
                </ol>
              </div>
            )}
          </ExpandedContent>
        )}
      </CardBody>
    </Card>
  );
};
```

### 4. Visual Hierarchy
```typescript
// Intelligence.styles.ts
export const InsightCard = styled.div<{ type: string }>`
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid ${props => props.theme.colors.border};
  background: ${props => props.theme.colors.surface};
  
  ${props => props.type === 'positive' && css`
    border-left: 4px solid ${props.theme.colors.success};
  `}
  
  ${props => props.type === 'warning' && css`
    border-left: 4px solid ${props.theme.colors.warning};
  `}
  
  ${props => props.type === 'neutral' && css`
    border-left: 4px solid ${props.theme.colors.info};
  `}
  
  h4 {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: ${props => props.theme.colors.text.primary};
  }
  
  p {
    color: ${props => props.theme.colors.text.secondary};
    line-height: 1.6;
  }
  
  .confidence {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    font-size: 0.875rem;
    color: ${props => props.theme.colors.text.muted};
    
    .confidence-bar {
      width: 100px;
      height: 4px;
      background: ${props => props.theme.colors.background};
      border-radius: 2px;
      overflow: hidden;
      
      .confidence-fill {
        height: 100%;
        background: ${props => props.theme.colors.primary};
        transition: width 0.3s ease;
      }
    }
  }
`;
```

---

## 🧪 Testing Strategy

### 1. Unit Tests
```typescript
// __tests__/useIntelligence.test.ts
import { renderHook, act } from '@testing-library/react-hooks';
import { useIntelligence } from '@/hooks/useIntelligence';
import intelligenceService from '@/services/intelligence.service';

jest.mock('@/services/intelligence.service');

describe('useIntelligence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should load intelligence data on mount', async () => {
    const mockData = {
      status: 'success',
      insights: [],
      predictions: [],
      shadow_patterns: [],
      strategies: []
    };
    
    intelligenceService.getIntelligenceData.mockResolvedValue(mockData);

    const { result, waitForNextUpdate } = renderHook(() => useIntelligence());

    expect(result.current.loading).toBe(true);

    await waitForNextUpdate();

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockData);
  });

  it('should handle refresh with limit enforcement', async () => {
    const { result } = renderHook(() => useIntelligence());

    act(() => {
      result.current.refreshLimit = { can_refresh: false, refreshes_remaining: 0 };
    });

    await act(async () => {
      await result.current.refreshIntelligence();
    });

    expect(intelligenceService.generateIntelligence).not.toHaveBeenCalled();
  });
});
```

### 2. Component Tests
```typescript
// __tests__/IntelligencePage.test.tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { IntelligencePage } from '@/pages/Intelligence';
import { useIntelligence } from '@/hooks/useIntelligence';

jest.mock('@/hooks/useIntelligence');

describe('IntelligencePage', () => {
  it('should show loading state initially', () => {
    useIntelligence.mockReturnValue({
      data: null,
      loading: true,
      refreshing: false,
      error: null
    });

    render(<IntelligencePage />);
    
    expect(screen.getByText('Loading your health intelligence...')).toBeInTheDocument();
  });

  it('should display all intelligence sections when data is loaded', () => {
    const mockData = {
      status: 'success',
      insights: [{ id: '1', title: 'Test Insight' }],
      predictions: [{ id: '2', event_description: 'Test Prediction' }],
      shadow_patterns: [{ id: '3', pattern_name: 'Test Pattern' }],
      strategies: [{ id: '4', strategy: 'Test Strategy' }]
    };

    useIntelligence.mockReturnValue({
      data: mockData,
      loading: false,
      refreshing: false,
      error: null
    });

    render(<IntelligencePage />);
    
    expect(screen.getByText('Test Insight')).toBeInTheDocument();
    expect(screen.getByText('Test Prediction')).toBeInTheDocument();
    expect(screen.getByText('Test Pattern')).toBeInTheDocument();
    expect(screen.getByText('Test Strategy')).toBeInTheDocument();
  });

  it('should handle refresh button click', async () => {
    const mockRefresh = jest.fn();
    
    useIntelligence.mockReturnValue({
      data: { insights: [] },
      loading: false,
      refreshing: false,
      error: null,
      refreshIntelligence: mockRefresh,
      refreshLimit: { can_refresh: true, refreshes_remaining: 5 }
    });

    render(<IntelligencePage />);
    
    const refreshButton = screen.getByText('Refresh Intelligence');
    fireEvent.click(refreshButton);
    
    expect(mockRefresh).toHaveBeenCalled();
  });
});
```

### 3. Integration Tests
```typescript
// __tests__/intelligence.integration.test.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { render, screen, waitFor } from '@testing-library/react';
import { IntelligencePage } from '@/pages/Intelligence';

const server = setupServer(
  rest.get('/api/health-analysis/:userId', (req, res, ctx) => {
    return res(
      ctx.json({
        status: 'success',
        insights: [
          {
            id: '1',
            insight_type: 'positive',
            title: 'Sleep Improving',
            description: 'Your sleep quality has improved',
            confidence: 85
          }
        ],
        predictions: [],
        shadow_patterns: [],
        strategies: []
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Intelligence Integration', () => {
  it('should load and display real data from API', async () => {
    render(<IntelligencePage />);
    
    await waitFor(() => {
      expect(screen.getByText('Sleep Improving')).toBeInTheDocument();
      expect(screen.getByText('Your sleep quality has improved')).toBeInTheDocument();
    });
  });

  it('should handle API errors gracefully', async () => {
    server.use(
      rest.get('/api/health-analysis/:userId', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }));
      })
    );

    render(<IntelligencePage />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load intelligence data')).toBeInTheDocument();
    });
  });
});
```

---

## 📱 Responsive Design

### Mobile-First Approach
```typescript
// Intelligence.styles.ts
export const PageContainer = styled.div`
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
  
  @media (min-width: 768px) {
    padding: 2rem;
  }
`;

export const SectionGrid = styled.div`
  display: grid;
  gap: 1.5rem;
  
  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (min-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
  }
`;

export const MobileRefreshButton = styled.button`
  position: fixed;
  bottom: 2rem;
  right: 1rem;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: ${props => props.theme.colors.primary};
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  
  @media (min-width: 768px) {
    display: none;
  }
`;
```

---

## 🔐 Security Considerations

### 1. API Security
```typescript
// services/api.ts
const secureApi = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to requests
secureApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle auth errors
secureApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### 2. Data Sanitization
```typescript
// utils/sanitize.ts
import DOMPurify from 'dompurify';

export const sanitizeIntelligenceData = (data: IntelligenceData): IntelligenceData => {
  return {
    ...data,
    insights: data.insights.map(insight => ({
      ...insight,
      title: DOMPurify.sanitize(insight.title),
      description: DOMPurify.sanitize(insight.description)
    })),
    predictions: data.predictions.map(prediction => ({
      ...prediction,
      event_description: DOMPurify.sanitize(prediction.event_description),
      reasoning: DOMPurify.sanitize(prediction.reasoning)
    }))
    // Continue for other fields...
  };
};
```

---

## 🚀 Deployment Checklist

### Pre-deployment
- [ ] Environment variables configured
- [ ] API endpoints tested in staging
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Performance monitoring set up
- [ ] Cache headers configured
- [ ] Rate limiting tested
- [ ] Mobile responsiveness verified
- [ ] Accessibility audit passed
- [ ] Security headers configured
- [ ] Bundle size optimized

### Post-deployment
- [ ] Monitor error rates
- [ ] Check API response times
- [ ] Verify refresh limits working
- [ ] Test all user flows
- [ ] Monitor user engagement
- [ ] Gather user feedback

---

## 📚 Additional Resources

### API Documentation
- [Health Intelligence API Docs](./API_REFERENCE.md)
- [Authentication Guide](./AUTH_GUIDE.md)
- [Rate Limiting Details](./RATE_LIMITING.md)

### Design Resources
- [Figma Design System](https://figma.com/...)
- [Component Library](./COMPONENT_LIBRARY.md)
- [Brand Guidelines](./BRAND_GUIDELINES.md)

### Support
- Technical Issues: tech-support@yourapp.com
- API Questions: api-team@yourapp.com
- Frontend Help: frontend-team@yourapp.com

---

## 🎯 Quick Reference

### Common Tasks

**Generate all intelligence components:**
```typescript
POST /api/generate-weekly-analysis
{
  "user_id": "user-123",
  "force_refresh": true,
  "include_predictions": true,
  "include_patterns": true,
  "include_strategies": true
}
```

**Get current week's data:**
```typescript
GET /api/health-analysis/{user_id}?week_of=2025-01-27
```

**Update strategy status:**
```typescript
PUT /api/strategic-moves/{move_id}/status?status=completed&user_id={user_id}
```

**Check refresh limit:**
```typescript
// Response includes:
{
  "refreshes_remaining": 7,
  "can_refresh": true
}
```

### Status Codes
- `success` - All good, show data
- `no_story` - Need health story first
- `insufficient_data` - Need more tracking
- `fallback` - Using simplified data
- `error` - Something went wrong

### Timing
- Generation: 30-90 seconds
- Cache duration: 24 hours
- Refresh limit: 10 per week
- Week resets: Monday 00:00 UTC

---

This guide should give your frontend team everything they need to implement the Health Intelligence feature successfully!