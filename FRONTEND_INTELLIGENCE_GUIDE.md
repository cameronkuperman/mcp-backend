# Frontend Implementation Guide - Health Intelligence

## 🔥 Complete Guide to Implement Insights & Shadow Patterns

### 1. **Fix Your useHealthIntelligence Hook**

The main issue is that the backend now properly validates UUIDs. Here's the updated hook logic:

```typescript
// hooks/useHealthIntelligence.ts

// Update the generation functions to handle responses properly
const generateInsights = async (forceRefresh = false) => {
  if (!user?.id) return;
  
  setGeneratingInsights(true);
  setInsightsError(null);
  
  try {
    const url = `${API_URL}/api/generate-insights/${user.id}${forceRefresh ? '?force_refresh=true' : ''}`;
    const response = await authenticatedFetch(url, { method: 'POST' });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to generate insights');
    }
    
    const data = await response.json();
    
    // Handle different response statuses
    if (data.status === 'no_data') {
      setInsightsError('Start tracking your health to get insights');
      setInsights([]);
    } else if (data.status === 'error') {
      setInsightsError(data.message || 'Failed to generate insights');
      setInsights([]);
    } else {
      // Success - could be 'success', 'cached', or 'fallback'
      setInsights(data.insights || []);
      setCachedFrom(data.cached_from || null);
      
      // Show appropriate message based on status
      if (data.status === 'cached') {
        console.log('Using cached insights from:', data.cached_from);
      } else if (data.status === 'fallback') {
        console.log('Using simplified insights');
      }
    }
  } catch (error) {
    console.error('Error generating insights:', error);
    setInsightsError(error.message);
    setInsights([]);
  } finally {
    setGeneratingInsights(false);
  }
};
```

### 2. **Update Shadow Patterns Function**

Shadow patterns need special handling as they require historical data:

```typescript
const generateShadowPatterns = async (forceRefresh = false) => {
  if (!user?.id) return;
  
  setGeneratingPatterns(true);
  setPatternsError(null);
  
  try {
    const url = `${API_URL}/api/generate-shadow-patterns/${user.id}${forceRefresh ? '?force_refresh=true' : ''}`;
    const response = await authenticatedFetch(url, { method: 'POST' });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to generate patterns');
    }
    
    const data = await response.json();
    
    // Shadow patterns might be empty for new users
    if (data.status === 'success' && data.count === 0) {
      setShadowPatterns([]);
      setPatternsError('Keep tracking - shadow patterns appear after 2+ weeks');
    } else if (data.status === 'error') {
      setPatternsError(data.message || 'Pattern detection unavailable');
      setShadowPatterns([]);
    } else {
      setShadowPatterns(data.shadow_patterns || []);
      
      // Group patterns by category for better display
      const groupedPatterns = (data.shadow_patterns || []).reduce((acc, pattern) => {
        const category = pattern.pattern_category || 'other';
        if (!acc[category]) acc[category] = [];
        acc[category].push(pattern);
        return acc;
      }, {});
      
      setGroupedShadowPatterns(groupedPatterns);
    }
  } catch (error) {
    console.error('Error generating shadow patterns:', error);
    setPatternsError(error.message);
    setShadowPatterns([]);
  } finally {
    setGeneratingPatterns(false);
  }
};
```

### 3. **Display Components**

#### Insights Component:
```tsx
// components/intelligence/InsightsDisplay.tsx
import React from 'react';
import { AlertCircle, TrendingUp, Info } from 'lucide-react';

interface Insight {
  id: string;
  insight_type: 'positive' | 'warning' | 'neutral';
  title: string;
  description: string;
  confidence: number;
  metadata?: {
    based_on?: string;
    is_fallback?: boolean;
  };
}

export const InsightsDisplay: React.FC<{ insights: Insight[] }> = ({ insights }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'positive': return <TrendingUp className="w-5 h-5 text-green-500" />;
      case 'warning': return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      default: return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'positive': return 'bg-green-50 border-green-200';
      case 'warning': return 'bg-yellow-50 border-yellow-200';
      default: return 'bg-blue-50 border-blue-200';
    }
  };

  if (insights.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Info className="w-12 h-12 mx-auto mb-3 text-gray-400" />
        <p>No insights yet. Keep tracking your health!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {insights.map((insight) => (
        <div
          key={insight.id}
          className={`p-4 rounded-lg border ${getTypeColor(insight.insight_type)}`}
        >
          <div className="flex items-start gap-3">
            {getIcon(insight.insight_type)}
            <div className="flex-1">
              <h4 className="font-medium text-gray-900">{insight.title}</h4>
              <p className="text-sm text-gray-600 mt-1">{insight.description}</p>
              
              <div className="flex items-center gap-4 mt-2">
                <span className="text-xs text-gray-500">
                  Confidence: {insight.confidence}%
                </span>
                {insight.metadata?.based_on && (
                  <span className="text-xs text-gray-500">
                    Based on: {insight.metadata.based_on}
                  </span>
                )}
                {insight.metadata?.is_fallback && (
                  <span className="text-xs text-orange-600">
                    Simplified insight
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
```

