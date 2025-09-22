# Frontend Multi-Part Selection Migration Guide

## Overview
This guide provides comprehensive instructions for migrating the frontend to support multiple body part selection while maintaining full backward compatibility.

## Migration Timeline
- **Phase 1 (Week 1)**: Backend deployed with dual support
- **Phase 2 (Week 2)**: Frontend migration  
- **Phase 3 (Week 3)**: Deprecate legacy single-part field

## API Changes

### Request Structure Changes

#### Quick Scan
```typescript
// OLD (Still supported for backward compatibility)
interface QuickScanRequest {
  body_part: string;
  form_data: FormData;
  user_id?: string;
}

// NEW (Recommended)
interface QuickScanRequest {
  body_parts: string[];  // Array of selected body parts
  parts_relationship?: 'related' | 'unrelated' | 'auto-detect';
  form_data: FormData;
  user_id?: string;
  // body_part is now optional/deprecated
}
```

#### Deep Dive
```typescript
// OLD (Still supported)
interface DeepDiveStartRequest {
  body_part: string;
  form_data: FormData;
  user_id?: string;
}

// NEW (Recommended)
interface DeepDiveStartRequest {
  body_parts: string[];
  parts_relationship?: 'related' | 'unrelated' | 'auto-detect';
  form_data: FormData;
  user_id?: string;
}
```

### Response Structure Changes
```typescript
// Enhanced response includes both formats
interface ScanResponse {
  scan_id: string;
  analysis: AnalysisResult;
  
  // Backward compatibility field
  body_part?: string;  // Single part (only if one part selected)
  
  // New fields
  body_parts: string[];  // Always present
  is_multi_part: boolean;
  parts_relationship?: 'related' | 'unrelated' | 'auto-detect';
  
  confidence: number;
  usage: object;
  model: string;
  status: 'success' | 'error';
}
```

## Frontend Implementation Steps

### 1. Update State Management

