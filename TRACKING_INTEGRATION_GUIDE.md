# Long-Term Symptom Tracking Integration Guide

This guide shows how to integrate the symptom tracking feature into your Next.js frontend.

## Overview

The tracking system allows users to:
- Get AI suggestions for what symptoms to track from Quick Scans/Deep Dives
- Customize tracking metrics (name, axis labels)
- View mixed dashboard with active tracking + suggestions
- Log daily symptom values
- View historical data in charts
- Start tracking from past scans/dives

## API Endpoints

### 1. Generate Tracking Suggestion
After a Quick Scan or Deep Dive completes, call this to get AI suggestion:

```typescript
// POST /api/tracking/suggest
const response = await fetch(`${API_URL}/api/tracking/suggest`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    source_type: 'quick_scan', // or 'deep_dive'
    source_id: scanId,
    user_id: userId
  })
});

const data = await response.json();
// Returns:
{
  suggestion_id: "uuid",
  suggestion: {
    metric_name: "Headache Severity",
    metric_description: "Track daily headache pain levels",
    y_axis_label: "Pain Level (1-10)",
    y_axis_type: "numeric",
    y_axis_min: 0,
    y_axis_max: 10,
    tracking_type: "severity",
    confidence_score: 0.85
  },
  status: "success"
}
```

### 2. Configure/Approve Tracking

#### Option A: Quick Approve (no changes)
```typescript
// POST /api/tracking/approve/{suggestion_id}
const response = await fetch(`${API_URL}/api/tracking/approve/${suggestionId}`, {
  method: 'POST'
});
```

#### Option B: Customize Before Approving
```typescript
// POST /api/tracking/configure
const response = await fetch(`${API_URL}/api/tracking/configure`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    suggestion_id: suggestionId,
    user_id: userId,
    metric_name: "My Custom Name", // User edited
    y_axis_label: "Pain (1-10)", // User edited
    show_on_homepage: true
  })
});
```

### 3. Add Daily Data Point
```typescript
// POST /api/tracking/data
const response = await fetch(`${API_URL}/api/tracking/data`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    configuration_id: configId,
    user_id: userId,
    value: 7, // Today's pain level
    notes: "Headache after work", // Optional
    recorded_at: new Date().toISOString() // Optional, defaults to now
  })
});
```

### 4. Get Dashboard Data
```typescript
// GET /api/tracking/dashboard?user_id={userId}
const response = await fetch(`${API_URL}/api/tracking/dashboard?user_id=${userId}`);
const data = await response.json();

// Returns mixed array of active tracking + suggestions:
{
  dashboard_items: [
    {
      type: "active",
      id: "config-uuid",
      metric_name: "Headache Severity",
      y_axis_label: "Pain Level (1-10)",
      latest_value: 7,
      latest_date: "2024-01-15T10:00:00Z",
      trend: "increasing", // or "decreasing", "stable"
      chart_type: "line",
      color: "#3B82F6",
      data_points_count: 15
    },
    {
      type: "suggestion",
      id: "suggestion-uuid",
      metric_name: "Chest Pain Frequency",
      description: "Track how often chest pain occurs",
      source_type: "quick_scan",
      confidence_score: 0.75,
      created_at: "2024-01-14T08:00:00Z"
    }
  ],
  total_active: 3,
  total_suggestions: 2,
  status: "success"
}
```

### 5. Get Chart Data
```typescript
// GET /api/tracking/chart/{config_id}?days=30
const response = await fetch(`${API_URL}/api/tracking/chart/${configId}?days=30`);
const data = await response.json();

// Returns:
{
  chart_data: {
    config: {
      metric_name: "Headache Severity",
      x_axis_label: "Date",
      y_axis_label: "Pain Level (1-10)",
      y_axis_min: 0,
      y_axis_max: 10,
      chart_type: "line",
      color: "#3B82F6"
    },
    data: [
      { x: "2024-01-01T10:00:00Z", y: 5, notes: "" },
      { x: "2024-01-02T10:00:00Z", y: 7, notes: "Bad day" },
      // ... more data points
    ],
    statistics: {
      average: 6.2,
      min: 3,
      max: 9,
      count: 30
    }
  },
  status: "success"
}
```

