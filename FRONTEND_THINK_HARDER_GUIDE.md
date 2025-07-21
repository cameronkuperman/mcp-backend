# Frontend Guide: 3-Tier Think Harder System

## Overview
The backend now supports a 3-tier analysis system for Quick Scan results:
1. **Initial Analysis** - DeepSeek V3 (deepseek/deepseek-chat) - fast, efficient
2. **Think Harder (o4-mini)** - Enhanced reasoning with o4-mini
3. **Ultra Think (Grok 4)** - Maximum reasoning capability with x-ai/grok-4

## API Endpoints

### 1. Initial Quick Scan
```typescript
POST /api/quick-scan
Body: {
  body_part: string,
  form_data: object,
  user_id?: string
}
Response: {
  scan_id: string,
  analysis: object,
  confidence: number,
  status: "success"
}
```

### 2. Think Harder with o4-mini (NEW)
```typescript
POST /api/quick-scan/think-harder-o4
Body: {
  scan_id: string,
  user_id?: string
}
Response: {
  status: "success",
  analysis_tier: "enhanced",
  o4_mini_analysis: {
    enhanced_diagnosis: object,
    overlooked_considerations: array,
    differential_refinement: array,
    specific_recommendations: array,
    timeline_expectations: object,
    confidence: number,
    reasoning_summary: string
  },
  original_confidence: number,
  o4_mini_confidence: number,
  confidence_improvement: number,
  processing_message: "o4-mini-ized",
  next_tier_available: true,
  next_tier_preview: string
}
```

### 3. Ultra Think with Grok 4 (NEW)
```typescript
POST /api/quick-scan/ultra-think
Body: {
  scan_id: string,
  user_id?: string
}
Response: {
  status: "success",
  analysis_tier: "ultra",
  ultra_analysis: {
    ultra_diagnosis: object,
    rare_considerations: array,
    systemic_analysis: object,
    diagnostic_strategy: object,
    critical_insights: array,
    confidence: number,
    complexity_score: number,
    recommendation_change: string
  },
  confidence_progression: {
    original: number,
    o4_mini: number,
    ultra: number
  },
  total_confidence_gain: number,
  complexity_score: number,
  critical_insights: array
}
```

### 4. Original Think Harder (Still Available)
```typescript
POST /api/quick-scan/think-harder
// Uses GPT-4 by default, returns enhanced_analysis
```

## Frontend Implementation

### 1. Progressive Enhancement UI
```tsx
const QuickScanResults = ({ scanData }) => {
  const [tier, setTier] = useState('basic');
  const [o4MiniAnalysis, setO4MiniAnalysis] = useState(null);
  const [ultraAnalysis, setUltraAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');

  const confidence = 
    tier === 'ultra' ? ultraAnalysis?.confidence_progression?.ultra :
    tier === 'enhanced' ? o4MiniAnalysis?.o4_mini_confidence :
    scanData.analysis.confidence;

  const handleO4Mini = async () => {
    setLoading(true);
    setLoadingMessage('o4-mini-izing...');
    
    try {
      const response = await fetch('/api/quick-scan/think-harder-o4', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_id: scanData.scan_id })
      });
      
      const data = await response.json();
      setO4MiniAnalysis(data);
      setTier('enhanced');
    } finally {
      setLoading(false);
    }
  };

  const handleUltraThink = async () => {
    setLoading(true);
    setLoadingMessage('Grokking your symptoms...');
    
    try {
      const response = await fetch('/api/quick-scan/ultra-think', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_id: scanData.scan_id })
      });
      
      const data = await response.json();
      setUltraAnalysis(data);
      setTier('ultra');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Confidence Meter */}
      <ConfidenceMeter 
        value={confidence} 
        tier={tier}
        showProgression={tier !== 'basic'}
        progression={ultraAnalysis?.confidence_progression}
      />

      {/* Current Analysis Display */}
      <AnalysisDisplay 
        tier={tier}
        basicAnalysis={scanData.analysis}
        o4MiniAnalysis={o4MiniAnalysis?.o4_mini_analysis}
        ultraAnalysis={ultraAnalysis?.ultra_analysis}
      />

      {/* Progressive Enhancement Buttons */}
      <div className="mt-6 space-y-3">
        {!o4MiniAnalysis && confidence < 85 && (
          <button
            onClick={handleO4Mini}
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white rounded-lg"
          >
            {loading ? loadingMessage : 'Think Harder (o4-mini)'}
          </button>
        )}

        {o4MiniAnalysis && !ultraAnalysis && (
          <button
            onClick={handleUltraThink}
            disabled={loading}
            className="w-full py-3 bg-purple-600 text-white rounded-lg"
          >
            {loading ? loadingMessage : 'Ultra Think (Grok 4)'}
          </button>
        )}
      </div>

      {/* Loading Animation */}
      {loading && <ThinkingAnimation message={loadingMessage} />}
    </div>
  );
};
```

