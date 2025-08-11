# Photo Analysis Complete Frontend Implementation Guide

## Table of Contents
1. [Core Photo Analysis Flow](#core-photo-analysis-flow)
2. [API Endpoints Reference](#api-endpoints-reference)
3. [Data Models & Types](#data-models--types)
4. [Implementation Steps](#implementation-steps)
5. [Advanced Features](#advanced-features)
6. [Error Handling](#error-handling)
7. [Security Considerations](#security-considerations)
8. [Best Practices](#best-practices)

## Core Photo Analysis Flow

### Complete User Journey
```
1. User initiates photo analysis
   ↓
2. Frontend categorizes photo (optional)
   ↓
3. Create or reuse session
   ↓
4. Upload photos to session
   ↓
5. Analyze photos with AI
   ↓
6. Display results & suggestions
   ↓
7. Enable follow-up tracking
   ↓
8. Configure reminders (optional)
   ↓
9. View progression over time
```

## API Endpoints Reference

### 1. Photo Categorization (Optional First Step)
```typescript
POST /api/photo-analysis/categorize
Content-Type: multipart/form-data

FormData:
- photo: File (image file)
- session_id?: string (optional, to maintain context)

Response:
{
  category: string,        // "skin", "wound", "rash", etc.
  confidence: number,       // 0.0 to 1.0
  subcategory?: string,     // More specific classification
  session_context?: {       // Context from existing session
    existing_condition: string,
    previous_analyses: number
  }
}
```

### 2. Session Management

#### Create New Session
```typescript
POST /api/photo-analysis/sessions
Content-Type: application/json

Body:
{
  user_id: string,
  condition_name: string,    // "Mole on left arm", "Healing cut", etc.
  is_sensitive: boolean,      // For privacy settings
  initial_notes?: string      // Optional initial observations
}

Response:
{
  session_id: string,
  created_at: string,
  status: "active"
}
```

#### Get User's Sessions
```typescript
GET /api/photo-analysis/sessions?user_id={userId}&limit=20&offset=0

Response:
{
  sessions: [
    {
      id: string,
      condition_name: string,
      created_at: string,
      last_photo_at?: string,
      photo_count: number,
      analysis_count: number,
      is_sensitive: boolean,
      latest_summary?: string,
      thumbnail_url?: string
    }
  ],
  total: number,
  has_more: boolean
}
```

#### Get Session Details
```typescript
GET /api/photo-analysis/session/{sessionId}

Response:
{
  session: {
    id: string,
    condition_name: string,
    created_at: string,
    photos: Array<PhotoRecord>,
    analyses: Array<AnalysisRecord>,
    reminders: Array<ReminderRecord>
  }
}
```

### 3. Photo Upload

```typescript
POST /api/photo-analysis/upload
Content-Type: multipart/form-data

FormData:
- photos: File[] (multiple image files)
- session_id?: string (optional, creates new if not provided)
- metadata?: JSON string with:
  {
    tags: string[],
    notes: string,
    lighting_conditions: string,
    distance_cm: number
  }

Response:
{
  session_id: string,
  uploaded_photos: [
    {
      photo_id: string,
      url: string,
      thumbnail_url: string,
      metadata: object,
      upload_timestamp: string
    }
  ],
  requires_action?: {
    type: "needs_better_quality" | "needs_different_angle",
    message: string,
    suggestions: string[]
  }
}
```

### 4. Photo Analysis

```typescript
POST /api/photo-analysis/analyze
Content-Type: application/json

Body:
{
  session_id: string,
  photo_ids: string[],           // Photos to analyze
  context?: string,               // Additional context
  comparison_photo_ids?: string[], // For progression analysis
  temporary_analysis: boolean      // If true, results expire after 24h
}

Response:
{
  analysis_id: string,
  analysis: {
    primary_observations: {
      condition_type: string,
      severity: "mild" | "moderate" | "severe",
      characteristics: string[],
      size_mm?: { width: number, height: number },
      color_description: string,
      texture: string,
      symmetry: "symmetric" | "asymmetric",
      borders: "regular" | "irregular"
    },
    medical_insights: {
      possible_conditions: Array<{
        name: string,
        likelihood: "low" | "medium" | "high",
        reasoning: string
      }>,
      urgency_level: "monitor" | "schedule_appointment" | "seek_care_soon" | "immediate_attention",
      red_flags: string[],
      reassuring_signs: string[]
    },
    recommendations: {
      immediate_actions: string[],
      monitoring_guidance: string[],
      when_to_seek_care: string[],
      self_care_tips: string[]
    },
    tracking_suggestions: {
      metrics_to_track: string[],
      photo_frequency: string,
      important_changes: string[]
    }
  },
  comparison?: {
    changes_detected: boolean,
    progression: "improving" | "stable" | "worsening" | "unclear",
    specific_changes: string[],
    percentage_change?: number,
    visual_overlay_url?: string
  },
  expires_at?: string  // If temporary_analysis is true
}
```

### 5. Follow-Up Photos

```typescript
POST /api/photo-analysis/session/{sessionId}/follow-up
Content-Type: multipart/form-data

FormData:
- photos: File[] (new follow-up photos)
- notes?: string
- symptoms_update?: JSON string with symptom changes
- compare_with?: string (analysis_id to compare against)

Response:
{
  follow_up_id: string,
  photos_added: number,
  auto_analysis?: {
    progression: string,
    key_changes: string[],
    continue_monitoring: boolean
  },
  next_reminder?: {
    date: string,
    message: string
  }
}
```

### 6. Timeline & Progression

#### Get Session Timeline
```typescript
GET /api/photo-analysis/session/{sessionId}/timeline

Response:
{
  timeline: [
    {
      date: string,
      type: "photo" | "analysis" | "reminder" | "note",
      content: object,
      milestone?: boolean
    }
  ],
  progression_summary: {
    overall_trend: string,
    total_duration_days: number,
    improvement_rate?: number
  }
}
```

#### Get Progression Analysis
```typescript
GET /api/photo-analysis/session/{sessionId}/progression-analysis

Response:
{
  progression_data: {
    metrics: {
      size_trend: Array<{date: string, value: number}>,
      color_changes: Array<{date: string, description: string}>,
      healing_progress: number  // 0-100%
    },
    velocity: {
      current_rate: string,
      acceleration: "increasing" | "steady" | "decreasing",
      projected_timeline: string
    },
    milestones: Array<{
      date: string,
      description: string,
      photo_id?: string
    }>,
    recommendations_based_on_trend: string[]
  }
}
```

### 7. Reminders Configuration

```typescript
POST /api/photo-analysis/reminders/configure
Content-Type: application/json

Body:
{
  session_id: string,
  analysis_id: string,
  enabled: boolean,
  interval_days: number,        // How often to remind
  reminder_method: "email" | "sms" | "in_app" | "none",
  reminder_text: string,        // "Time to check on your healing wound"
  contact_info?: {
    email?: string,
    phone?: string
  }
}

Response:
{
  reminder_id: string,
  next_reminder_date: string,
  schedule: Array<{
    date: string,
    status: "pending" | "sent" | "acknowledged"
  }>
}
```

### 8. Monitoring Suggestions

```typescript
POST /api/photo-analysis/monitoring/suggest
Content-Type: application/json

Body:
{
  analysis_id: string,
  condition_context?: {
    duration_days: number,
    previous_treatments: string[],
    risk_factors: string[]
  }
}

Response:
{
  monitoring_plan: {
    recommended_frequency: string,
    key_indicators: string[],
    photo_tips: {
      lighting: string,
      angles: string[],
      distance: string,
      background: string
    },
    warning_signs: string[],
    expected_timeline: {
      initial_improvement: string,
      significant_change: string,
      full_resolution: string
    }
  }
}
```

### 9. Analysis History

```typescript
GET /api/photo-analysis/session/{sessionId}/analysis-history?current_analysis_id={analysisId}

Response:
{
  history: Array<{
    analysis_id: string,
    date: string,
    key_findings: string[],
    severity: string,
    photo_count: number
  }>,
  comparison_available: boolean,
  trend_analysis?: {
    direction: string,
    confidence: number
  }
}
```

## Data Models & Types

### TypeScript Interfaces

```typescript
interface PhotoSession {
  id: string;
  user_id: string;
  condition_name: string;
  created_at: string;
  updated_at: string;
  is_sensitive: boolean;
  is_deleted: boolean;
  metadata?: {
    body_location?: string;
    initial_size_mm?: { width: number; height: number };
    tags?: string[];
  };
}

interface PhotoRecord {
  id: string;
  session_id: string;
  storage_url: string;
  thumbnail_url?: string;
  metadata: {
    original_filename: string;
    file_size: number;
    mime_type: string;
    dimensions: { width: number; height: number };
    exif_data?: object;
    upload_metadata?: object;
  };
  uploaded_at: string;
  is_deleted: boolean;
}

interface PhotoAnalysis {
  id: string;
  session_id: string;
  photo_ids: string[];
  analysis_type: "single" | "comparison" | "progression";
  results: AnalysisResults;
  model_used: string;
  confidence_score: number;
  created_at: string;
  expires_at?: string;
  is_temporary: boolean;
}

interface AnalysisResults {
  primary_observations: {
    condition_type: string;
    severity: "mild" | "moderate" | "severe";
    characteristics: string[];
    measurements?: object;
  };
  medical_insights: {
    possible_conditions: Condition[];
    urgency_level: UrgencyLevel;
    confidence: number;
  };
  recommendations: {
    immediate_actions: string[];
    monitoring_guidance: string[];
    self_care_tips: string[];
  };
  comparison_results?: ComparisonData;
}

interface Condition {
  name: string;
  likelihood: "low" | "medium" | "high";
  reasoning: string;
  icd_code?: string;
}

type UrgencyLevel = 
  | "monitor"
  | "schedule_appointment" 
  | "seek_care_soon"
  | "immediate_attention";

interface ComparisonData {
  baseline_photo_id: string;
  changes_detected: boolean;
  progression: "improving" | "stable" | "worsening" | "unclear";
  specific_changes: string[];
  confidence: number;
}
```

## Implementation Steps

### Step 1: Initial Setup

```typescript
// 1. Create photo analysis service
class PhotoAnalysisService {
  private baseUrl = '/api/photo-analysis';
  
  async categorizePhoto(photo: File, sessionId?: string): Promise<CategoryResponse> {
    const formData = new FormData();
    formData.append('photo', photo);
    if (sessionId) formData.append('session_id', sessionId);
    
    const response = await fetch(`${this.baseUrl}/categorize`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  }
  
  async createSession(data: CreateSessionData): Promise<SessionResponse> {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }
  
  async uploadPhotos(photos: File[], sessionId?: string, metadata?: object): Promise<UploadResponse> {
    const formData = new FormData();
    photos.forEach(photo => formData.append('photos', photo));
    if (sessionId) formData.append('session_id', sessionId);
    if (metadata) formData.append('metadata', JSON.stringify(metadata));
    
    const response = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  }
  
  async analyzePhotos(data: AnalyzeRequest): Promise<AnalysisResponse> {
    const response = await fetch(`${this.baseUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }
}
```

### Step 2: Photo Capture Component

```typescript
// 2. Implement photo capture with quality checks
interface PhotoCaptureProps {
  onPhotoCaptured: (photo: File) => void;
  guidelines?: PhotoGuidelines;
}

const PhotoCapture: React.FC<PhotoCaptureProps> = ({ onPhotoCaptured, guidelines }) => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedPhoto, setCapturedPhoto] = useState<File | null>(null);
  const [quality, setQuality] = useState<QualityCheck | null>(null);
  
  const validatePhotoQuality = async (photo: File): Promise<QualityCheck> => {
    // Check file size (should be > 100KB for adequate quality)
    if (photo.size < 100000) {
      return { passed: false, message: "Photo quality too low" };
    }
    
    // Check dimensions
    const img = new Image();
    const url = URL.createObjectURL(photo);
    
    return new Promise((resolve) => {
      img.onload = () => {
        URL.revokeObjectURL(url);
        if (img.width < 640 || img.height < 480) {
          resolve({ passed: false, message: "Resolution too low (min 640x480)" });
        } else {
          resolve({ passed: true, message: "Quality check passed" });
        }
      };
      img.src = url;
    });
  };
  
  const capturePhoto = async () => {
    // Implementation for capturing from camera stream
    // Convert to File object
    // Validate quality
    // Call onPhotoCaptured if quality passes
  };
  
  return (
    <div className="photo-capture-container">
      {/* Camera preview */}
      {/* Capture button */}
      {/* Quality feedback */}
      {/* Guidelines overlay */}
    </div>
  );
};
```

### Step 3: Analysis Results Display

```typescript
// 3. Display analysis results with visual indicators
interface AnalysisDisplayProps {
  analysis: AnalysisResults;
  sessionId: string;
  onRequestFollowUp: () => void;
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ 
  analysis, 
  sessionId, 
  onRequestFollowUp 
}) => {
  const getUrgencyColor = (level: UrgencyLevel): string => {
    const colors = {
      monitor: '#10b981',           // green
      schedule_appointment: '#f59e0b', // yellow
      seek_care_soon: '#f97316',    // orange
      immediate_attention: '#ef4444'  // red
    };
    return colors[level];
  };
  
  const renderConditionLikelihood = (likelihood: string) => {
    const levels = { low: 1, medium: 2, high: 3 };
    const level = levels[likelihood] || 0;
    
    return (
      <div className="likelihood-indicator">
        {[1, 2, 3].map(i => (
          <div 
            key={i}
            className={`bar ${i <= level ? 'active' : ''}`}
            style={{ 
              backgroundColor: i <= level ? getUrgencyColor('monitor') : '#e5e7eb' 
            }}
          />
        ))}
      </div>
    );
  };
  
  return (
    <div className="analysis-results">
      {/* Urgency Banner */}
      <div 
        className="urgency-banner"
        style={{ backgroundColor: getUrgencyColor(analysis.medical_insights.urgency_level) }}
      >
        <h3>{analysis.medical_insights.urgency_level.replace('_', ' ').toUpperCase()}</h3>
      </div>
      
      {/* Primary Observations */}
      <section className="observations">
        <h4>What We Observed</h4>
        <div className="observation-grid">
          <div>Condition Type: {analysis.primary_observations.condition_type}</div>
          <div>Severity: {analysis.primary_observations.severity}</div>
          {/* More observation details */}
        </div>
      </section>
      
      {/* Possible Conditions */}
      <section className="conditions">
        <h4>Possible Conditions</h4>
        {analysis.medical_insights.possible_conditions.map(condition => (
          <div key={condition.name} className="condition-card">
            <h5>{condition.name}</h5>
            {renderConditionLikelihood(condition.likelihood)}
            <p>{condition.reasoning}</p>
          </div>
        ))}
      </section>
      
      {/* Recommendations */}
      <section className="recommendations">
        <h4>Recommended Actions</h4>
        {analysis.recommendations.immediate_actions.length > 0 && (
          <div className="action-group immediate">
            <h5>Do This Now:</h5>
            <ul>
              {analysis.recommendations.immediate_actions.map((action, i) => (
                <li key={i}>{action}</li>
              ))}
            </ul>
          </div>
        )}
        {/* More recommendation sections */}
      </section>
      
      {/* Follow-up Button */}
      <button onClick={onRequestFollowUp} className="follow-up-btn">
        Schedule Follow-up Photos
      </button>
    </div>
  );
};
```

### Step 4: Progression Tracking

```typescript
// 4. Implement progression visualization
interface ProgressionTrackerProps {
  sessionId: string;
  analyses: PhotoAnalysis[];
}

const ProgressionTracker: React.FC<ProgressionTrackerProps> = ({ sessionId, analyses }) => {
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [progression, setProgression] = useState<ProgressionData | null>(null);
  
  useEffect(() => {
    loadProgressionData();
  }, [sessionId]);
  
  const loadProgressionData = async () => {
    const [timelineRes, progressionRes] = await Promise.all([
      fetch(`/api/photo-analysis/session/${sessionId}/timeline`),
      fetch(`/api/photo-analysis/session/${sessionId}/progression-analysis`)
    ]);
    
    setTimeline(await timelineRes.json());
    setProgression(await progressionRes.json());
  };
  
  const renderProgressionChart = () => {
    if (!progression) return null;
    
    // Use charting library like Chart.js or D3
    return (
      <LineChart
        data={progression.progression_data.metrics.size_trend}
        xAxis="date"
        yAxis="value"
        title="Size Progression Over Time"
      />
    );
  };
  
  const renderTimeline = () => {
    if (!timeline) return null;
    
    return (
      <div className="timeline">
        {timeline.timeline.map((event, index) => (
          <div key={index} className={`timeline-event ${event.type}`}>
            <div className="timeline-date">{formatDate(event.date)}</div>
            <div className="timeline-content">
              {event.type === 'photo' && <PhotoThumbnail data={event.content} />}
              {event.type === 'analysis' && <AnalysisSummary data={event.content} />}
              {event.milestone && <span className="milestone-badge">Milestone</span>}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  return (
    <div className="progression-tracker">
      <h3>Condition Progression</h3>
      
      {/* Overall trend indicator */}
      <div className="trend-summary">
        <span>Overall Trend: </span>
        <span className={`trend-${progression?.progression_data.velocity.current_rate}`}>
          {progression?.progression_data.velocity.current_rate}
        </span>
      </div>
      
      {/* Progression chart */}
      {renderProgressionChart()}
      
      {/* Timeline */}
      {renderTimeline()}
      
      {/* Milestones */}
      <div className="milestones">
        <h4>Key Milestones</h4>
        {progression?.progression_data.milestones.map((milestone, i) => (
          <div key={i} className="milestone">
            <span className="milestone-date">{milestone.date}</span>
            <span className="milestone-desc">{milestone.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## Advanced Features

### 1. Comparison View

```typescript
// Side-by-side comparison with overlay
const ComparisonView: React.FC<ComparisonProps> = ({ beforePhoto, afterPhoto, analysis }) => {
  const [viewMode, setViewMode] = useState<'side-by-side' | 'overlay' | 'slider'>('side-by-side');
  const [overlayOpacity, setOverlayOpacity] = useState(0.5);
  
  return (
    <div className="comparison-view">
      <div className="view-controls">
        <button onClick={() => setViewMode('side-by-side')}>Side by Side</button>
        <button onClick={() => setViewMode('overlay')}>Overlay</button>
        <button onClick={() => setViewMode('slider')}>Slider</button>
      </div>
      
      {viewMode === 'side-by-side' && (
        <div className="side-by-side">
          <img src={beforePhoto.url} alt="Before" />
          <img src={afterPhoto.url} alt="After" />
        </div>
      )}
      
      {viewMode === 'overlay' && (
        <div className="overlay-view">
          <img src={beforePhoto.url} alt="Before" />
          <img 
            src={afterPhoto.url} 
            alt="After" 
            style={{ opacity: overlayOpacity }}
          />
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.1"
            value={overlayOpacity}
            onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
          />
        </div>
      )}
      
      {/* Analysis overlay showing specific changes */}
      {analysis.comparison && (
        <div className="change-indicators">
          {analysis.comparison.specific_changes.map((change, i) => (
            <div key={i} className="change-marker">
              {change}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### 2. Smart Reminder System

```typescript
// Intelligent reminder scheduling based on condition
const ReminderConfiguration: React.FC<ReminderProps> = ({ sessionId, analysisId, condition }) => {
  const [reminderSettings, setReminderSettings] = useState({
    enabled: true,
    interval_days: 30,
    reminder_method: 'in_app',
    reminder_text: '',
    smart_scheduling: true
  });
  
  useEffect(() => {
    // Get AI-suggested reminder schedule
    getSuggestedSchedule();
  }, [condition]);
  
  const getSuggestedSchedule = async () => {
    const response = await fetch('/api/photo-analysis/monitoring/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        analysis_id: analysisId,
        condition_context: { condition_type: condition }
      })
    });
    
    const suggestions = await response.json();
    // Update reminder settings based on AI suggestions
  };
  
  const configureReminders = async () => {
    await fetch('/api/photo-analysis/reminders/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        analysis_id: analysisId,
        ...reminderSettings
      })
    });
  };
  
  return (
    <div className="reminder-config">
      {/* Reminder configuration UI */}
    </div>
  );
};
```

### 3. Export & Sharing

```typescript
// Generate shareable report for healthcare providers
const ExportReport: React.FC<ExportProps> = ({ sessionId, analyses }) => {
  const [reportFormat, setReportFormat] = useState<'pdf' | 'email' | 'print'>('pdf');
  const [includePhotos, setIncludePhotos] = useState(true);
  const [anonymize, setAnonymize] = useState(false);
  
  const generateReport = async () => {
    const response = await fetch('/api/photo-analysis/reports/photo-analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: getCurrentUserId(),
        session_ids: [sessionId],
        include_visual_timeline: includePhotos,
        anonymize: anonymize
      })
    });
    
    const report = await response.json();
    
    if (reportFormat === 'pdf') {
      downloadPDF(report);
    } else if (reportFormat === 'email') {
      await emailToProvider(report);
    }
  };
  
  return (
    <div className="export-options">
      {/* Export configuration UI */}
    </div>
  );
};
```

## Error Handling

### Common Error Scenarios

```typescript
class PhotoAnalysisErrorHandler {
  handleError(error: any, context: string): ErrorResponse {
    // Network errors
    if (!navigator.onLine) {
      return {
        type: 'network',
        message: 'No internet connection. Photos saved locally.',
        action: 'retry',
        canContinueOffline: true
      };
    }
    
    // File size errors
    if (error.message?.includes('file too large')) {
      return {
        type: 'validation',
        message: 'Photo exceeds 10MB limit. Please resize or compress.',
        action: 'resize',
        suggestions: ['Use camera app settings to reduce quality', 'Crop unnecessary areas']
      };
    }
    
    // API errors
    if (error.status === 429) {
      return {
        type: 'rate_limit',
        message: 'Too many requests. Please wait a moment.',
        action: 'wait',
        retryAfter: error.headers?.get('Retry-After') || 60
      };
    }
    
    // Model errors
    if (error.message?.includes('model unavailable')) {
      return {
        type: 'service',
        message: 'Analysis service temporarily unavailable.',
        action: 'fallback',
        fallbackAvailable: true
      };
    }
    
    // Invalid image format
    if (error.message?.includes('invalid image')) {
      return {
        type: 'validation',
        message: 'Unsupported image format. Please use JPG, PNG, or HEIC.',
        action: 'reupload'
      };
    }
    
    return {
      type: 'unknown',
      message: 'An unexpected error occurred.',
      action: 'contact_support',
      errorId: generateErrorId()
    };
  }
  
  async retryWithFallback(
    request: () => Promise<any>, 
    fallbacks: string[] = []
  ): Promise<any> {
    try {
      return await request();
    } catch (error) {
      if (fallbacks.length > 0) {
        const [nextFallback, ...remaining] = fallbacks;
        console.log(`Retrying with fallback: ${nextFallback}`);
        // Modify request to use fallback
        return this.retryWithFallback(request, remaining);
      }
      throw error;
    }
  }
}
```

### Offline Support

```typescript
class OfflinePhotoQueue {
  private queue: QueuedPhoto[] = [];
  
  async addToQueue(photo: File, sessionId: string, metadata: any) {
    const entry: QueuedPhoto = {
      id: generateId(),
      photo: await this.storeLocally(photo),
      sessionId,
      metadata,
      timestamp: Date.now(),
      status: 'queued'
    };
    
    this.queue.push(entry);
    await this.persistQueue();
    
    // Try to sync if online
    if (navigator.onLine) {
      this.syncQueue();
    }
  }
  
  private async storeLocally(photo: File): Promise<string> {
    // Use IndexedDB or localStorage for photo data
    const db = await openDB('photo-analysis', 1);
    const tx = db.transaction('photos', 'readwrite');
    const photoId = generateId();
    
    await tx.objectStore('photos').put({
      id: photoId,
      data: await photo.arrayBuffer(),
      type: photo.type,
      name: photo.name
    });
    
    return photoId;
  }
  
  async syncQueue() {
    const pending = this.queue.filter(item => item.status === 'queued');
    
    for (const item of pending) {
      try {
        const photo = await this.retrieveLocalPhoto(item.photo);
        await this.uploadPhoto(photo, item.sessionId, item.metadata);
        item.status = 'synced';
      } catch (error) {
        console.error('Sync failed for photo:', item.id);
        item.status = 'error';
      }
    }
    
    await this.persistQueue();
  }
}
```

## Security Considerations

### 1. Data Privacy

```typescript
// Implement client-side encryption for sensitive photos
class SecurePhotoHandler {
  private encryptionKey: CryptoKey | null = null;
  
  async initializeEncryption(userPassword: string) {
    const encoder = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      encoder.encode(userPassword),
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );
    
    this.encryptionKey = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: encoder.encode('photo-analysis-salt'),
        iterations: 100000,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  }
  
  async encryptPhoto(photo: File): Promise<EncryptedPhoto> {
    if (!this.encryptionKey) throw new Error('Encryption not initialized');
    
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const photoData = await photo.arrayBuffer();
    
    const encryptedData = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      this.encryptionKey,
      photoData
    );
    
    return {
      data: encryptedData,
      iv: Array.from(iv),
      metadata: {
        originalName: photo.name,
        type: photo.type,
        size: photo.size
      }
    };
  }
}
```

### 2. Authentication & Authorization

```typescript
// Secure API calls with proper authentication
class SecureApiClient {
  private token: string | null = null;
  private refreshToken: string | null = null;
  
  async makeAuthenticatedRequest(
    url: string, 
    options: RequestInit = {}
  ): Promise<Response> {
    // Ensure token is valid
    if (!this.token || this.isTokenExpired(this.token)) {
      await this.refreshAccessToken();
    }
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.token}`,
        'X-CSRF-Token': this.getCSRFToken()
      }
    });
    
    if (response.status === 401) {
      // Token expired, refresh and retry
      await this.refreshAccessToken();
      return this.makeAuthenticatedRequest(url, options);
    }
    
    return response;
  }
  
  private getCSRFToken(): string {
    // Get CSRF token from meta tag or cookie
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  }
}
```

### 3. Input Validation

```typescript
// Validate all inputs before sending to API
class InputValidator {
  validatePhotoFile(file: File): ValidationResult {
    const errors: string[] = [];
    
    // Check file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/heic', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      errors.push('Invalid file type');
    }
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      errors.push('File size exceeds 10MB');
    }
    
    // Check file name for malicious patterns
    if (!/^[\w\-. ]+$/.test(file.name)) {
      errors.push('Invalid file name');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
  
  sanitizeMetadata(metadata: any): object {
    // Remove any potentially dangerous fields
    const safe = {};
    const allowedFields = ['tags', 'notes', 'lighting_conditions', 'distance_cm'];
    
    for (const field of allowedFields) {
      if (metadata[field] !== undefined) {
        // Sanitize string inputs
        if (typeof metadata[field] === 'string') {
          safe[field] = this.sanitizeString(metadata[field]);
        } else if (Array.isArray(metadata[field])) {
          safe[field] = metadata[field].map(item => 
            typeof item === 'string' ? this.sanitizeString(item) : item
          );
        } else {
          safe[field] = metadata[field];
        }
      }
    }
    
    return safe;
  }
  
  private sanitizeString(input: string): string {
    // Remove HTML tags and dangerous characters
    return input
      .replace(/<[^>]*>/g, '')
      .replace(/[<>\"']/g, '')
      .trim();
  }
}
```

## Best Practices

### 1. Performance Optimization

```typescript
// Lazy loading and virtualization for photo galleries
const PhotoGallery: React.FC<GalleryProps> = ({ photos }) => {
  const [visiblePhotos, setVisiblePhotos] = useState<Photo[]>([]);
  const observerRef = useRef<IntersectionObserver>();
  
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            // Load high-res version
            loadHighResPhoto(entry.target.dataset.photoId);
          }
        });
      },
      { threshold: 0.1 }
    );
    
    return () => observerRef.current?.disconnect();
  }, []);
  
  const loadHighResPhoto = async (photoId: string) => {
    // Replace thumbnail with high-res version
  };
  
  return (
    <VirtualList
      items={photos}
      renderItem={(photo) => (
        <div 
          className="photo-item"
          data-photo-id={photo.id}
          ref={el => el && observerRef.current?.observe(el)}
        >
          <img src={photo.thumbnail_url} loading="lazy" />
        </div>
      )}
    />
  );
};
```

### 2. Accessibility

```typescript
// Ensure photo analysis is accessible
const AccessiblePhotoAnalysis: React.FC = () => {
  return (
    <div role="main" aria-label="Photo Analysis">
      <h1 id="analysis-title">Skin Condition Analysis</h1>
      
      {/* Photo upload with screen reader support */}
      <div role="region" aria-labelledby="upload-title">
        <h2 id="upload-title">Upload Photos</h2>
        <input
          type="file"
          accept="image/*"
          multiple
          aria-label="Select photos to analyze"
          aria-describedby="upload-help"
        />
        <p id="upload-help" className="sr-only">
          Select one or more photos of the affected area. 
          For best results, ensure good lighting and clear focus.
        </p>
      </div>
      
      {/* Analysis results with proper ARIA labels */}
      <div role="region" aria-labelledby="results-title" aria-live="polite">
        <h2 id="results-title">Analysis Results</h2>
        {/* Results content with proper semantic markup */}
      </div>
      
      {/* Keyboard navigation support */}
      <button
        onClick={handleAnalyze}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleAnalyze();
          }
        }}
        aria-label="Start photo analysis"
      >
        Analyze Photos
      </button>
    </div>
  );
};
```

### 3. Testing Strategy

```typescript
// Comprehensive testing for photo analysis
describe('PhotoAnalysisService', () => {
  let service: PhotoAnalysisService;
  
  beforeEach(() => {
    service = new PhotoAnalysisService();
  });
  
  describe('Photo Upload', () => {
    it('should validate file size before upload', async () => {
      const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.jpg');
      await expect(service.uploadPhotos([largeFile])).rejects.toThrow('File too large');
    });
    
    it('should handle network failures gracefully', async () => {
      // Mock network failure
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
      
      const result = await service.uploadPhotos([testPhoto], undefined, { offline: true });
      expect(result.queued).toBe(true);
    });
    
    it('should compress images if needed', async () => {
      const photo = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const compressed = await service.compressPhoto(photo, { maxSize: 1024 * 1024 });
      expect(compressed.size).toBeLessThanOrEqual(1024 * 1024);
    });
  });
  
  describe('Analysis', () => {
    it('should retry with fallback model on failure', async () => {
      // Mock first call failure, second success
      global.fetch = jest.fn()
        .mockRejectedValueOnce(new Error('Model unavailable'))
        .mockResolvedValueOnce({ json: () => mockAnalysisResponse });
      
      const result = await service.analyzePhotos({
        session_id: 'test',
        photo_ids: ['photo1'],
        fallback_models: ['model2', 'model3']
      });
      
      expect(result).toBeDefined();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });
});
```

## Monitoring & Analytics

```typescript
// Track photo analysis usage and performance
class PhotoAnalysisAnalytics {
  trackEvent(eventName: string, properties: object) {
    // Send to analytics service
    if (window.analytics) {
      window.analytics.track(eventName, {
        ...properties,
        timestamp: new Date().toISOString(),
        session_id: this.getSessionId()
      });
    }
  }
  
  trackPhotoUpload(photoCount: number, totalSize: number) {
    this.trackEvent('photo_uploaded', {
      photo_count: photoCount,
      total_size_mb: totalSize / (1024 * 1024),
      upload_method: 'camera' // or 'gallery'
    });
  }
  
  trackAnalysisRequest(sessionId: string, photoIds: string[]) {
    const startTime = performance.now();
    
    return {
      complete: (response: any) => {
        const duration = performance.now() - startTime;
        this.trackEvent('analysis_completed', {
          session_id: sessionId,
          photo_count: photoIds.length,
          duration_ms: duration,
          model_used: response.model_used,
          confidence: response.confidence_score
        });
      },
      error: (error: any) => {
        this.trackEvent('analysis_failed', {
          session_id: sessionId,
          error_type: error.type,
          error_message: error.message
        });
      }
    };
  }
}
```

## Deployment Checklist

- [ ] All API endpoints properly authenticated
- [ ] File upload size limits enforced (10MB max)
- [ ] Image compression implemented for large files
- [ ] Offline queue functionality tested
- [ ] Error boundaries in place for all components
- [ ] Loading states for all async operations
- [ ] Accessibility standards met (WCAG 2.1 AA)
- [ ] Performance metrics within targets (<3s analysis time)
- [ ] Security headers configured (CSP, CORS)
- [ ] Analytics tracking implemented
- [ ] Privacy policy updated for photo storage
- [ ] SSL/TLS properly configured
- [ ] Rate limiting implemented
- [ ] Monitoring alerts configured
- [ ] Backup strategy for photo storage

## Support Resources

- API Documentation: `/api/docs`
- Status Page: `status.healthoracle.ai`
- Support Email: `support@healthoracle.ai`
- Developer Discord: `discord.gg/healthoracle`

---

This guide provides a complete implementation roadmap for the photo analysis feature. Follow the steps sequentially and refer to the advanced features section for enhanced functionality.