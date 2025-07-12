# Next.js Quick Scan Integration Guide

This comprehensive guide details how to integrate the Quick Scan feature with your Next.js application. The Quick Scan API is available on the `run_oracle.py` server at port 8000.

## Table of Contents
1. [API Endpoint Details](#api-endpoint-details)
2. [Next.js Implementation Guide](#nextjs-implementation-guide)
3. [Form Component Updates](#form-component-updates)
4. [Results Display Component](#results-display-component)
5. [Oracle Integration Flow](#oracle-integration-flow)
6. [Symptom Tracking Visualization](#symptom-tracking-visualization)
7. [Error Handling](#error-handling)
8. [Authentication Considerations](#authentication-considerations)
9. [Supabase Setup](#supabase-setup)
10. [Testing Checklist](#testing-checklist)

## API Endpoint Details

### Quick Scan Endpoint
**URL**: `POST http://localhost:8000/api/quick-scan`

**Request Headers**:
```javascript
{
  'Content-Type': 'application/json',
  'Authorization': 'Bearer YOUR_SUPABASE_JWT' // Optional for anonymous users
}
```

**Request Body**:
```typescript
interface QuickScanRequest {
  body_part: string;
  form_data: {
    symptoms: string;
    painType?: string[];
    painLevel?: number;
    duration?: string;
    dailyImpact?: string[];
    worseWhen?: string;
    betterWhen?: string;
    sleepImpact?: string;
    frequency?: string;
    whatTried?: string;
    didItHelp?: string;
    associatedSymptoms?: string;
  };
  user_id?: string;  // Optional - null for anonymous users
  model?: string;    // Optional - defaults to "deepseek/deepseek-chat"
}
```

**Response**:
```typescript
interface QuickScanResponse {
  scan_id: string;
  analysis: AnalysisResult;
  body_part: string;
  confidence: number;
  user_id: string | null;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model: string;
  status: 'success' | 'error';
}

interface AnalysisResult {
  confidence: number;
  primaryCondition: string;
  likelihood: 'Very likely' | 'Likely' | 'Possible';
  symptoms: string[];
  recommendations: string[];
  urgency: 'low' | 'medium' | 'high';
  differentials: Array<{
    condition: string;
    probability: number;
  }>;
  redFlags: string[];
  selfCare: string[];
  timeline: string;
  followUp: string;
  relatedSymptoms: string[];
}
```

## Next.js Implementation Guide

### 1. API Service Layer

Create a service file to handle Quick Scan API calls:

```typescript
// services/quickScanService.ts
import { createClient } from '@supabase/supabase-js';

const API_BASE_URL = process.env.NEXT_PUBLIC_ORACLE_API_URL || 'http://localhost:8000';

export interface QuickScanFormData {
  symptoms: string;
  painType?: string[];
  painLevel?: number;
  duration?: string;
  dailyImpact?: string[];
  worseWhen?: string;
  betterWhen?: string;
  sleepImpact?: string;
  frequency?: string;
  whatTried?: string;
  didItHelp?: string;
  associatedSymptoms?: string;
}

export const quickScanService = {
  async performQuickScan(
    bodyPart: string,
    formData: QuickScanFormData,
    userId?: string
  ) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/quick-scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          body_part: bodyPart,
          form_data: formData,
          user_id: userId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Quick scan failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.status === 'error') {
        throw new Error(data.error || 'Quick scan analysis failed');
      }

      return data;
    } catch (error) {
      console.error('Quick scan error:', error);
      throw error;
    }
  },

  async generateSummary(scanId: string, userId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/generate_summary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          quick_scan_id: scanId,
          user_id: userId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Summary generation failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Summary generation error:', error);
      throw error;
    }
  },
};
```

### 2. Quick Scan Hook

Create a custom hook for better state management:

```typescript
// hooks/useQuickScan.ts
import { useState, useCallback } from 'react';
import { quickScanService, QuickScanFormData } from '@/services/quickScanService';
import { useAuth } from '@/hooks/useAuth'; // Your auth hook

export const useQuickScan = () => {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState(null);

  const performScan = useCallback(async (
    bodyPart: string,
    formData: QuickScanFormData
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await quickScanService.performQuickScan(
        bodyPart,
        formData,
        user?.id
      );
      
      setScanResult(result);
      
      // If user is authenticated, generate summary
      if (user?.id && result.scan_id) {
        try {
          await quickScanService.generateSummary(result.scan_id, user.id);
        } catch (summaryError) {
          console.warn('Summary generation failed:', summaryError);
          // Don't fail the whole operation if summary fails
        }
      }
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Quick scan failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  const reset = useCallback(() => {
    setScanResult(null);
    setError(null);
  }, []);

  return {
    performScan,
    isLoading,
    error,
    scanResult,
    reset,
  };
};
```

## Form Component Updates

Update your QuickScanDemo component to include the new fields:

```tsx
// components/QuickScanDemo.tsx
import React, { useState } from 'react';
import { useQuickScan } from '@/hooks/useQuickScan';
import { motion, AnimatePresence } from 'framer-motion';

interface FormData {
  symptoms: string;
  painType: string[];
  painLevel: number;
  duration: string;
  dailyImpact: string[];
  worseWhen: string;
  betterWhen: string;
  sleepImpact: string;
  frequency: string;
  whatTried: string;
  didItHelp: string;
  associatedSymptoms: string;
}

export const QuickScanDemo: React.FC = () => {
  const { performScan, isLoading, error, scanResult } = useQuickScan();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedBodyPart, setSelectedBodyPart] = useState('');
  const [formData, setFormData] = useState<FormData>({
    symptoms: '',
    painType: [],
    painLevel: 5,
    duration: '',
    dailyImpact: [],
    worseWhen: '',
    betterWhen: '',
    sleepImpact: 'none',
    frequency: 'first',
    whatTried: '',
    didItHelp: '',
    associatedSymptoms: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedBodyPart) {
      alert('Please select a body part');
      return;
    }

    try {
      await performScan(selectedBodyPart, formData);
    } catch (err) {
      // Error is already handled in the hook
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleMultiSelect = (field: keyof FormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(value)
        ? prev[field].filter(item => item !== value)
        : [...prev[field], value]
    }));
  };

  if (scanResult) {
    return <QuickScanResults result={scanResult} onReset={() => window.location.reload()} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Body part selector */}
      <BodyPartSelector 
        selectedPart={selectedBodyPart}
        onSelectPart={setSelectedBodyPart}
      />

      {/* Basic symptoms */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Describe your symptoms
        </label>
        <textarea
          name="symptoms"
          value={formData.symptoms}
          onChange={handleInputChange}
          required
          placeholder="e.g., Sharp pain in lower back when bending..."
          className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white border 
            border-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          rows={3}
        />
      </div>

      {/* Advanced questions toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-blue-400 hover:text-blue-300 text-sm"
      >
        {showAdvanced ? 'Hide' : 'Show'} advanced questions
      </button>

      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-4"
          >
            {/* Frequency field */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Have you experienced this before?
              </label>
              <select
                name="frequency"
                value={formData.frequency}
                onChange={handleInputChange}
                className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white border 
                  border-gray-700 focus:border-blue-500"
              >
                <option value="first">This is the first time</option>
                <option value="rarely">Rarely (few times a year)</option>
                <option value="sometimes">Sometimes (monthly)</option>
                <option value="often">Often (weekly)</option>
                <option value="veryOften">Very often (daily)</option>
                <option value="constant">Constantly</option>
              </select>
            </div>

            {/* What tried fields */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Have you tried anything for this?
              </label>
              <div className="space-y-3">
                <textarea
                  name="whatTried"
                  value={formData.whatTried}
                  onChange={handleInputChange}
                  placeholder="What did you try? (e.g., rest, ice, medication...)"
                  rows={2}
                  className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white border 
                    border-gray-700 focus:border-blue-500"
                />
                <textarea
                  name="didItHelp"
                  value={formData.didItHelp}
                  onChange={handleInputChange}
                  placeholder="Did it help? How?"
                  rows={2}
                  className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white border 
                    border-gray-700 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Associated symptoms */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Any other symptoms elsewhere in your body?
              </label>
              <input
                type="text"
                name="associatedSymptoms"
                value={formData.associatedSymptoms}
                onChange={handleInputChange}
                placeholder="e.g., Fatigue, fever, other areas affected..."
                className="w-full px-4 py-3 rounded-xl bg-gray-800/50 text-white border 
                  border-gray-700 focus:border-blue-500"
              />
            </div>

            {/* Add other fields like painLevel, duration, etc. */}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit button */}
      <button
        type="submit"
        disabled={isLoading || !formData.symptoms || !selectedBodyPart}
        className="w-full py-4 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 
          disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium
          transition-all duration-200"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <Spinner className="w-5 h-5 animate-spin" />
            Analyzing symptoms...
          </span>
        ) : (
          'Analyze Symptoms'
        )}
      </button>

      {/* Error display */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/50 text-red-300">
          {error}
        </div>
      )}
    </form>
  );
};
```

## Results Display Component

Create a comprehensive results display:

```tsx
// components/QuickScanResults.tsx
import React from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle, Brain, FileText, TrendingUp, ChevronRight } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

interface QuickScanResultsProps {
  result: {
    scan_id: string;
    analysis: AnalysisResult;
    body_part: string;
    confidence: number;
    user_id: string | null;
  };
  onReset: () => void;
}

export const QuickScanResults: React.FC<QuickScanResultsProps> = ({ result, onReset }) => {
  const router = useRouter();
  const { user } = useAuth();
  const { analysis, confidence, body_part, scan_id } = result;

  const handleAskOracle = async () => {
    // Create Oracle context
    const oraclePrompt = confidence < 70
      ? `I just did a Quick Scan for ${body_part} symptoms but the confidence was low (${confidence}%). Can you help me understand my symptoms better?`
      : `I was diagnosed with ${analysis.primaryCondition} from Quick Scan. Can you provide more detailed insights?`;

    // Store context in session storage for Oracle to retrieve
    sessionStorage.setItem('quickScanContext', JSON.stringify({
      source: 'quick_scan',
      scanId: scan_id,
      bodyPart: body_part,
      analysis: analysis,
      confidence: confidence,
    }));

    // Navigate to Oracle chat
    router.push(`/chat?prompt=${encodeURIComponent(oraclePrompt)}`);
  };

  const handleGenerateReport = async () => {
    // Implementation for report generation
    console.log('Generate report for scan:', scan_id);
  };

  const handleTrackProgress = () => {
    if (!user) {
      router.push('/login?redirect=/dashboard/symptoms');
      return;
    }
    router.push('/dashboard/symptoms');
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'text-red-500 bg-red-500/20';
      case 'medium': return 'text-yellow-500 bg-yellow-500/20';
      default: return 'text-green-500 bg-green-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with confidence */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Analysis Results</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Confidence:</span>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="text-sm font-medium text-white">{confidence}%</span>
          </div>
        </div>
      </div>

      {/* Primary condition */}
      <div className="bg-gray-900/50 rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Primary Assessment</h3>
          <span className={`px-3 py-1 rounded-full text-sm ${getUrgencyColor(analysis.urgency)}`}>
            {analysis.urgency} urgency
          </span>
        </div>
        
        <div className="space-y-2">
          <p className="text-2xl font-bold text-white">{analysis.primaryCondition}</p>
          <p className="text-gray-400">{analysis.likelihood} based on your symptoms</p>
        </div>
      </div>

      {/* Symptoms identified */}
      <div className="bg-gray-900/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Symptoms Identified</h3>
        <div className="flex flex-wrap gap-2">
          {analysis.symptoms.map((symptom, index) => (
            <span 
              key={index}
              className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-sm"
            >
              {symptom}
            </span>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-gray-900/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Recommendations</h3>
        <ul className="space-y-3">
          {analysis.recommendations.map((rec, index) => (
            <li key={index} className="flex items-start gap-3">
              <span className="text-blue-400 mt-1">•</span>
              <span className="text-gray-300">{rec}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Red flags if any */}
      {analysis.redFlags.length > 0 && (
        <div className="bg-red-500/10 rounded-2xl p-6 border border-red-500/30">
          <div className="flex items-center gap-3 mb-4">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-white">Warning Signs to Watch</h3>
          </div>
          <ul className="space-y-2">
            {analysis.redFlags.map((flag, index) => (
              <li key={index} className="text-red-300 flex items-start gap-2">
                <span>•</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <div className="bg-gray-900/50 rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-lg font-semibold text-white">Next Steps</h4>
          {confidence < 70 && (
            <div className="flex items-center gap-2 text-sm text-amber-400">
              <AlertCircle className="w-4 h-4" />
              <span>Low confidence - consider deeper analysis</span>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <button 
            onClick={handleGenerateReport}
            className="px-6 py-4 rounded-xl bg-gray-800 hover:bg-gray-700 
              transition-all flex items-center justify-center gap-3 group"
          >
            <FileText className="w-5 h-5 text-gray-400 group-hover:text-gray-300" />
            <div className="text-left">
              <div className="font-medium text-white">Generate Detailed Report</div>
              <div className="text-xs text-gray-400">For your doctor visit</div>
            </div>
          </button>

          <button 
            onClick={handleTrackProgress}
            className="px-6 py-4 rounded-xl bg-gray-800 hover:bg-gray-700 
              transition-all flex items-center justify-center gap-3 group"
          >
            <TrendingUp className="w-5 h-5 text-gray-400 group-hover:text-gray-300" />
            <div className="text-left">
              <div className="font-medium text-white">Track Over Time</div>
              <div className="text-xs text-gray-400">Monitor symptom changes</div>
            </div>
          </button>
        </div>

        {/* Oracle prompt */}
        <div className={`p-4 rounded-xl transition-all ${
          confidence < 70 
            ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30' 
            : 'bg-gray-800/50 border border-gray-700'
        }`}>
          <button
            onClick={handleAskOracle}
            className="w-full flex items-center justify-between group"
          >
            <div className="flex items-center gap-3">
              <Brain className={`w-5 h-5 ${
                confidence < 70 ? 'text-purple-400' : 'text-gray-400'
              }`} />
              <div className="text-left">
                <div className="font-medium text-white">
                  {confidence < 70
                    ? 'Get a deeper analysis with Oracle AI'
                    : 'Have questions? Ask Oracle AI'}
                </div>
                <div className="text-xs text-gray-400">
                  Advanced reasoning for complex symptoms
                </div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-gray-300 
              transition-transform group-hover:translate-x-1" />
          </button>
        </div>
      </div>

      {/* Timeline and follow-up */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-900/50 rounded-xl p-4 border border-white/10">
          <h5 className="text-sm font-medium text-gray-400 mb-2">Expected Timeline</h5>
          <p className="text-white">{analysis.timeline}</p>
        </div>
        
        <div className="bg-gray-900/50 rounded-xl p-4 border border-white/10">
          <h5 className="text-sm font-medium text-gray-400 mb-2">Follow-up</h5>
          <p className="text-white">{analysis.followUp}</p>
        </div>
      </div>

      {/* Reset button */}
      <button
        onClick={onReset}
        className="w-full py-3 px-6 rounded-xl bg-gray-800 hover:bg-gray-700 
          text-white font-medium transition-all"
      >
        Start New Scan
      </button>
    </div>
  );
};
```

## Oracle Integration Flow

When escalating to Oracle from Quick Scan:

```typescript
// pages/chat.tsx or components/OracleChat.tsx
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

export const OracleChat = () => {
  const searchParams = useSearchParams();
  const [initialPrompt, setInitialPrompt] = useState('');
  const [quickScanContext, setQuickScanContext] = useState(null);

  useEffect(() => {
    // Check for Quick Scan context
    const contextStr = sessionStorage.getItem('quickScanContext');
    if (contextStr) {
      setQuickScanContext(JSON.parse(contextStr));
      sessionStorage.removeItem('quickScanContext');
    }

    // Check for prompt in URL
    const prompt = searchParams.get('prompt');
    if (prompt) {
      setInitialPrompt(decodeURIComponent(prompt));
    }
  }, [searchParams]);

  const handleSendMessage = async (message: string) => {
    // Include quick scan context if available
    const requestBody = {
      query: message,
      user_id: user?.id,
      conversation_id: conversationId,
      category: 'health-scan',
      metadata: quickScanContext ? {
        quick_scan_context: quickScanContext
      } : undefined
    };

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // Handle response...
  };

  // Rest of your Oracle chat implementation...
};
```

## Symptom Tracking Visualization

Create a symptom tracking dashboard:

```typescript
// components/SymptomTracker.tsx
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { supabase } from '@/lib/supabase';

interface SymptomData {
  occurrence_date: string;
  severity: number;
  symptom_name: string;
  body_part: string;
}

export const SymptomTracker: React.FC<{ userId: string }> = ({ userId }) => {
  const [symptoms, setSymptoms] = useState<SymptomData[]>([]);
  const [selectedSymptom, setSelectedSymptom] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSymptoms();
  }, [userId]);

  const fetchSymptoms = async () => {
    try {
      // Get unique symptoms
      const { data: uniqueSymptoms } = await supabase
        .from('symptom_tracking')
        .select('symptom_name, body_part')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });

      if (uniqueSymptoms && uniqueSymptoms.length > 0) {
        setSelectedSymptom(uniqueSymptoms[0].symptom_name);
        
        // Get symptom history
        const { data: history } = await supabase
          .from('symptom_tracking')
          .select('*')
          .eq('user_id', userId)
          .eq('symptom_name', uniqueSymptoms[0].symptom_name)
          .gte('occurrence_date', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())
          .order('occurrence_date', { ascending: true });

        setSymptoms(history || []);
      }
    } catch (error) {
      console.error('Error fetching symptoms:', error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = {
    labels: symptoms.map(s => new Date(s.occurrence_date).toLocaleDateString()),
    datasets: [{
      label: selectedSymptom,
      data: symptoms.map(s => s.severity),
      borderColor: 'rgb(99, 102, 241)',
      backgroundColor: 'rgba(99, 102, 241, 0.1)',
      tension: 0.4,
    }],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Symptom Severity Over Time',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 10,
        title: {
          display: true,
          text: 'Severity',
        },
      },
      x: {
        title: {
          display: true,
          text: 'Date',
        },
      },
    },
  };

  if (loading) return <div>Loading symptom data...</div>;

  return (
    <div className="space-y-6">
      {/* Symptom selector */}
      <select
        value={selectedSymptom}
        onChange={(e) => setSelectedSymptom(e.target.value)}
        className="px-4 py-2 rounded-lg bg-gray-800 text-white border border-gray-700"
      >
        {/* Map unique symptoms */}
      </select>

      {/* Chart */}
      <div className="bg-gray-900/50 rounded-2xl p-6 border border-white/10">
        <Line data={chartData} options={chartOptions} />
      </div>

      {/* Trend analysis */}
      <div className="bg-gray-900/50 rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Trend Analysis</h3>
        {/* Add trend calculation and display */}
      </div>
    </div>
  );
};
```

## Error Handling

Implement comprehensive error handling:

```typescript
// utils/errorHandler.ts
export class QuickScanError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'QuickScanError';
  }
}

export const handleQuickScanError = (error: any): string => {
  if (error instanceof QuickScanError) {
    switch (error.code) {
      case 'PARSE_ERROR':
        return 'Unable to analyze symptoms. Please try again.';
      case 'NETWORK_ERROR':
        return 'Connection error. Please check your internet.';
      case 'AUTH_ERROR':
        return 'Please sign in to save your scan results.';
      default:
        return error.message;
    }
  }
  
  return 'An unexpected error occurred. Please try again.';
};
```

## Authentication Considerations

Handle both authenticated and anonymous users:

```typescript
// components/QuickScanWrapper.tsx
export const QuickScanWrapper: React.FC = () => {
  const { user } = useAuth();
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);

  const handleScanComplete = (result: any) => {
    if (!user && result.confidence > 0) {
      setShowAuthPrompt(true);
    }
  };

  return (
    <>
      <QuickScanDemo onComplete={handleScanComplete} />
      
      {showAuthPrompt && !user && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold text-white mb-4">
              Save Your Results
            </h3>
            <p className="text-gray-400 mb-6">
              Sign in to save your scan results, track symptoms over time, 
              and get personalized health insights.
            </p>
            <div className="space-y-3">
              <button
                onClick={() => router.push('/login')}
                className="w-full py-3 px-6 rounded-xl bg-blue-600 hover:bg-blue-700 
                  text-white font-medium transition-all"
              >
                Sign In
              </button>
              <button
                onClick={() => setShowAuthPrompt(false)}
                className="w-full py-3 px-6 rounded-xl bg-gray-800 hover:bg-gray-700 
                  text-white font-medium transition-all"
              >
                Continue Without Saving
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

## Supabase Setup

1. **Run the migrations** in your Supabase SQL editor:
   - First run `quick_scan_tables.sql`
   - Then run `quick_scan_queries.sql`

2. **Enable RLS** - The migrations include RLS policies, ensure RLS is enabled:
   ```sql
   ALTER TABLE quick_scans ENABLE ROW LEVEL SECURITY;
   ALTER TABLE symptom_tracking ENABLE ROW LEVEL SECURITY;
   ```

3. **Test the policies** with sample queries:
   ```sql
   -- Test anonymous quick scan insert
   INSERT INTO quick_scans (body_part, form_data, analysis_result, confidence_score)
   VALUES ('head', '{"symptoms": "headache"}', '{"primaryCondition": "Tension Headache"}', 82);
   
   -- Test authenticated user query
   SELECT * FROM quick_scans WHERE user_id = auth.uid()::text;
   ```

## Testing Checklist

- [ ] Anonymous user can perform quick scan
- [ ] Authenticated user's scans are saved to database
- [ ] Symptom tracking records are created for authenticated users
- [ ] Low confidence scans show enhanced Oracle prompt
- [ ] Summary generation works for quick scans
- [ ] Oracle integration receives quick scan context
- [ ] Error handling works for malformed AI responses
- [ ] Results display all fields correctly
- [ ] Symptom tracking visualization loads historical data
- [ ] RLS policies prevent unauthorized access
- [ ] Generate report functionality (when implemented)
- [ ] Mobile responsive design works properly

## Environment Variables

Add to your `.env.local`:

```bash
NEXT_PUBLIC_ORACLE_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Common Issues and Solutions

1. **CORS errors**: Ensure the Oracle server has proper CORS configuration
2. **JSON parsing fails**: The API includes retry logic, but ensure prompt is optimized
3. **Anonymous scans not working**: Check RLS policies allow null user_id
4. **Symptom tracking duplicates**: The unique index prevents duplicate daily entries

This guide provides a complete implementation path for integrating Quick Scan into your Next.js application. The modular approach allows you to implement features incrementally while maintaining a working application throughout the process.