### 2. Confidence Meter Component
```tsx
const ConfidenceMeter = ({ value, tier, showProgression, progression }) => {
  const getColor = (conf) => {
    if (conf >= 90) return 'bg-green-600';
    if (conf >= 80) return 'bg-blue-600';
    if (conf >= 70) return 'bg-yellow-600';
    return 'bg-red-600';
  };

  return (
    <div className="mb-6">
      <div className="flex justify-between mb-2">
        <span className="text-sm font-medium">Diagnostic Confidence</span>
        <span className="text-sm font-bold">{value}%</span>
      </div>
      
      {/* Main confidence bar */}
      <div className="w-full bg-gray-200 rounded-full h-4">
        <div 
          className={`h-4 rounded-full transition-all duration-1000 ${getColor(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>

      {/* Progression indicators */}
      {showProgression && progression && (
        <div className="mt-2 flex justify-between text-xs">
          <span>Basic: {progression.original}%</span>
          {progression.o4_mini && <span>Enhanced: {progression.o4_mini}%</span>}
          {progression.ultra && <span>Ultra: {progression.ultra}%</span>}
        </div>
      )}
    </div>
  );
};
```

### 3. Analysis Display Component
```tsx
const AnalysisDisplay = ({ tier, basicAnalysis, o4MiniAnalysis, ultraAnalysis }) => {
  const currentAnalysis = 
    tier === 'ultra' ? ultraAnalysis :
    tier === 'enhanced' ? o4MiniAnalysis :
    basicAnalysis;

  return (
    <div className="space-y-4">
      {/* Tier Badge */}
      <div className="flex items-center gap-2">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          tier === 'ultra' ? 'bg-purple-100 text-purple-800' :
          tier === 'enhanced' ? 'bg-blue-100 text-blue-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {tier === 'ultra' ? 'Ultra Analysis' :
           tier === 'enhanced' ? 'Enhanced Analysis' :
           'Initial Analysis'}
        </span>
        {tier !== 'basic' && (
          <span className="text-sm text-gray-600">
            powered by {tier === 'ultra' ? 'Grok 4' : 'o4-mini'}
          </span>
        )}
      </div>

      {/* Primary Diagnosis */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-2">Primary Assessment</h3>
        <p className="text-gray-800">
          {tier === 'ultra' ? ultraAnalysis?.ultra_diagnosis?.primary :
           tier === 'enhanced' ? o4MiniAnalysis?.enhanced_diagnosis?.primary :
           basicAnalysis?.primaryCondition}
        </p>
        
        {/* Show key pattern for o4-mini */}
        {tier === 'enhanced' && o4MiniAnalysis?.enhanced_diagnosis?.key_pattern && (
          <p className="mt-2 text-sm text-blue-600">
            Key Pattern: {o4MiniAnalysis.enhanced_diagnosis.key_pattern}
          </p>
        )}

        {/* Show reasoning chain for ultra */}
        {tier === 'ultra' && ultraAnalysis?.ultra_diagnosis?.reasoning_chain && (
          <div className="mt-3 space-y-1">
            <p className="text-sm font-medium">Reasoning Process:</p>
            {ultraAnalysis.ultra_diagnosis.reasoning_chain.map((step, i) => (
              <p key={i} className="text-sm text-gray-600 ml-4">• {step}</p>
            ))}
          </div>
        )}
      </div>

      {/* Additional Insights (tier-specific) */}
      {tier === 'enhanced' && o4MiniAnalysis?.overlooked_considerations && (
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="font-medium mb-2">New Insights from o4-mini</h4>
          {o4MiniAnalysis.overlooked_considerations.map((item, i) => (
            <div key={i} className="mb-2">
              <p className="font-medium text-sm">{item.factor}</p>
              <p className="text-sm text-gray-600">{item.significance}</p>
            </div>
          ))}
        </div>
      )}

      {tier === 'ultra' && ultraAnalysis?.critical_insights && (
        <div className="bg-purple-50 p-4 rounded-lg">
          <h4 className="font-medium mb-2">Critical Insights from Grok</h4>
          {ultraAnalysis.critical_insights.map((insight, i) => (
            <p key={i} className="text-sm mb-1">• {insight}</p>
          ))}
          {ultraAnalysis.complexity_score && (
            <p className="mt-2 text-sm">
              Case Complexity: {ultraAnalysis.complexity_score}/10
            </p>
          )}
        </div>
      )}
    </div>
  );
};
```

### 4. Thinking Animation
```tsx
const ThinkingAnimation = ({ message }) => {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="text-center">
        <div className="animate-pulse mb-4">
          <svg className="w-16 h-16 mx-auto text-blue-600" fill="none" viewBox="0 0 24 24">
            {/* Brain/thinking icon */}
          </svg>
        </div>
        <p className="text-gray-600 animate-pulse">{message}</p>
        <div className="flex justify-center mt-2 space-x-1">
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
        </div>
      </div>
    </div>
  );
};
```

## Best Practices

1. **Show Confidence Progression**: Always display how confidence improves with each tier
2. **Loading States**: Use specific messages like "o4-mini-izing..." to set expectations
3. **Conditional Buttons**: Only show next tier if confidence < target or user wants more detail
4. **Cache Results**: Store enhanced analyses to avoid re-fetching
5. **Error Handling**: Gracefully handle API errors and show fallback UI
6. **Cost Awareness**: Consider showing estimated cost for ultra analysis

## State Management Example (Redux/Zustand)
```typescript
interface AnalysisState {
  basicAnalysis: any;
  o4MiniAnalysis: any;
  ultraAnalysis: any;
  currentTier: 'basic' | 'enhanced' | 'ultra';
  isLoading: boolean;
  loadingMessage: string;
}

const useAnalysisStore = create<AnalysisState>((set) => ({
  basicAnalysis: null,
  o4MiniAnalysis: null,
  ultraAnalysis: null,
  currentTier: 'basic',
  isLoading: false,
  loadingMessage: '',
  
  runO4MiniAnalysis: async (scanId: string) => {
    set({ isLoading: true, loadingMessage: 'o4-mini-izing...' });
    try {
      const response = await api.quickScan.thinkHarderO4(scanId);
      set({ 
        o4MiniAnalysis: response.data,
        currentTier: 'enhanced',
        isLoading: false 
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },
  
  runUltraAnalysis: async (scanId: string) => {
    set({ isLoading: true, loadingMessage: 'Grokking your symptoms...' });
    try {
      const response = await api.quickScan.ultraThink(scanId);
      set({ 
        ultraAnalysis: response.data,
        currentTier: 'ultra',
        isLoading: false 
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  }
}));
```

## Notes
- The existing `/api/quick-scan/think-harder` endpoint still works (uses GPT-4)
- Deep Dive think-harder now uses Grok 4 by default
- All endpoints return backward-compatible responses
- Database automatically stores each tier's analysis separately