# Photo Analysis Frontend Implementation Guide

## Overview
This guide provides complete implementation details for integrating the Photo Analysis feature into your React/Next.js frontend.

## API Endpoints Reference

### 1. Photo Categorization
```typescript
POST /api/photo-analysis/categorize
Content-Type: multipart/form-data

Request:
- photo: File (required)
- session_id: string (optional)

Response:
{
  category: "medical_normal" | "medical_sensitive" | "medical_gore" | "unclear" | "non_medical" | "inappropriate",
  confidence: number,
  subcategory?: string,
  session_context?: {
    is_sensitive_session: boolean,
    previous_photos: number
  }
}
```

### 2. Photo Upload
```typescript
POST /api/photo-analysis/upload
Content-Type: multipart/form-data

Request:
- photos: File[] (required, max 5 files)
- user_id: string (required)
- session_id?: string
- condition_name?: string (required if no session_id)
- description?: string

Response:
{
  session_id: string,
  uploaded_photos: Array<{
    id: string,
    category: string,
    stored: boolean,
    preview_url: string | null
  }>,
  requires_action?: {
    type: "sensitive_modal" | "unclear_modal",
    affected_photos: string[],
    message: string
  }
}
```

### 3. Photo Analysis
```typescript
POST /api/photo-analysis/analyze

Request:
{
  session_id: string,
  photo_ids: string[],
  context?: string,
  comparison_photo_ids?: string[],
  temporary_analysis?: boolean
}

Response:
{
  analysis_id: string,
  analysis: {
    primary_assessment: string,
    confidence: number,
    visual_observations: string[],
    differential_diagnosis: string[],
    recommendations: string[],
    red_flags: string[],
    trackable_metrics: Array<{
      metric_name: string,
      current_value: number,
      unit: string,
      suggested_tracking: "daily" | "weekly" | "monthly"
    }>
  },
  comparison?: {
    days_between: number,
    changes: object,
    trend: "improving" | "worsening" | "stable",
    ai_summary: string
  },
  expires_at?: string
}
```

### 4. Get Sessions
```typescript
GET /api/photo-analysis/sessions?user_id={user_id}&limit=20&offset=0

Response:
{
  sessions: Array<{
    id: string,
    condition_name: string,
    created_at: string,
    last_photo_at: string,
    photo_count: number,
    analysis_count: number,
    is_sensitive: boolean,
    latest_summary: string,
    thumbnail_url: string
  }>,
  total: number,
  has_more: boolean
}
```

## React Component Examples

### 1. Photo Upload Component
```tsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, AlertCircle, Camera } from 'lucide-react';

interface PhotoUploadProps {
  onUploadComplete: (sessionId: string, photos: any[]) => void;
  existingSessionId?: string;
}

export function PhotoUpload({ onUploadComplete, existingSessionId }: PhotoUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conditionName, setConditionName] = useState('');
  const [description, setDescription] = useState('');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    
    if (acceptedFiles.length > 5) {
      setError('Maximum 5 photos at a time');
      return;
    }

    if (!existingSessionId && !conditionName) {
      setError('Please enter a condition name');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    acceptedFiles.forEach(file => {
      formData.append('photos', file);
    });
    formData.append('user_id', 'current-user-id'); // Get from auth
    
    if (existingSessionId) {
      formData.append('session_id', existingSessionId);
    } else {
      formData.append('condition_name', conditionName);
      formData.append('description', description);
    }

    try {
      const response = await fetch('/api/photo-analysis/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      
      // Handle special cases
      if (data.requires_action) {
        handleRequiredAction(data.requires_action);
      }

      onUploadComplete(data.session_id, data.uploaded_photos);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }, [conditionName, description, existingSessionId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.heic', '.heif', '.webp']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  const handleRequiredAction = (action: any) => {
    if (action.type === 'sensitive_modal') {
      // Show modal explaining sensitive content handling
      alert('Sensitive content detected. Photos will be analyzed temporarily without permanent storage.');
    } else if (action.type === 'unclear_modal') {
      // Show modal about unclear photos
      alert('Some photos are too unclear for analysis. Please retake with better lighting.');
    }
  };

  return (
    <div className="space-y-4">
      {!existingSessionId && (
        <div className="space-y-2">
          <input
            type="text"
            placeholder="Condition name (e.g., 'Arm rash')"
            value={conditionName}
            onChange={(e) => setConditionName(e.target.value)}
            className="w-full p-2 border rounded"
            required
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-2 border rounded"
            rows={2}
          />
        </div>
      )}

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} disabled={uploading} />
        
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        
        {isDragActive ? (
          <p>Drop photos here...</p>
        ) : (
          <div>
            <p className="mb-2">Drag & drop photos here, or click to select</p>
            <p className="text-sm text-gray-500">Maximum 5 photos, up to 10MB each</p>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {uploading && (
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-2">Uploading photos...</p>
        </div>
      )}
    </div>
  );
}
```

