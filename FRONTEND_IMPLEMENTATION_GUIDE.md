# 🚀 Frontend Implementation Guide for Health Intelligence Features

A comprehensive guide for implementing the health intelligence features in your Next.js frontend.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Database Setup](#database-setup)
3. [API Integration](#api-integration)
4. [UI Components](#ui-components)
5. [State Management](#state-management)
6. [Real-time Updates](#real-time-updates)
7. [Error Handling](#error-handling)
8. [Testing](#testing)

---

## 🌟 Overview

The health intelligence system provides:
- **Weekly AI Analysis**: Automatic insights, predictions, and pattern detection
- **Shadow Patterns**: Identifies missing health tracking patterns
- **Strategic Moves**: Personalized health optimization strategies
- **PDF Export**: Professional health reports
- **Doctor Sharing**: Secure, time-limited report sharing

---

## 💾 Database Setup

### 1. Run Migrations

First, execute the SQL migration to create all necessary tables:

```bash
# Using Supabase CLI
supabase db push migrations/001_health_intelligence_tables.sql

# Or via Supabase Dashboard
# Go to SQL Editor > New Query > Paste the migration > Run
```

### 2. Enable Realtime (Optional)

For live updates when analysis is generated:

```sql
-- Enable realtime for insights table
ALTER PUBLICATION supabase_realtime ADD TABLE health_insights;
ALTER PUBLICATION supabase_realtime ADD TABLE health_predictions;
```

---

## 🔌 API Integration

### 1. Create API Client

```typescript
// lib/api/health-intelligence.ts
import { API_URL } from '@/lib/config';

export class HealthIntelligenceAPI {
  private baseUrl = API_URL;

  async generateWeeklyAnalysis(userId: string, forceRefresh = false) {
    const response = await fetch(`${this.baseUrl}/api/generate-weekly-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        force_refresh: forceRefresh,
        include_predictions: true,
        include_patterns: true,
        include_strategies: true
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail?.message || 'Analysis generation failed');
    }

    return response.json();
  }

  async getAnalysis(userId: string, weekOf?: string) {
    const url = weekOf 
      ? `${this.baseUrl}/api/health-analysis/${userId}?week_of=${weekOf}`
      : `${this.baseUrl}/api/health-analysis/${userId}`;

    const response = await fetch(url);
    return response.json();
  }

  async exportPDF(userId: string, storyIds: string[], options?: {
    includeAnalysis?: boolean;
    includeNotes?: boolean;
  }) {
    const response = await fetch(`${this.baseUrl}/api/export-pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        story_ids: storyIds,
        include_analysis: options?.includeAnalysis ?? true,
        include_notes: options?.includeNotes ?? true
      })
    });

    const data = await response.json();
    return data;
  }

  async shareWithDoctor(userId: string, storyIds: string[], options?: {
    recipientEmail?: string;
    expiresInDays?: number;
  }) {
    const response = await fetch(`${this.baseUrl}/api/share-with-doctor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        story_ids: storyIds,
        recipient_email: options?.recipientEmail,
        expires_in_days: options?.expiresInDays || 30
      })
    });

    return response.json();
  }

  async updateStrategyStatus(moveId: string, status: string, userId: string) {
    const response = await fetch(
      `${this.baseUrl}/api/strategic-moves/${moveId}/status?user_id=${userId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      }
    );

    return response.json();
  }
}

export const healthIntelligenceAPI = new HealthIntelligenceAPI();
```

### 2. Create React Hooks

```typescript
// hooks/useHealthIntelligence.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { healthIntelligenceAPI } from '@/lib/api/health-intelligence';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

export function useHealthAnalysis(weekOf?: string) {
  const { user } = useAuth();

  return useQuery({
    queryKey: ['health-analysis', user?.id, weekOf],
    queryFn: () => healthIntelligenceAPI.getAnalysis(user!.id, weekOf),
    enabled: !!user?.id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useGenerateAnalysis() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (forceRefresh = false) => 
      healthIntelligenceAPI.generateWeeklyAnalysis(user!.id, forceRefresh),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health-analysis'] });
      toast.success('Analysis generated successfully!');
    },
    onError: (error: any) => {
      if (error.message?.includes('refresh limit')) {
        toast.error('Weekly refresh limit reached (10/week)');
      } else {
        toast.error('Failed to generate analysis');
      }
    }
  });
}

export function useExportPDF() {
  const { user } = useAuth();

  return useMutation({
    mutationFn: ({ storyIds, options }: {
      storyIds: string[];
      options?: { includeAnalysis?: boolean; includeNotes?: boolean };
    }) => healthIntelligenceAPI.exportPDF(user!.id, storyIds, options),
    onSuccess: (data) => {
      if (data.pdf_url) {
        window.open(data.pdf_url, '_blank');
        toast.success('PDF exported successfully!');
      }
    },
    onError: () => {
      toast.error('Failed to export PDF');
    }
  });
}

export function useShareWithDoctor() {
  const { user } = useAuth();

  return useMutation({
    mutationFn: ({ storyIds, options }: {
      storyIds: string[];
      options?: { recipientEmail?: string; expiresInDays?: number };
    }) => healthIntelligenceAPI.shareWithDoctor(user!.id, storyIds, options),
    onSuccess: (data) => {
      if (data.share_link) {
        toast.success('Share link created!');
      }
    },
    onError: () => {
      toast.error('Failed to create share link');
    }
  });
}

export function useUpdateStrategy() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ moveId, status }: { moveId: string; status: string }) =>
      healthIntelligenceAPI.updateStrategyStatus(moveId, status, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['health-analysis'] });
      toast.success('Strategy updated!');
    }
  });
}
```

---

## 🎨 UI Components

### 1. Health Insights Component

```typescript
// components/intelligence/HealthInsights.tsx
import { Card } from '@/components/ui/card';
import { motion } from 'framer-motion';
import { TrendingUp, AlertTriangle, Info } from 'lucide-react';

interface Insight {
  id: string;
  insight_type: 'positive' | 'warning' | 'neutral';
  title: string;
  description: string;
  confidence: number;
}

export function HealthInsights({ insights }: { insights: Insight[] }) {
  const getIcon = (type: string) => {
    switch (type) {
      case 'positive': return <TrendingUp className="w-5 h-5 text-green-500" />;
      case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default: return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getColorClass = (type: string) => {
    switch (type) {
      case 'positive': return 'border-green-500/20 bg-green-500/5';
      case 'warning': return 'border-yellow-500/20 bg-yellow-500/5';
      default: return 'border-blue-500/20 bg-blue-500/5';
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Key Insights</h3>
      
      {insights.map((insight, index) => (
        <motion.div
          key={insight.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <Card className={`p-4 border ${getColorClass(insight.insight_type)}`}>
            <div className="flex items-start gap-3">
              {getIcon(insight.insight_type)}
              <div className="flex-1">
                <h4 className="font-medium text-white mb-1">{insight.title}</h4>
                <p className="text-sm text-gray-400">{insight.description}</p>
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1 flex-1 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-purple-600"
                      style={{ width: `${insight.confidence}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500">{insight.confidence}% confidence</span>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
```

### 2. Health Predictions Component

```typescript
// components/intelligence/HealthPredictions.tsx
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, Shield } from 'lucide-react';

interface Prediction {
  id: string;
  event_description: string;
  probability: number;
  timeframe: string;
  preventable: boolean;
  reasoning?: string;
  suggested_actions?: string[];
}

export function HealthPredictions({ predictions }: { predictions: Prediction[] }) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Health Outlook</h3>
      
      {predictions.map((prediction) => (
        <Card key={prediction.id} className="p-4 border-white/10">
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <h4 className="font-medium text-white flex-1">
                {prediction.event_description}
              </h4>
              {prediction.preventable && (
                <Badge variant="secondary" className="ml-2">
                  <Shield className="w-3 h-3 mr-1" />
                  Preventable
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1 text-gray-400">
                <Clock className="w-4 h-4" />
                {prediction.timeframe}
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-24 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      prediction.probability > 70
                        ? 'bg-red-500'
                        : prediction.probability > 40
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${prediction.probability}%` }}
                  />
                </div>
                <span className="text-gray-400">{prediction.probability}%</span>
              </div>
            </div>

            {prediction.reasoning && (
              <p className="text-sm text-gray-500 italic">{prediction.reasoning}</p>
            )}

            {prediction.suggested_actions && prediction.suggested_actions.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-gray-400 font-medium">Preventive actions:</p>
                <ul className="text-sm text-gray-300 space-y-1">
                  {prediction.suggested_actions.map((action, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-purple-400 mt-1">•</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
```

### 3. Shadow Patterns Component

```typescript
// components/intelligence/ShadowPatterns.tsx
import { Card } from '@/components/ui/card';
import { Ghost, Calendar } from 'lucide-react';

interface ShadowPattern {
  id: string;
  pattern_name: string;
  pattern_category?: string;
  last_seen_description: string;
  significance: 'high' | 'medium' | 'low';
  days_missing: number;
  last_mentioned_date?: string;
}

export function ShadowPatterns({ patterns }: { patterns: ShadowPattern[] }) {
  const getSignificanceColor = (significance: string) => {
    switch (significance) {
      case 'high': return 'text-red-400 bg-red-500/10';
      case 'medium': return 'text-yellow-400 bg-yellow-500/10';
      default: return 'text-gray-400 bg-gray-500/10';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Ghost className="w-5 h-5 text-purple-400" />
        <h3 className="text-lg font-semibold text-white">Shadow Patterns</h3>
      </div>
      
      <p className="text-sm text-gray-400">
        These patterns were prominent in your recent health tracking but are now missing:
      </p>

      {patterns.map((pattern) => (
        <Card key={pattern.id} className="p-4 border-white/10 hover:border-purple-500/20 transition-colors">
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <h4 className="font-medium text-white">{pattern.pattern_name}</h4>
              <Badge className={getSignificanceColor(pattern.significance)}>
                {pattern.significance}
              </Badge>
            </div>

            <p className="text-sm text-gray-400">{pattern.last_seen_description}</p>

            <div className="flex items-center gap-3 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Missing for {pattern.days_missing} days
              </div>
              {pattern.pattern_category && (
                <Badge variant="outline" className="text-xs">
                  {pattern.pattern_category}
                </Badge>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
```

### 4. Strategic Moves Component

```typescript
// components/intelligence/StrategicMoves.tsx
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Target, Lightbulb, Shield, TrendingUp } from 'lucide-react';
import { useUpdateStrategy } from '@/hooks/useHealthIntelligence';

interface Strategy {
  id: string;
  strategy: string;
  strategy_type: 'discovery' | 'pattern' | 'prevention' | 'optimization';
  priority: number;
  rationale?: string;
  expected_outcome?: string;
  completion_status: string;
}

export function StrategicMoves({ strategies }: { strategies: Strategy[] }) {
  const updateStrategy = useUpdateStrategy();

  const getIcon = (type: string) => {
    switch (type) {
      case 'discovery': return <Lightbulb className="w-5 h-5" />;
      case 'prevention': return <Shield className="w-5 h-5" />;
      case 'optimization': return <TrendingUp className="w-5 h-5" />;
      default: return <Target className="w-5 h-5" />;
    }
  };

  const handleStatusChange = (moveId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    updateStrategy.mutate({ moveId, status: newStatus });
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Strategic Moves</h3>
      
      {strategies
        .sort((a, b) => b.priority - a.priority)
        .map((strategy) => (
          <Card
            key={strategy.id}
            className={`p-4 border-white/10 ${
              strategy.completion_status === 'completed' ? 'opacity-60' : ''
            }`}
          >
            <div className="flex items-start gap-3">
              <Checkbox
                checked={strategy.completion_status === 'completed'}
                onCheckedChange={() => handleStatusChange(strategy.id, strategy.completion_status)}
                className="mt-1"
              />
              
              <div className="flex-1 space-y-2">
                <div className="flex items-start gap-3">
                  <div className="text-purple-400">{getIcon(strategy.strategy_type)}</div>
                  <div className="flex-1">
                    <p className={`font-medium ${
                      strategy.completion_status === 'completed'
                        ? 'text-gray-400 line-through'
                        : 'text-white'
                    }`}>
                      {strategy.strategy}
                    </p>
                    
                    {strategy.rationale && (
                      <p className="text-sm text-gray-400 mt-1">{strategy.rationale}</p>
                    )}
                    
                    {strategy.expected_outcome && (
                      <p className="text-sm text-green-400 mt-1">
                        Expected: {strategy.expected_outcome}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {[...Array(10)].map((_, i) => (
                      <div
                        key={i}
                        className={`h-1 w-1 rounded-full ${
                          i < strategy.priority ? 'bg-purple-500' : 'bg-gray-700'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-gray-500">
                    Priority: {strategy.priority}/10
                  </span>
                </div>
              </div>
            </div>
          </Card>
        ))}
    </div>
  );
}
```

### 5. Complete Intelligence View

```typescript
// pages/intelligence/index.tsx
import { useState } from 'react';
import { useHealthAnalysis, useGenerateAnalysis } from '@/hooks/useHealthIntelligence';
import { HealthInsights } from '@/components/intelligence/HealthInsights';
import { HealthPredictions } from '@/components/intelligence/HealthPredictions';
import { ShadowPatterns } from '@/components/intelligence/ShadowPatterns';
import { StrategicMoves } from '@/components/intelligence/StrategicMoves';
import { Button } from '@/components/ui/button';
import { RefreshCw, Download, Share2 } from 'lucide-react';
import { format, startOfWeek } from 'date-fns';

export default function IntelligencePage() {
  const [selectedWeek, setSelectedWeek] = useState<string>(
    format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd')
  );
  
  const { data: analysis, isLoading } = useHealthAnalysis(selectedWeek);
  const generateAnalysis = useGenerateAnalysis();

  const handleRefresh = () => {
    generateAnalysis.mutate(true); // force refresh
  };

  if (isLoading) {
    return <LoadingState />;
  }

  if (!analysis || (!analysis.insights?.length && !analysis.predictions?.length)) {
    return <EmptyState onGenerate={() => generateAnalysis.mutate(false)} />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Health Intelligence</h1>
          <p className="text-gray-400 mt-1">
            Week of {format(new Date(selectedWeek), 'MMMM d, yyyy')}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={generateAnalysis.isPending}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${generateAnalysis.isPending ? 'animate-spin' : ''}`} />
            Refresh Analysis
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-8">
          {analysis.insights && analysis.insights.length > 0 && (
            <HealthInsights insights={analysis.insights} />
          )}
          
          {analysis.predictions && analysis.predictions.length > 0 && (
            <HealthPredictions predictions={analysis.predictions} />
          )}
        </div>
        
        <div className="space-y-8">
          {analysis.shadow_patterns && analysis.shadow_patterns.length > 0 && (
            <ShadowPatterns patterns={analysis.shadow_patterns} />
          )}
          
          {analysis.strategies && analysis.strategies.length > 0 && (
            <StrategicMoves strategies={analysis.strategies} />
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## 📊 State Management

### Zustand Store for Analysis State

```typescript
// stores/health-intelligence.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface HealthIntelligenceState {
  currentAnalysis: any | null;
  weeklyAnalyses: Record<string, any>;
  refreshCount: number;
  refreshLimit: number;
  
  setCurrentAnalysis: (analysis: any) => void;
  addWeeklyAnalysis: (weekOf: string, analysis: any) => void;
  incrementRefreshCount: () => void;
  resetWeeklyState: () => void;
}

export const useHealthIntelligenceStore = create<HealthIntelligenceState>()(
  devtools(
    (set) => ({
      currentAnalysis: null,
      weeklyAnalyses: {},
      refreshCount: 0,
      refreshLimit: 10,
      
      setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
      
      addWeeklyAnalysis: (weekOf, analysis) =>
        set((state) => ({
          weeklyAnalyses: {
            ...state.weeklyAnalyses,
            [weekOf]: analysis
          }
        })),
      
      incrementRefreshCount: () =>
        set((state) => ({ refreshCount: state.refreshCount + 1 })),
      
      resetWeeklyState: () =>
        set({ refreshCount: 0, currentAnalysis: null })
    }),
    {
      name: 'health-intelligence'
    }
  )
);
```

---

## 🔄 Real-time Updates

### Supabase Realtime Integration

```typescript
// hooks/useRealtimeAnalysis.ts
import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

export function useRealtimeAnalysis() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!user?.id) return;

    const channel = supabase
      .channel('health-analysis-updates')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'health_insights',
          filter: `user_id=eq.${user.id}`
        },
        (payload) => {
          // Invalidate and refetch analysis
          queryClient.invalidateQueries({ queryKey: ['health-analysis'] });
          toast.success('New health insights available!');
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'analysis_generation_log',
          filter: `user_id=eq.${user.id}`
        },
        (payload) => {
          if (payload.new.status === 'completed') {
            toast.success('Analysis generation completed!');
          } else if (payload.new.status === 'failed') {
            toast.error('Analysis generation failed');
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user?.id, queryClient]);
}
```

---

## ⚠️ Error Handling

### Global Error Boundary

```typescript
// components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-[400px] flex items-center justify-center">
            <div className="text-center space-y-4">
              <h2 className="text-xl font-semibold text-white">
                Something went wrong
              </h2>
              <p className="text-gray-400">
                We encountered an error while loading your health analysis.
              </p>
              <Button onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
```

---

## 🧪 Testing

### Component Tests

```typescript
// __tests__/components/HealthInsights.test.tsx
import { render, screen } from '@testing-library/react';
import { HealthInsights } from '@/components/intelligence/HealthInsights';

describe('HealthInsights', () => {
  const mockInsights = [
    {
      id: '1',
      insight_type: 'positive' as const,
      title: 'Improving Sleep Pattern',
      description: 'Your sleep quality has improved by 20% this week',
      confidence: 85
    },
    {
      id: '2',
      insight_type: 'warning' as const,
      title: 'Increased Stress Indicators',
      description: 'Stress-related symptoms have increased recently',
      confidence: 70
    }
  ];

  it('renders all insights', () => {
    render(<HealthInsights insights={mockInsights} />);
    
    expect(screen.getByText('Improving Sleep Pattern')).toBeInTheDocument();
    expect(screen.getByText('Increased Stress Indicators')).toBeInTheDocument();
  });

  it('displays correct confidence levels', () => {
    render(<HealthInsights insights={mockInsights} />);
    
    expect(screen.getByText('85% confidence')).toBeInTheDocument();
    expect(screen.getByText('70% confidence')).toBeInTheDocument();
  });

  it('applies correct styling based on insight type', () => {
    const { container } = render(<HealthInsights insights={mockInsights} />);
    
    const positiveCard = container.querySelector('.border-green-500\\/20');
    const warningCard = container.querySelector('.border-yellow-500\\/20');
    
    expect(positiveCard).toBeInTheDocument();
    expect(warningCard).toBeInTheDocument();
  });
});
```

### Integration Tests

```typescript
// __tests__/integration/health-analysis-flow.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useHealthAnalysis, useGenerateAnalysis } from '@/hooks/useHealthIntelligence';
import { healthIntelligenceAPI } from '@/lib/api/health-intelligence';

jest.mock('@/lib/api/health-intelligence');

describe('Health Analysis Flow', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  it('fetches analysis data successfully', async () => {
    const mockData = {
      insights: [{ id: '1', title: 'Test Insight' }],
      predictions: [],
      shadow_patterns: [],
      strategies: []
    };

    (healthIntelligenceAPI.getAnalysis as jest.Mock).mockResolvedValue(mockData);

    const { result } = renderHook(() => useHealthAnalysis(), { wrapper });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockData);
    });
  });

  it('handles generation errors gracefully', async () => {
    const error = new Error('Weekly refresh limit reached');
    (healthIntelligenceAPI.generateWeeklyAnalysis as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useGenerateAnalysis(), { wrapper });

    await result.current.mutateAsync(true);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
      expect(result.current.error).toEqual(error);
    });
  });
});
```

---

## 🚀 Deployment Checklist

- [ ] Run database migrations
- [ ] Set up environment variables
- [ ] Configure API endpoints
- [ ] Test all features locally
- [ ] Enable error tracking
- [ ] Set up monitoring
- [ ] Configure rate limiting
- [ ] Test PDF generation
- [ ] Verify email functionality
- [ ] Load test the analysis generation

---

## 📈 Performance Optimization

### 1. Lazy Loading

```typescript
// Lazy load heavy components
const HealthIntelligencePage = lazy(() => import('./pages/intelligence'));

// Use Suspense
<Suspense fallback={<LoadingSpinner />}>
  <HealthIntelligencePage />
</Suspense>
```

### 2. Data Caching

```typescript
// Configure React Query for optimal caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
    },
  },
});
```

### 3. Optimistic Updates

```typescript
// Update UI immediately while mutation is pending
const updateStrategy = useMutation({
  mutationFn: updateStrategyStatus,
  onMutate: async ({ moveId, status }) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries(['health-analysis']);
    
    // Snapshot previous value
    const previous = queryClient.getQueryData(['health-analysis']);
    
    // Optimistically update
    queryClient.setQueryData(['health-analysis'], (old: any) => ({
      ...old,
      strategies: old.strategies.map((s: any) =>
        s.id === moveId ? { ...s, completion_status: status } : s
      ),
    }));
    
    return { previous };
  },
  onError: (err, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['health-analysis'], context?.previous);
  },
});
```

---

This guide provides a complete implementation path for integrating all health intelligence features into your frontend. Each component is designed to work seamlessly with the backend API while providing an excellent user experience.