```typescript
// components/HealthScan3D.tsx
import { useState } from 'react';

interface HealthScan3DProps {
  onPartsSelected: (parts: string[]) => void;
  maxSelections?: number;
}

export const HealthScan3D = ({ onPartsSelected, maxSelections = 5 }: HealthScan3DProps) => {
  const [selectedParts, setSelectedParts] = useState<string[]>([]);
  const [partsRelationship, setPartsRelationship] = useState<'related' | 'unrelated' | 'auto-detect'>('auto-detect');

  const handlePartClick = (part: string) => {
    setSelectedParts(prev => {
      // Toggle selection
      if (prev.includes(part)) {
        const updated = prev.filter(p => p !== part);
        onPartsSelected(updated);
        return updated;
      }
      
      // Add if under limit
      if (prev.length < maxSelections) {
        const updated = [...prev, part];
        onPartsSelected(updated);
        return updated;
      }
      
      // Replace oldest if at limit
      const updated = [...prev.slice(1), part];
      onPartsSelected(updated);
      return updated;
    });
  };

  // Visual feedback for relationships
  const getPartColor = (part: string) => {
    if (selectedParts.includes(part)) {
      return '#FF0000'; // Selected
    }
    if (isRelatedPart(part, selectedParts)) {
      return '#FFA500'; // Related to selection
    }
    return '#808080'; // Unselected
  };

  return (
    <div className="scan-3d-container">
      {/* 3D Model with click handlers */}
      <Canvas>
        <HumanModel
          onPartClick={handlePartClick}
          getPartColor={getPartColor}
          selectedParts={selectedParts}
        />
      </Canvas>

      {/* Selection Info */}
      {selectedParts.length > 0 && (
        <div className="selection-info">
          <h3>Selected Areas ({selectedParts.length})</h3>
          <ul>
            {selectedParts.map(part => (
              <li key={part}>
                {part}
                <button onClick={() => handlePartClick(part)}>×</button>
              </li>
            ))}
          </ul>
          
          {selectedParts.length > 1 && (
            <div className="relationship-selector">
              <label>These areas are:</label>
              <select 
                value={partsRelationship}
                onChange={(e) => setPartsRelationship(e.target.value as any)}
              >
                <option value="auto-detect">Let AI determine</option>
                <option value="related">Related symptoms</option>
                <option value="unrelated">Separate issues</option>
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

### 2. Update API Calls

```typescript
// services/healthScanApi.ts
export class HealthScanAPI {
  // Backward compatible wrapper
  static async quickScan(params: {
    body_part?: string;  // Deprecated
    body_parts?: string[];  // New
    parts_relationship?: string;
    form_data: any;
    user_id?: string;
  }) {
    // Normalize to new format
    const requestBody = {
      body_parts: params.body_parts || (params.body_part ? [params.body_part] : []),
      parts_relationship: params.parts_relationship || 'auto-detect',
      form_data: params.form_data,
      user_id: params.user_id
    };

    const response = await fetch('/api/quick-scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    return response.json();
  }

  static async deepDiveStart(params: {
    body_parts: string[];
    parts_relationship?: string;
    form_data: any;
    user_id?: string;
  }) {
    const response = await fetch('/api/deep-dive/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });

    return response.json();
  }
}
```

### 3. Relationship Detection Helper

```typescript
// utils/bodyPartRelationships.ts
const BODY_SYSTEM_GROUPS = {
  cardiac: ['chest', 'left arm', 'left shoulder', 'jaw', 'neck'],
  neurological: ['head', 'eyes', 'face', 'neck', 'spine'],
  digestive: ['abdomen', 'stomach', 'chest', 'throat'],
  musculoskeletal: ['back', 'neck', 'shoulders', 'hips', 'knees'],
  respiratory: ['chest', 'throat', 'nose', 'lungs']
};

export function detectRelationship(parts: string[]): 'related' | 'unrelated' | 'auto-detect' {
  if (parts.length <= 1) return 'auto-detect';
  
  // Check if parts belong to same system
  for (const [system, systemParts] of Object.entries(BODY_SYSTEM_GROUPS)) {
    const overlappingParts = parts.filter(p => 
      systemParts.some(sp => 
        p.toLowerCase().includes(sp) || sp.includes(p.toLowerCase())
      )
    );
    
    if (overlappingParts.length >= 2) {
      return 'related';
    }
  }
  
  return 'unrelated';
}

export function suggestRelatedParts(selectedParts: string[]): string[] {
  const suggestions = new Set<string>();
  
  selectedParts.forEach(part => {
    Object.values(BODY_SYSTEM_GROUPS).forEach(group => {
      if (group.some(p => p.includes(part.toLowerCase()))) {
        group.forEach(p => suggestions.add(p));
      }
    });
  });
  
  // Remove already selected parts
  selectedParts.forEach(p => suggestions.delete(p));
  
  return Array.from(suggestions);
}
```

### 4. UI Components for Multi-Part Display

```typescript
// components/ScanResults.tsx
interface ScanResultsProps {
  results: ScanResponse;
}

export const ScanResults = ({ results }: ScanResultsProps) => {
  const { body_parts, is_multi_part, parts_relationship, analysis } = results;

  return (
    <div className="scan-results">
      {/* Header with body parts */}
      <div className="results-header">
        <h2>
          Analysis for {is_multi_part ? 'Multiple Areas' : body_parts[0]}
        </h2>
        
        {is_multi_part && (
          <div className="multi-part-info">
            <span className="badge">
              {parts_relationship === 'related' ? '🔗 Related Symptoms' : '🔀 Separate Issues'}
            </span>
            <div className="parts-list">
              {body_parts.map((part, idx) => (
                <span key={part} className="part-tag">
                  {part}
                  {idx < body_parts.length - 1 && ' + '}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Analysis results */}
      <div className="analysis-content">
        {/* If multi-part and unrelated, show grouped analysis */}
        {is_multi_part && parts_relationship === 'unrelated' ? (
          <div className="grouped-analysis">
            <Alert>
              The AI has analyzed these as separate issues. 
              Review each area's findings below.
            </Alert>
            {/* Render grouped conditions */}
          </div>
        ) : (
          <div className="unified-analysis">
            {/* Standard single or related analysis */}
          </div>
        )}
      </div>
    </div>
  );
};
```

### 5. Migration Checklist

```typescript
// hooks/useMultiPartMigration.ts
export const useMultiPartMigration = () => {
  // Feature flag for gradual rollout
  const isMultiPartEnabled = useFeatureFlag('multi_part_selection');
  
  // Helper to convert old calls to new format
  const migrateApiCall = (oldParams: any) => {
    if ('body_part' in oldParams && !('body_parts' in oldParams)) {
      console.warn('Using deprecated body_part field. Please migrate to body_parts array.');
      return {
        ...oldParams,
        body_parts: [oldParams.body_part],
        parts_relationship: 'single'
      };
    }
    return oldParams;
  };

  return {
    isMultiPartEnabled,
    migrateApiCall,
    maxParts: isMultiPartEnabled ? 5 : 1
  };
};
```

## Testing Strategy

### Unit Tests
```typescript
// __tests__/multiPartSelection.test.ts
describe('Multi-Part Selection', () => {
  it('should handle single part selection (backward compat)', () => {
    const request = { body_part: 'chest', form_data: {} };
    const migrated = migrateToMultiPart(request);
    expect(migrated.body_parts).toEqual(['chest']);
  });

  it('should handle multiple parts', () => {
    const request = { body_parts: ['chest', 'left arm'], form_data: {} };
    expect(detectRelationship(request.body_parts)).toBe('related');
  });

  it('should limit selections to max allowed', () => {
    const parts = ['head', 'chest', 'arm', 'leg', 'foot', 'hand'];
    const limited = limitSelections(parts, 5);
    expect(limited).toHaveLength(5);
  });
});
```

### Integration Tests
```typescript
describe('API Integration', () => {
  it('should support both old and new request formats', async () => {
    // Test old format
    const oldResponse = await api.quickScan({
      body_part: 'chest',
      form_data: { symptoms: 'pain' }
    });
    expect(oldResponse.status).toBe('success');

    // Test new format
    const newResponse = await api.quickScan({
      body_parts: ['chest', 'left arm'],
      parts_relationship: 'related',
      form_data: { symptoms: 'pain' }
    });
    expect(newResponse.status).toBe('success');
    expect(newResponse.is_multi_part).toBe(true);
  });
});
```

## Performance Considerations

### 1. Debounce Multi-Selection
```typescript
const debouncedSelection = useMemo(
  () => debounce((parts: string[]) => {
    onPartsSelected(parts);
  }, 300),
  [onPartsSelected]
);
```

### 2. Optimize Re-renders
```typescript
const BodyPartSelector = React.memo(({ parts, onChange }) => {
  // Component only re-renders when parts actually change
  return <div>...</div>;
}, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.parts) === JSON.stringify(nextProps.parts);
});
```

### 3. Batch API Calls
```typescript
// If analyzing multiple unrelated parts, consider batching
const analyzeMultipleParts = async (parts: string[], formData: any) => {
  if (parts.length === 1) {
    return api.quickScan({ body_parts: parts, form_data: formData });
  }

  // For truly unrelated parts, could batch analyze
  const relationship = detectRelationship(parts);
  if (relationship === 'unrelated' && parts.length > 3) {
    // Consider warning user about complexity
    return api.quickScan({
      body_parts: parts,
      parts_relationship: 'unrelated',
      form_data: formData
    });
  }

  return api.quickScan({ body_parts: parts, parts_relationship: relationship, form_data: formData });
};
```

## Rollback Plan
If issues arise, the frontend can instantly revert by:
1. Limiting selection to single part
2. Using `body_part` field instead of `body_parts`
3. Backend maintains full backward compatibility

## Monitoring
Track these metrics during migration:
- Multi-part selection usage rate
- API response times for multi vs single
- User engagement with multi-part feature
- Error rates by selection count

## FAQ

### Q: What happens if frontend sends both body_part and body_parts?
A: Backend prioritizes `body_parts`. If only `body_part` exists, it's converted to single-element array.

### Q: How many parts can be selected?
A: Recommended limit is 5 parts to maintain analysis quality and performance.

### Q: Will old frontend code break?
A: No, full backward compatibility is maintained. Old code using `body_part` continues working.

### Q: How does the AI handle unrelated symptoms?
A: The AI analyzes each independently while checking for hidden connections, providing comprehensive coverage.

## Support
For migration assistance, contact the backend team or refer to the API documentation.