### 2. Photo Analysis Component
```tsx
import React, { useState } from 'react';
import { Eye, AlertTriangle, TrendingUp } from 'lucide-react';

interface PhotoAnalysisProps {
  sessionId: string;
  photoIds: string[];
  photos: Array<{ id: string; preview_url: string; category: string }>;
}

export function PhotoAnalysis({ sessionId, photoIds, photos }: PhotoAnalysisProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [context, setContext] = useState('');
  const [comparisonPhotoId, setComparisonPhotoId] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    
    try {
      const response = await fetch('/api/photo-analysis/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          photo_ids: photoIds,
          context: context || undefined,
          comparison_photo_ids: comparisonPhotoId ? [comparisonPhotoId] : undefined,
          temporary_analysis: photos.some(p => p.category === 'medical_sensitive')
        })
      });

      if (!response.ok) throw new Error('Analysis failed');
      
      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      console.error('Analysis error:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleTrackingApproval = async (metrics: any[]) => {
    const metricConfigs = metrics.map(m => ({
      metric_name: m.metric_name,
      y_axis_label: `${m.metric_name} (${m.unit})`,
      y_axis_min: 0,
      y_axis_max: m.current_value * 2,
      initial_value: m.current_value
    }));

    const response = await fetch('/api/photo-analysis/tracking/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_id: analysis.analysis_id,
        metric_configs: metricConfigs
      })
    });

    if (response.ok) {
      const data = await response.json();
      window.location.href = data.dashboard_url;
    }
  };

  return (
    <div className="space-y-6">
      {/* Photo Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {photos.map((photo) => (
          <div key={photo.id} className="relative">
            <img
              src={photo.preview_url || '/placeholder.png'}
              alt="Medical photo"
              className="w-full h-40 object-cover rounded-lg"
            />
            {photo.category === 'medical_sensitive' && (
              <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center">
                <span className="text-white text-sm">Sensitive Content</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Context Input */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Additional Context (optional)
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Any specific concerns or questions about these photos?"
          className="w-full p-3 border rounded-lg"
          rows={3}
        />
      </div>

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={analyzing || photoIds.length === 0}
        className="w-full bg-blue-500 text-white py-3 rounded-lg font-medium 
                   disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-600"
      >
        {analyzing ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
            Analyzing...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Eye className="h-5 w-5" />
            Analyze Photos
          </span>
        )}
      </button>

      {/* Analysis Results */}
      {analysis && (
        <div className="bg-white rounded-lg shadow-lg p-6 space-y-4">
          <h3 className="text-xl font-semibold">{analysis.analysis.primary_assessment}</h3>
          
          <div className="flex items-center gap-4 text-sm">
            <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full">
              {analysis.analysis.confidence}% confidence
            </span>
            {analysis.expires_at && (
              <span className="text-gray-500">
                Analysis expires in 24 hours
              </span>
            )}
          </div>

          {/* Red Flags */}
          {analysis.analysis.red_flags.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h4 className="font-medium text-red-800 flex items-center gap-2 mb-2">
                <AlertTriangle className="h-5 w-5" />
                Urgent Concerns
              </h4>
              <ul className="list-disc list-inside space-y-1">
                {analysis.analysis.red_flags.map((flag: string, i: number) => (
                  <li key={i} className="text-red-700">{flag}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Visual Observations */}
          <div>
            <h4 className="font-medium mb-2">Visual Observations</h4>
            <ul className="list-disc list-inside space-y-1 text-gray-700">
              {analysis.analysis.visual_observations.map((obs: string, i: number) => (
                <li key={i}>{obs}</li>
              ))}
            </ul>
          </div>

          {/* Recommendations */}
          <div>
            <h4 className="font-medium mb-2">Recommendations</h4>
            <ul className="list-disc list-inside space-y-1 text-gray-700">
              {analysis.analysis.recommendations.map((rec: string, i: number) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </div>

          {/* Trackable Metrics */}
          {analysis.analysis.trackable_metrics.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-4">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Track Progress
              </h4>
              <div className="space-y-2">
                {analysis.analysis.trackable_metrics.map((metric: any, i: number) => (
                  <div key={i} className="flex items-center justify-between">
                    <span>{metric.metric_name}: {metric.current_value} {metric.unit}</span>
                    <span className="text-sm text-gray-600">Track {metric.suggested_tracking}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => handleTrackingApproval(analysis.analysis.trackable_metrics)}
                className="mt-3 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Start Tracking
              </button>
            </div>
          )}

          {/* Comparison Results */}
          {analysis.comparison && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium mb-2">Progress Comparison</h4>
              <p className="text-sm text-gray-600 mb-2">
                {analysis.comparison.days_between} days between photos
              </p>
              <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm
                ${analysis.comparison.trend === 'improving' ? 'bg-green-100 text-green-700' : 
                  analysis.comparison.trend === 'worsening' ? 'bg-red-100 text-red-700' : 
                  'bg-gray-100 text-gray-700'}`}>
                {analysis.comparison.trend === 'improving' ? '✓' : 
                 analysis.comparison.trend === 'worsening' ? '✗' : '—'}
                {analysis.comparison.trend}
              </div>
              <p className="mt-2 text-gray-700">{analysis.comparison.ai_summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### 3. Photo Sessions List Component
```tsx
import React, { useState, useEffect } from 'react';
import { Calendar, Camera, FileText, ChevronRight } from 'lucide-react';

interface PhotoSession {
  id: string;
  condition_name: string;
  created_at: string;
  last_photo_at: string;
  photo_count: number;
  analysis_count: number;
  is_sensitive: boolean;
  latest_summary: string;
  thumbnail_url: string;
}

export function PhotoSessionsList({ userId }: { userId: string }) {
  const [sessions, setSessions] = useState<PhotoSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    loadSessions();
  }, [page]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/photo-analysis/sessions?user_id=${userId}&limit=20&offset=${page * 20}`
      );
      const data = await response.json();
      
      if (page === 0) {
        setSessions(data.sessions);
      } else {
        setSessions(prev => [...prev, ...data.sessions]);
      }
      setHasMore(data.has_more);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    return formatDate(dateString);
  };

  if (loading && page === 0) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold mb-4">Photo Sessions</h2>
      
      {sessions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Camera className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No photo sessions yet</p>
          <p className="text-sm text-gray-500 mt-2">
            Upload photos to start tracking conditions visually
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => window.location.href = `/photo-session/${session.id}`}
            >
              <div className="p-4 flex items-center gap-4">
                {/* Thumbnail */}
                <div className="flex-shrink-0">
                  {session.thumbnail_url ? (
                    <img
                      src={session.thumbnail_url}
                      alt=""
                      className="w-20 h-20 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center">
                      <Camera className="h-8 w-8 text-gray-400" />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-grow">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    {session.condition_name}
                    {session.is_sensitive && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
                        Sensitive
                      </span>
                    )}
                  </h3>
                  
                  <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      Started {formatTimeAgo(session.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Camera className="h-4 w-4" />
                      {session.photo_count} photos
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="h-4 w-4" />
                      {session.analysis_count} analyses
                    </span>
                  </div>

                  {session.latest_summary && (
                    <p className="text-sm text-gray-700 mt-2">
                      Latest: {session.latest_summary}
                    </p>
                  )}

                  {session.last_photo_at && (
                    <p className="text-xs text-gray-500 mt-1">
                      Last photo {formatTimeAgo(session.last_photo_at)}
                    </p>
                  )}
                </div>

                {/* Arrow */}
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          ))}
        </div>
      )}

      {hasMore && (
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={loading}
          className="w-full py-3 text-blue-500 hover:text-blue-600 font-medium"
        >
          {loading ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

### 4. Integration with Existing App

#### Add to your main dashboard:
```tsx
import { PhotoSessionsList } from '@/components/PhotoSessionsList';
import { PhotoUpload } from '@/components/PhotoUpload';

export function Dashboard() {
  const [showUpload, setShowUpload] = useState(false);
  
  return (
    <div>
      {/* Existing dashboard content */}
      
      <section className="mt-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Visual Tracking</h2>
          <button
            onClick={() => setShowUpload(true)}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg"
          >
            Upload Photos
          </button>
        </div>
        
        {showUpload ? (
          <PhotoUpload 
            onUploadComplete={(sessionId) => {
              setShowUpload(false);
              // Navigate to session or refresh list
            }}
          />
        ) : (
          <PhotoSessionsList userId={currentUser.id} />
        )}
      </section>
    </div>
  );
}
```

## Security Considerations

### 1. Frontend Image Preprocessing
```typescript
// Compress and resize images before upload
const preprocessImage = async (file: File): Promise<Blob> => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        
        // Max dimensions
        const maxWidth = 2048;
        const maxHeight = 2048;
        
        let width = img.width;
        let height = img.height;
        
        if (width > height) {
          if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width = (width * maxHeight) / height;
            height = maxHeight;
          }
        }
        
        canvas.width = width;
        canvas.height = height;
        
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => {
          resolve(blob!);
        }, 'image/jpeg', 0.85);
      };
      img.src = e.target!.result as string;
    };
    reader.readAsDataURL(file);
  });
};
```

### 2. Sensitive Content Handling
```typescript
// Component for sensitive photo warning
export function SensitiveContentWarning({ onAccept, onDecline }: {
  onAccept: () => void;
  onDecline: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-lg font-semibold mb-4">Sensitive Content Detected</h3>
        
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            We've detected that your photos contain sensitive medical content.
          </p>
          
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
            <p className="font-medium text-yellow-800 mb-1">Privacy Protection:</p>
            <ul className="list-disc list-inside space-y-1 text-yellow-700">
              <li>Photos will NOT be permanently stored</li>
              <li>Analysis will be temporary (24 hours)</li>
              <li>Data is encrypted during processing</li>
            </ul>
          </div>
          
          <p>
            Would you like to proceed with temporary analysis?
          </p>
        </div>
        
        <div className="flex gap-3 mt-6">
          <button
            onClick={onDecline}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onAccept}
            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Proceed Safely
          </button>
        </div>
      </div>
    </div>
  );
}
```

## Error Handling

```typescript
// Centralized error handler for photo operations
export const handlePhotoError = (error: any): string => {
  if (error.status === 413) {
    return 'File too large. Please use photos under 10MB.';
  }
  if (error.status === 400) {
    if (error.message?.includes('inappropriate')) {
      return 'Inappropriate content detected. Please upload appropriate medical photos only.';
    }
    return error.message || 'Invalid request';
  }
  if (error.status === 500) {
    return 'Analysis failed. Please try again or contact support.';
  }
  return 'An unexpected error occurred. Please try again.';
};
```

## Best Practices

1. **Progress Indicators**: Always show upload/analysis progress
2. **Preview Before Upload**: Let users review photos before uploading
3. **Batch Operations**: Allow selecting multiple photos for comparison
4. **Offline Support**: Cache analyses locally for offline viewing
5. **Accessibility**: Ensure all photo features work with screen readers

## Testing Checklist

- [ ] Test with various image formats (JPEG, PNG, HEIC)
- [ ] Test file size limits (should reject >10MB)
- [ ] Test sensitive content flow
- [ ] Test unclear photo handling
- [ ] Test session continuity
- [ ] Test analysis with comparisons
- [ ] Test tracking integration
- [ ] Test error scenarios
- [ ] Test on mobile devices
- [ ] Test with slow connections