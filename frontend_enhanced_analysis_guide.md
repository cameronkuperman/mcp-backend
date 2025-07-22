# Frontend Implementation for Enhanced Analysis

## 1. Fetching Enhanced Analysis from Supabase

### For Quick Scans:
```javascript
// Fetch a quick scan with all enhancement tiers
const { data, error } = await supabase
  .from('quick_scans')
  .select(`
    *,
    analysis_result,
    enhanced_analysis,
    enhanced_confidence,
    o4_mini_analysis,
    o4_mini_confidence,
    ultra_analysis,
    ultra_confidence
  `)
  .eq('id', scanId)
  .single();

// Get the best available analysis
const bestAnalysis = data.ultra_analysis || 
                    data.o4_mini_analysis || 
                    data.enhanced_analysis || 
                    data.analysis_result;

const bestConfidence = data.ultra_confidence || 
                      data.o4_mini_confidence || 
                      data.enhanced_confidence || 
                      data.confidence_score;
```

### For Deep Dives:
```javascript
// Fetch a deep dive with all enhancement tiers
const { data, error } = await supabase
  .from('deep_dive_sessions')
  .select(`
    *,
    final_analysis,
    final_confidence,
    enhanced_analysis,
    enhanced_confidence,
    ultra_analysis,
    ultra_confidence
  `)
  .eq('id', sessionId)
  .single();

// Get the best available analysis
const bestAnalysis = data.ultra_analysis || 
                    data.enhanced_analysis || 
                    data.final_analysis;

const bestConfidence = data.ultra_confidence || 
                      data.enhanced_confidence || 
                      data.final_confidence;
```

## 2. Using the Analysis Progression View

```javascript
// Get all analyses for a user with their highest tier
const { data, error } = await supabase
  .from('analysis_progression')
  .select('*')
  .eq('user_id', userId)
  .order('created_at', { ascending: false });

// Filter by highest tier achieved
const ultraAnalyses = data.filter(item => item.highest_tier === 'ultra');
```

## 3. Helper Functions for Frontend

```javascript
// Get the best analysis using the database function
async function getBestQuickScanAnalysis(scanId) {
  const { data, error } = await supabase
    .rpc('get_best_quick_scan_analysis', { scan_id: scanId });
  
  return data; // Returns the best available analysis JSON
}

async function getBestDeepDiveAnalysis(sessionId) {
  const { data, error } = await supabase
    .rpc('get_best_deep_dive_analysis', { session_id: sessionId });
  
  return data; // Returns the best available analysis JSON
}
```

## 4. Display Enhancement Progression

```javascript
function AnalysisProgression({ quickScan }) {
  const tiers = [
    {
      name: 'Original',
      confidence: quickScan.confidence_score,
      analysis: quickScan.analysis_result,
      model: 'deepseek/deepseek-chat'
    },
    {
      name: 'Enhanced',
      confidence: quickScan.enhanced_confidence,
      analysis: quickScan.enhanced_analysis,
      model: quickScan.enhanced_model,
      timestamp: quickScan.enhanced_at
    },
    {
      name: 'O4 Mini',
      confidence: quickScan.o4_mini_confidence,
      analysis: quickScan.o4_mini_analysis,
      model: quickScan.o4_mini_model,
      timestamp: quickScan.o4_mini_at
    },
    {
      name: 'Ultra (Grok)',
      confidence: quickScan.ultra_confidence,
      analysis: quickScan.ultra_analysis,
      model: quickScan.ultra_model,
      timestamp: quickScan.ultra_at
    }
  ].filter(tier => tier.analysis); // Only show tiers that exist

  return (
    <div className="analysis-progression">
      {tiers.map((tier, index) => (
        <div key={tier.name} className={`tier ${index === tiers.length - 1 ? 'active' : ''}`}>
          <h4>{tier.name}</h4>
          <div className="confidence">{tier.confidence}%</div>
          {tier.timestamp && (
            <div className="timestamp">
              {new Date(tier.timestamp).toLocaleString()}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

## 5. Real-time Updates

```javascript
// Subscribe to updates when enhancements are added
const subscription = supabase
  .channel('analysis-updates')
  .on(
    'postgres_changes',
    {
      event: 'UPDATE',
      schema: 'public',
      table: 'quick_scans',
      filter: `id=eq.${scanId}`
    },
    (payload) => {
      // Check if enhanced analysis was added
      if (payload.new.enhanced_analysis && !payload.old.enhanced_analysis) {
        setEnhancedAnalysis(payload.new.enhanced_analysis);
        setShowEnhancementNotification(true);
      }
      // Check for ultra analysis
      if (payload.new.ultra_analysis && !payload.old.ultra_analysis) {
        setUltraAnalysis(payload.new.ultra_analysis);
        setShowUltraNotification(true);
      }
    }
  )
  .subscribe();
```

## 6. Checking Enhancement Availability

```javascript
// Check which enhancements are available for a scan
function getAvailableEnhancements(scan) {
  const enhancements = {
    canEnhance: !scan.enhanced_analysis && scan.confidence_score < 85,
    canO4Mini: scan.enhanced_analysis && !scan.o4_mini_analysis && scan.enhanced_confidence < 90,
    canUltra: !scan.ultra_analysis && (scan.o4_mini_confidence || scan.enhanced_confidence || scan.confidence_score) < 95,
    hasAllTiers: !!(scan.enhanced_analysis && scan.o4_mini_analysis && scan.ultra_analysis)
  };
  
  return enhancements;
}

// Usage
const enhancements = getAvailableEnhancements(quickScan);
if (enhancements.canEnhance) {
  showThinkHarderButton();
}
if (enhancements.canUltra) {
  showUltraThinkButton();
}
```

## 7. Summary Statistics

```javascript
// Get enhancement statistics for a user
async function getUserEnhancementStats(userId) {
  const { data, error } = await supabase
    .from('analysis_progression')
    .select('highest_tier, max_confidence')
    .eq('user_id', userId);
  
  const stats = {
    total: data.length,
    enhanced: data.filter(d => ['enhanced', 'o4_mini', 'ultra'].includes(d.highest_tier)).length,
    ultra: data.filter(d => d.highest_tier === 'ultra').length,
    averageConfidence: data.reduce((sum, d) => sum + d.max_confidence, 0) / data.length,
    enhancementRate: (data.filter(d => d.highest_tier !== 'original').length / data.length) * 100
  };
  
  return stats;
}
```