#### Shadow Patterns Component:
```tsx
// components/intelligence/ShadowPatternsDisplay.tsx
import React from 'react';
import { Eye, EyeOff, AlertTriangle } from 'lucide-react';

interface ShadowPattern {
  id: string;
  pattern_name: string;
  pattern_category: string;
  last_seen_description: string;
  significance: 'high' | 'medium' | 'low';
  days_missing: number;
}

export const ShadowPatternsDisplay: React.FC<{ patterns: ShadowPattern[] }> = ({ patterns }) => {
  const getSignificanceColor = (significance: string) => {
    switch (significance) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'symptom': return '🩺';
      case 'body_part': return '🦴';
      case 'medication': return '💊';
      case 'wellness': return '🧘';
      case 'mental_health': return '🧠';
      default: return '📋';
    }
  };

  if (patterns.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <EyeOff className="w-12 h-12 mx-auto mb-3 text-gray-400" />
        <p>No shadow patterns detected</p>
        <p className="text-sm mt-1">You're being consistent with tracking!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4 text-sm text-gray-600">
        <Eye className="w-4 h-4" />
        <span>Things you haven't mentioned recently:</span>
      </div>
      
      {patterns.map((pattern) => (
        <div
          key={pattern.id}
          className="p-4 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl">{getCategoryIcon(pattern.pattern_category)}</span>
            
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900">{pattern.pattern_name}</h4>
                <span className={`text-xs px-2 py-1 rounded-full ${getSignificanceColor(pattern.significance)}`}>
                  {pattern.significance}
                </span>
              </div>
              
              <p className="text-sm text-gray-600 mt-1">
                {pattern.last_seen_description}
              </p>
              
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>Missing for {pattern.days_missing} days</span>
                <span>Category: {pattern.pattern_category}</span>
              </div>
            </div>
            
            {pattern.significance === 'high' && (
              <AlertTriangle className="w-5 h-5 text-orange-500" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
```

### 4. **Main Intelligence Page Integration**

```tsx
// app/intelligence/page.tsx
import { useHealthIntelligence } from '@/hooks/useHealthIntelligence';

export default function IntelligencePage() {
  const {
    insights,
    shadowPatterns,
    generatingInsights,
    generatingShadowPatterns,
    insightsError,
    patternsError,
    generateInsights,
    generateShadowPatterns,
    refreshLimits,
  } = useHealthIntelligence();

  return (
    <div className="container mx-auto p-4">
      {/* Insights Section */}
      <section className="mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Key Insights</h2>
          <button
            onClick={() => generateInsights(true)}
            disabled={generatingInsights || refreshLimits?.refreshes_remaining === 0}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {generatingInsights ? 'Generating...' : 'Refresh'}
          </button>
        </div>
        
        {insightsError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
            {insightsError}
          </div>
        )}
        
        <InsightsDisplay insights={insights} />
      </section>

      {/* Shadow Patterns Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-2xl font-bold">Shadow Patterns</h2>
            <p className="text-sm text-gray-600">Health topics you've stopped mentioning</p>
          </div>
          <button
            onClick={() => generateShadowPatterns(true)}
            disabled={generatingShadowPatterns || refreshLimits?.refreshes_remaining === 0}
            className="px-4 py-2 bg-purple-500 text-white rounded disabled:opacity-50"
          >
            {generatingShadowPatterns ? 'Analyzing...' : 'Refresh'}
          </button>
        </div>
        
        {patternsError && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700">
            {patternsError}
          </div>
        )}
        
        <ShadowPatternsDisplay patterns={shadowPatterns} />
      </section>

      {/* Refresh Limits */}
      {refreshLimits && (
        <div className="mt-8 text-sm text-gray-600 text-center">
          Refreshes remaining this week: {refreshLimits.refreshes_remaining}/10
        </div>
      )}
    </div>
  );
}
```

### 5. **Key Frontend Fixes Needed**

1. **UUID Validation**: Always ensure user IDs are valid UUIDs
2. **Error Handling**: Handle `no_data`, `no_story`, and error statuses
3. **Empty States**: Show helpful messages when no data exists
4. **Loading States**: Show proper loading indicators
5. **Cache Status**: Display when data is cached vs fresh

### 6. **Testing Your Implementation**

```bash
# Test with the fixed script
python test_intelligence_fixed.py YOUR-USER-UUID

# Example with real UUID:
python test_intelligence_fixed.py 123e4567-e89b-12d3-a456-426614174000
```

### 7. **Common Issues & Solutions**

| Issue | Solution |
|-------|----------|
| "Invalid UUID format" | Ensure user.id is a valid UUID string |
| "No insights generated" | User needs health data - use Oracle chat first |
| "Shadow patterns empty" | Normal for new users - needs 2+ weeks of data |
| "story_id constraint violation" | Fixed in backend - now uses dummy UUID |
| "CORS errors" | Backend CORS is fixed for localhost:3000/3001 |

### 8. **Data Flow Diagram**

```
Frontend                    Backend                    Database
--------                    -------                    --------
generateInsights() -------> POST /generate-insights -> health_insights table
                           validates UUID              (user_id: UUID)
                           generates with AI           (story_id: UUID - dummy)
                           returns JSON <------------- stores insights

loadInsights() -----------> GET /insights/{uuid} ----> retrieves from DB
                           returns stored data <------ returns insights
```

## 🎯 Quick Implementation Checklist

- [ ] Update useHealthIntelligence hook with proper error handling
- [ ] Create InsightsDisplay component
- [ ] Create ShadowPatternsDisplay component  
- [ ] Ensure all user IDs are valid UUIDs
- [ ] Handle empty states gracefully
- [ ] Show loading states during generation
- [ ] Display refresh limits to users
- [ ] Test with real user data