### 6. Get Historical Scans/Dives
```typescript
// GET /api/tracking/past-scans?user_id={userId}&limit=20
const scans = await fetch(`${API_URL}/api/tracking/past-scans?user_id=${userId}&limit=20`);

// GET /api/tracking/past-dives?user_id={userId}&limit=20
const dives = await fetch(`${API_URL}/api/tracking/past-dives?user_id=${userId}&limit=20`);

// Both return:
{
  past_scans: [ // or past_dives
    {
      id: "scan-uuid",
      date: "2024-01-10T15:30:00Z",
      body_part: "head",
      primary_condition: "Tension Headache",
      symptoms: ["headache", "neck pain", "light sensitivity"],
      urgency: "medium",
      has_tracking: false // true if already tracking this
    }
  ],
  total: 15,
  status: "success"
}
```

## React Component Examples

### 1. Tracking Suggestion Card
```jsx
function TrackingSuggestionCard({ suggestion, onApprove, onCustomize }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold">{suggestion.metric_name}</h3>
      <p className="text-sm text-gray-600">{suggestion.description}</p>
      <div className="flex justify-between items-center mt-4">
        <span className="text-xs text-gray-500">
          Confidence: {(suggestion.confidence_score * 100).toFixed(0)}%
        </span>
        <div className="space-x-2">
          <button
            onClick={() => onCustomize(suggestion)}
            className="px-3 py-1 text-sm border rounded"
          >
            Customize
          </button>
          <button
            onClick={() => onApprove(suggestion.id)}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded"
          >
            Start Tracking
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 2. Active Tracking Card
```jsx
function ActiveTrackingCard({ item, onLogValue, onViewChart }) {
  const getTrendIcon = (trend) => {
    if (trend === 'increasing') return '↑';
    if (trend === 'decreasing') return '↓';
    return '→';
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-start">
        <h3 className="font-semibold">{item.metric_name}</h3>
        <span className="text-2xl" style={{ color: item.color }}>
          {getTrendIcon(item.trend)}
        </span>
      </div>
      
      <div className="mt-2">
        <p className="text-2xl font-bold">
          {item.latest_value || '--'}
          <span className="text-sm font-normal text-gray-600 ml-2">
            {item.y_axis_label}
          </span>
        </p>
        <p className="text-xs text-gray-500">
          {item.latest_date 
            ? new Date(item.latest_date).toLocaleDateString()
            : 'No data yet'}
        </p>
      </div>
      
      <div className="flex space-x-2 mt-4">
        <button
          onClick={() => onLogValue(item.id)}
          className="flex-1 px-3 py-1 text-sm bg-blue-500 text-white rounded"
        >
          Log Today
        </button>
        <button
          onClick={() => onViewChart(item.id)}
          className="flex-1 px-3 py-1 text-sm border rounded"
        >
          View Chart
        </button>
      </div>
    </div>
  );
}
```

### 3. Dashboard Grid
```jsx
function TrackingDashboard({ userId }) {
  const [dashboardItems, setDashboardItems] = useState([]);
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 4; // Adjust based on screen size

  useEffect(() => {
    fetchDashboard();
  }, [userId]);

  const fetchDashboard = async () => {
    const response = await fetch(`/api/tracking/dashboard?user_id=${userId}`);
    const data = await response.json();
    setDashboardItems(data.dashboard_items);
  };

  const visibleItems = dashboardItems.slice(
    currentPage * itemsPerPage,
    (currentPage + 1) * itemsPerPage
  );

  return (
    <div className="relative">
      {/* Navigation Arrows */}
      {currentPage > 0 && (
        <button
          onClick={() => setCurrentPage(currentPage - 1)}
          className="absolute left-0 top-1/2 transform -translate-y-1/2 z-10"
        >
          ←
        </button>
      )}
      
      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {visibleItems.map((item) => (
          item.type === 'active' ? (
            <ActiveTrackingCard
              key={item.id}
              item={item}
              onLogValue={handleLogValue}
              onViewChart={handleViewChart}
            />
          ) : (
            <TrackingSuggestionCard
              key={item.id}
              suggestion={item}
              onApprove={handleApprove}
              onCustomize={handleCustomize}
            />
          )
        ))}
      </div>
      
      {/* Right Arrow */}
      {(currentPage + 1) * itemsPerPage < dashboardItems.length && (
        <button
          onClick={() => setCurrentPage(currentPage + 1)}
          className="absolute right-0 top-1/2 transform -translate-y-1/2 z-10"
        >
          →
        </button>
      )}
    </div>
  );
}
```

### 4. Customize Tracking Modal
```jsx
function CustomizeTrackingModal({ suggestion, onSave, onClose }) {
  const [metricName, setMetricName] = useState(suggestion.metric_name);
  const [yAxisLabel, setYAxisLabel] = useState(suggestion.y_axis_label);

  const handleSave = async () => {
    const response = await fetch('/api/tracking/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        suggestion_id: suggestion.id,
        user_id: userId,
        metric_name: metricName,
        y_axis_label: yAxisLabel,
        show_on_homepage: true
      })
    });
    
    if (response.ok) {
      onSave();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-semibold mb-4">Customize Tracking</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Metric Name
            </label>
            <input
              type="text"
              value={metricName}
              onChange={(e) => setMetricName(e.target.value)}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">
              Y-Axis Label
            </label>
            <input
              type="text"
              value={yAxisLabel}
              onChange={(e) => setYAxisLabel(e.target.value)}
              className="w-full px-3 py-2 border rounded"
              placeholder="e.g., Pain Level (1-10)"
            />
          </div>
          
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-sm text-gray-600">
              <strong>Tracking Type:</strong> {suggestion.tracking_type}
            </p>
            <p className="text-sm text-gray-600">
              <strong>AI Confidence:</strong> {(suggestion.confidence_score * 100).toFixed(0)}%
            </p>
          </div>
        </div>
        
        <div className="flex space-x-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded"
          >
            Start Tracking
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 5. Chart View Component
```jsx
import { Line } from 'react-chartjs-2';

function TrackingChart({ configId }) {
  const [chartData, setChartData] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchChartData();
  }, [configId, days]);

  const fetchChartData = async () => {
    const response = await fetch(`/api/tracking/chart/${configId}?days=${days}`);
    const data = await response.json();
    setChartData(data.chart_data);
  };

  if (!chartData) return <div>Loading...</div>;

  const chartConfig = {
    data: {
      labels: chartData.data.map(d => new Date(d.x).toLocaleDateString()),
      datasets: [{
        label: chartData.config.metric_name,
        data: chartData.data.map(d => d.y),
        borderColor: chartData.config.color,
        backgroundColor: chartData.config.color + '20',
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (context) => {
              const point = chartData.data[context.dataIndex];
              return point.notes ? `Note: ${point.notes}` : '';
            }
          }
        }
      },
      scales: {
        y: {
          min: chartData.config.y_axis_min,
          max: chartData.config.y_axis_max,
          title: {
            display: true,
            text: chartData.config.y_axis_label
          }
        },
        x: {
          title: {
            display: true,
            text: chartData.config.x_axis_label
          }
        }
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">{chartData.config.metric_name}</h2>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-1 border rounded"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>
      
      <Line data={chartConfig.data} options={chartConfig.options} />
      
      <div className="grid grid-cols-4 gap-4 mt-6 text-center">
        <div>
          <p className="text-sm text-gray-600">Average</p>
          <p className="text-lg font-semibold">{chartData.statistics.average.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Min</p>
          <p className="text-lg font-semibold">{chartData.statistics.min}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Max</p>
          <p className="text-lg font-semibold">{chartData.statistics.max}</p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Data Points</p>
          <p className="text-lg font-semibold">{chartData.statistics.count}</p>
        </div>
      </div>
    </div>
  );
}
```

## Implementation Flow

### 1. After Quick Scan/Deep Dive Completes
```jsx
// In your scan completion handler
const handleScanComplete = async (scanResult) => {
  // Save scan result...
  
  // Generate tracking suggestion
  const trackingResponse = await fetch('/api/tracking/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: 'quick_scan',
      source_id: scanResult.scan_id,
      user_id: currentUser.id
    })
  });
  
  const trackingData = await trackingResponse.json();
  
  // Show suggestion to user
  if (trackingData.status === 'success') {
    showTrackingSuggestion(trackingData.suggestion);
  }
};
```

### 2. Historical Tracking
```jsx
function HistoricalScans({ userId }) {
  const [pastScans, setPastScans] = useState([]);

  const handleStartTracking = async (scan) => {
    // Generate suggestion from past scan
    const response = await fetch('/api/tracking/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_type: 'quick_scan',
        source_id: scan.id,
        user_id: userId
      })
    });
    
    const data = await response.json();
    if (data.status === 'success') {
      // Show customize modal or quick approve
      showTrackingOptions(data.suggestion);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Past Health Scans</h2>
      {pastScans.map(scan => (
        <div key={scan.id} className="flex justify-between items-center p-4 border rounded">
          <div>
            <p className="font-medium">{scan.primary_condition}</p>
            <p className="text-sm text-gray-600">
              {new Date(scan.date).toLocaleDateString()} - {scan.body_part}
            </p>
          </div>
          {!scan.has_tracking && (
            <button
              onClick={() => handleStartTracking(scan)}
              className="px-4 py-2 bg-blue-500 text-white rounded"
            >
              Start Tracking
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

## Best Practices

1. **Auto-suggest after scans**: Always call `/api/tracking/suggest` after Quick Scan/Deep Dive
2. **Mixed dashboard**: Show both active tracking and suggestions together
3. **Easy logging**: Make daily logging prominent with a big "Log Today" button
4. **Visual trends**: Use color-coded arrows (↑↓→) to show trends at a glance
5. **Retroactive tracking**: Allow users to browse past scans and start tracking
6. **Mobile responsive**: Stack cards vertically on mobile, use swipe gestures

## Error Handling

```typescript
const apiCall = async (url: string, options?: RequestInit) => {
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    
    if (data.status === 'error') {
      throw new Error(data.error || 'API request failed');
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    // Show user-friendly error message
    showToast({
      type: 'error',
      message: 'Failed to load tracking data. Please try again.'
    });
    throw error;
  }
};
```

## State Management Example (Zustand)

```typescript
import { create } from 'zustand';

interface TrackingStore {
  dashboardItems: any[];
  activeConfigs: Map<string, any>;
  fetchDashboard: (userId: string) => Promise<void>;
  logDataPoint: (configId: string, value: number, notes?: string) => Promise<void>;
  approvesuggestion: (suggestionId: string) => Promise<void>;
}

export const useTrackingStore = create<TrackingStore>((set, get) => ({
  dashboardItems: [],
  activeConfigs: new Map(),
  
  fetchDashboard: async (userId) => {
    const data = await apiCall(`/api/tracking/dashboard?user_id=${userId}`);
    set({ dashboardItems: data.dashboard_items });
  },
  
  logDataPoint: async (configId, value, notes) => {
    await apiCall('/api/tracking/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        configuration_id: configId,
        user_id: getCurrentUser().id,
        value,
        notes
      })
    });
    
    // Refresh dashboard
    await get().fetchDashboard(getCurrentUser().id);
  },
  
  approveSuggestion: async (suggestionId) => {
    await apiCall(`/api/tracking/approve/${suggestionId}`, {
      method: 'POST'
    });
    
    // Refresh dashboard
    await get().fetchDashboard(getCurrentUser().id);
  }
}));
```

## Deployment Checklist

- [ ] Run database migrations in Supabase
- [ ] Update environment variables with API endpoints
- [ ] Test tracking suggestion generation after scans
- [ ] Verify dashboard mixing active + suggestions
- [ ] Test chart rendering with real data
- [ ] Mobile responsiveness check
- [ ] Error state handling
- [ ] Loading states for all async operations