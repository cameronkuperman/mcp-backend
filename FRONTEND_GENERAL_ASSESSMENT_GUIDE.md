# Frontend Implementation Guide: General Assessment System

## Overview

This guide provides complete frontend implementation details for the General Assessment system - a category-based health assessment tool for concerns that don't fit the 3D body visualization model. This system is **completely separate** from the photo analysis system.

## System Components

```
Category Selector → Assessment Form → API Call → Results Display
                         ↓
                   Deep Dive Option → Conversational Q&A → Final Analysis
```

## API Endpoints

All endpoints are now live at:
- `POST /api/flash-assessment` - Quick text-based triage
- `POST /api/general-assessment` - Structured category assessment
- `POST /api/general-deepdive/start` - Begin conversational diagnosis
- `POST /api/general-deepdive/continue` - Submit answer, get next question
- `POST /api/general-deepdive/complete` - Get final analysis

## Component Architecture

### 1. Entry Point Component

```tsx
// GeneralHealthAssessment.tsx
import { useState } from 'react';
import CategorySelector from './CategorySelector';
import AssessmentForm from './AssessmentForm';
import FlashAssessment from './FlashAssessment';

export default function GeneralHealthAssessment() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showFlash, setShowFlash] = useState(false);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">How are you feeling?</h1>
      
      {/* Quick question option */}
      <button
        onClick={() => setShowFlash(true)}
        className="mb-6 text-blue-600 hover:text-blue-800"
      >
        Have a quick question? Try Flash Assessment →
      </button>

      {showFlash ? (
        <FlashAssessment onBack={() => setShowFlash(false)} />
      ) : selectedCategory ? (
        <AssessmentForm 
          category={selectedCategory}
          onBack={() => setSelectedCategory(null)}
        />
      ) : (
        <CategorySelector onSelect={setSelectedCategory} />
      )}
    </div>
  );
}
```

### 2. Category Selector

```tsx
// CategorySelector.tsx
const CATEGORIES = [
  {
    id: 'energy',
    label: 'Energy & Fatigue',
    icon: Battery,
    color: 'from-yellow-400 to-orange-500',
    description: 'Tired, exhausted, or low energy'
  },
  {
    id: 'mental',
    label: 'Mental Health',
    icon: Brain,
    color: 'from-purple-400 to-pink-500',
    description: 'Mood, anxiety, stress, or cognitive issues'
  },
  {
    id: 'sick',
    label: 'Feeling Sick',
    icon: Thermometer,
    color: 'from-red-400 to-rose-500',
    description: 'Cold, flu, or general illness symptoms'
  },
  {
    id: 'medication',
    label: 'Medication Side Effects',
    icon: Pill,
    color: 'from-green-400 to-teal-500',
    description: 'Reactions to medications'
  },
  {
    id: 'multiple',
    label: 'Multiple Issues',
    icon: Layers,
    color: 'from-indigo-400 to-blue-500',
    description: 'Several things wrong at once'
  },
  {
    id: 'unsure',
    label: "Not Sure What's Wrong",
    icon: HelpCircle,
    color: 'from-gray-400 to-slate-500',
    description: "Something's off but can't pinpoint it"
  },
  {
    id: 'physical',
    label: 'Physical Pain/Injury',
    icon: Activity,
    color: 'from-red-500 to-rose-600',
    description: 'Pain, injury, or physical discomfort'
  }
];

export default function CategorySelector({ onSelect }: { onSelect: (category: string) => void }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {CATEGORIES.map((category) => {
        const Icon = category.icon;
        return (
          <button
            key={category.id}
            onClick={() => onSelect(category.id)}
            className="p-6 rounded-lg border-2 border-gray-200 hover:border-gray-400 transition-all hover:shadow-lg"
          >
            <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${category.color} flex items-center justify-center mb-4`}>
              <Icon className="w-6 h-6 text-white" />
            </div>
            <h3 className="font-semibold text-lg mb-2">{category.label}</h3>
            <p className="text-sm text-gray-600">{category.description}</p>
          </button>
        );
      })}
    </div>
  );
}
```

### 3. Assessment Form

```tsx
// AssessmentForm.tsx
import { useState } from 'react';
import BaseFormFields from './BaseFormFields';
import CategorySpecificFields from './CategorySpecificFields';
import LocationSelector from './LocationSelector';
import AssessmentResults from './AssessmentResults';

export default function AssessmentForm({ category, onBack }: Props) {
  const [formData, setFormData] = useState({
    // Base fields
    symptoms: '',
    duration: '',
    impactLevel: 5,
    aggravatingFactors: [],
    triedInterventions: [],
    
    // Category-specific fields
    ...getCategoryDefaults(category),
    
    // Optional location
    bodyLocation: null
  });
  
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Show location selector for relevant categories
  const showLocation = ['physical', 'sick', 'medication', 'energy', 'mental'].includes(category);
  const locationRequired = category === 'physical';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('/api/general-assessment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          form_data: formData,
          user_id: getCurrentUserId() // Your auth method
        })
      });
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Assessment error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (results) {
    return <AssessmentResults results={results} category={category} formData={formData} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <button onClick={onBack} className="text-gray-600 hover:text-gray-800 mb-4">
        ← Back to categories
      </button>
      
      <h2 className="text-2xl font-bold">{getCategoryTitle(category)} Assessment</h2>
      
      {/* Base fields for all categories */}
      <BaseFormFields 
        formData={formData}
        onChange={(updates) => setFormData({...formData, ...updates})}
      />
      
      {/* Category-specific fields */}
      <CategorySpecificFields
        category={category}
        formData={formData}
        onChange={(updates) => setFormData({...formData, ...updates})}
      />
      
      {/* Optional location selector */}
      {showLocation && (
        <LocationSelector
          required={locationRequired}
          value={formData.bodyLocation}
          onChange={(location) => setFormData({...formData, bodyLocation: location})}
        />
      )}
      
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Analyzing...' : 'Get Assessment'}
      </button>
    </form>
  );
}
```

### 4. Category-Specific Fields

```tsx
// CategorySpecificFields.tsx
export default function CategorySpecificFields({ category, formData, onChange }: Props) {
  switch (category) {
    case 'energy':
      return (
        <>
          <div>
            <label className="block text-sm font-medium mb-2">Energy Pattern</label>
            <select 
              value={formData.energyPattern}
              onChange={(e) => onChange({ energyPattern: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">Select pattern</option>
              <option value="Morning">Worst in morning</option>
              <option value="Afternoon">Afternoon crash</option>
              <option value="Evening">Evening fatigue</option>
              <option value="All day">Constant fatigue</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Sleep Hours</label>
            <input
              type="text"
              value={formData.sleepHours}
              onChange={(e) => onChange({ sleepHours: e.target.value })}
              placeholder="e.g., 7-8 hours"
              className="w-full p-2 border rounded"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">How do you feel when waking up?</label>
            <select 
              value={formData.wakingUpFeeling}
              onChange={(e) => onChange({ wakingUpFeeling: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">Select feeling</option>
              <option value="Refreshed">Refreshed</option>
              <option value="Tired">Tired</option>
              <option value="Exhausted">Exhausted</option>
            </select>
          </div>
        </>
      );
      
    case 'physical':
      return (
        <>
          <div>
            <label className="block text-sm font-medium mb-2">Body Region</label>
            <select 
              value={formData.bodyRegion}
              onChange={(e) => onChange({ bodyRegion: e.target.value })}
              className="w-full p-2 border rounded"
              required
            >
              <option value="">Select region</option>
              <option value="head_neck">Head & Neck</option>
              <option value="chest">Chest</option>
              <option value="abdomen">Abdomen</option>
              <option value="back">Back</option>
              <option value="arms">Arms</option>
              <option value="legs">Legs</option>
              <option value="joints">Joints</option>
              <option value="skin">Skin</option>
              <option value="multiple">Multiple Areas</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Issue Type</label>
            <select 
              value={formData.issueType}
              onChange={(e) => onChange({ issueType: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">Select type</option>
              <option value="pain">Pain</option>
              <option value="injury">Injury</option>
              <option value="rash">Rash</option>
              <option value="swelling">Swelling</option>
              <option value="numbness">Numbness</option>
              <option value="weakness">Weakness</option>
              <option value="other">Other</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">When does it occur?</label>
            <select 
              value={formData.occurrencePattern}
              onChange={(e) => onChange({ occurrencePattern: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">Select pattern</option>
              <option value="constant">Constant</option>
              <option value="movement">With movement</option>
              <option value="rest">At rest</option>
              <option value="random">Random times</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Affected Side</label>
            <select 
              value={formData.affectedSide}
              onChange={(e) => onChange({ affectedSide: e.target.value })}
              className="w-full p-2 border rounded"
            >
              <option value="">Select if applicable</option>
              <option value="left">Left side</option>
              <option value="right">Right side</option>
              <option value="both">Both sides</option>
              <option value="center">Center/Middle</option>
            </select>
          </div>
          
          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.radiatingPain}
                onChange={(e) => onChange({ radiatingPain: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm">Pain radiates to other areas</span>
            </label>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Specific movements that trigger it</label>
            <textarea
              value={formData.specificMovements}
              onChange={(e) => onChange({ specificMovements: e.target.value })}
              placeholder="e.g., Hurts when bending forward, worse when climbing stairs"
              className="w-full p-2 border rounded h-20"
            />
          </div>
        </>
      );
      
    // Add other category cases...
    
    default:
      return null;
  }
}
```

### 5. Flash Assessment Component

```tsx
// FlashAssessment.tsx
export default function FlashAssessment({ onBack }: { onBack: () => void }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('/api/flash-assessment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: query,
          user_id: getCurrentUserId()
        })
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Flash assessment error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="space-y-6">
        <button onClick={() => setResult(null)} className="text-gray-600">
          ← Ask another question
        </button>
        
        <div className="bg-blue-50 p-6 rounded-lg">
          <p className="text-lg mb-4">{result.response}</p>
          
          <div className="mt-4 p-4 bg-white rounded">
            <p className="text-sm text-gray-600">Main concern identified:</p>
            <p className="font-medium">{result.main_concern}</p>
            
            <div className="mt-2 flex items-center gap-4">
              <span className={`px-3 py-1 rounded-full text-sm ${
                result.urgency === 'high' ? 'bg-red-100 text-red-800' :
                result.urgency === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-green-100 text-green-800'
              }`}>
                {result.urgency} urgency
              </span>
              <span className="text-sm text-gray-600">
                Confidence: {result.confidence}%
              </span>
            </div>
          </div>
          
          <div className="mt-4">
            <p className="font-medium mb-2">Recommended next step:</p>
            <NextStepButton 
              action={result.next_steps.recommended_action}
              reason={result.next_steps.reason}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <button onClick={onBack} className="text-gray-600">← Back</button>
      
      <div>
        <label className="block text-lg font-medium mb-2">
          What's your health question or concern?
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Describe what you're experiencing..."
          className="w-full p-3 border rounded-lg h-32"
          required
        />
      </div>
      
      <button
        type="submit"
        disabled={loading || !query.trim()}
        className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Analyzing...' : 'Get Quick Assessment'}
      </button>
    </form>
  );
}
```

### 6. Deep Dive Flow

```tsx
// DeepDiveFlow.tsx
export default function DeepDiveFlow({ category, formData, onComplete }: Props) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [questionNumber, setQuestionNumber] = useState(1);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  // Start deep dive session
  useEffect(() => {
    startDeepDive();
  }, []);

  const startDeepDive = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/general-deepdive/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          form_data: formData,
          user_id: getCurrentUserId()
        })
      });
      
      const data = await response.json();
      setSessionId(data.session_id);
      setCurrentQuestion(data.question);
      setQuestionNumber(1);
    } catch (error) {
      console.error('Start deep dive error:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!answer.trim() || !sessionId) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/general-deepdive/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          answer,
          question_number: questionNumber
        })
      });
      
      const data = await response.json();
      
      if (data.ready_for_analysis) {
        completeDeepDive();
      } else {
        setCurrentQuestion(data.question);
        setQuestionNumber(data.question_number);
        setAnswer('');
      }
    } catch (error) {
      console.error('Continue deep dive error:', error);
    } finally {
      setLoading(false);
    }
  };

  const completeDeepDive = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/general-deepdive/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          final_answer: answer
        })
      });
      
      const data = await response.json();
      setIsComplete(true);
      onComplete(data);
    } catch (error) {
      console.error('Complete deep dive error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (isComplete) {
    return <div>Generating your comprehensive analysis...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-medium">Deep Dive Assessment</h3>
          <span className="text-sm text-gray-600">
            Question {questionNumber} of ~5
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${(questionNumber / 5) * 100}%` }}
          />
        </div>
      </div>

      <div className="bg-gray-50 p-6 rounded-lg mb-6">
        <p className="text-lg">{currentQuestion}</p>
      </div>

      <div className="space-y-4">
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          className="w-full p-3 border rounded-lg h-32"
          disabled={loading}
        />
        
        <button
          onClick={submitAnswer}
          disabled={loading || !answer.trim()}
          className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Processing...' : 
           questionNumber >= 4 ? 'Submit Final Answer' : 'Next Question'}
        </button>
      </div>
    </div>
  );
}
```

### 7. Assessment Results

```tsx
// AssessmentResults.tsx
export default function AssessmentResults({ results, category, formData }: Props) {
  const [showDeepDive, setShowDeepDive] = useState(false);
  const [deepDiveResults, setDeepDiveResults] = useState(null);

  if (deepDiveResults) {
    return <DeepDiveResults results={deepDiveResults} />;
  }

  if (showDeepDive) {
    return (
      <DeepDiveFlow 
        category={category}
        formData={formData}
        onComplete={setDeepDiveResults}
      />
    );
  }

  const { analysis } = results;

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 p-6 rounded-lg">
        <h3 className="text-xl font-semibold mb-3">Assessment Results</h3>
        <p className="text-lg">{analysis.primary_assessment}</p>
        
        <div className="mt-4 flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-sm ${
            analysis.urgency === 'high' || analysis.urgency === 'emergency' ? 'bg-red-100 text-red-800' :
            analysis.urgency === 'medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-green-100 text-green-800'
          }`}>
            {analysis.urgency} urgency
          </span>
          <span className="text-sm text-gray-600">
            Confidence: {analysis.confidence}%
          </span>
        </div>
      </div>

      {analysis.key_findings.length > 0 && (
        <div>
          <h4 className="font-medium mb-2">Key Findings:</h4>
          <ul className="list-disc list-inside space-y-1">
            {analysis.key_findings.map((finding, i) => (
              <li key={i} className="text-gray-700">{finding}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.possible_causes.length > 0 && (
        <div>
          <h4 className="font-medium mb-2">Possible Causes:</h4>
          <div className="space-y-2">
            {analysis.possible_causes.map((cause, i) => (
              <div key={i} className="bg-gray-50 p-3 rounded">
                <div className="flex justify-between items-start">
                  <span className="font-medium">{cause.condition}</span>
                  <span className="text-sm text-gray-600">{cause.likelihood}% likely</span>
                </div>
                <p className="text-sm text-gray-700 mt-1">{cause.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.recommendations.length > 0 && (
        <div>
          <h4 className="font-medium mb-2">Recommendations:</h4>
          <ul className="list-disc list-inside space-y-1">
            {analysis.recommendations.map((rec, i) => (
              <li key={i} className="text-gray-700">{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.confidence < 80 && (
        <div className="bg-amber-50 p-4 rounded-lg">
          <p className="text-sm text-amber-800">
            The assessment confidence is moderate. Consider a Deep Dive assessment for more accurate analysis.
          </p>
          <button
            onClick={() => setShowDeepDive(true)}
            className="mt-2 text-amber-900 font-medium hover:underline"
          >
            Start Deep Dive Assessment →
          </button>
        </div>
      )}
    </div>
  );
}
```

## State Management

```tsx
// types/generalAssessment.ts
export interface GeneralAssessmentState {
  // Current flow
  mode: 'category' | 'flash' | 'form' | 'deepdive' | 'results';
  
  // Selected category
  category: string | null;
  
  // Form data
  formData: AssessmentFormData;
  
  // Results
  assessmentResults: AssessmentResponse | null;
  deepDiveResults: DeepDiveResponse | null;
  
  // Deep dive session
  sessionId: string | null;
  currentQuestion: string | null;
  questionNumber: number;
}

// Form data structure matching backend
export interface AssessmentFormData {
  // Base fields
  symptoms: string;
  duration: string;
  impactLevel: number;
  aggravatingFactors: string[];
  triedInterventions: string[];
  
  // Category-specific fields
  [key: string]: any;
  
  // Optional location
  bodyLocation?: {
    regions: string[];
    description?: string;
  };
}
```

## Integration Points

### 1. User Authentication
```tsx
// Get current user ID from your auth system
const getCurrentUserId = () => {
  // Your auth implementation
  return auth.currentUser?.id || null;
};
```

### 2. Navigation Integration
```tsx
// Add to your main health dashboard
<NavigationCard
  title="General Health Assessment"
  description="For symptoms that affect your whole body or multiple areas"
  icon={<Layers />}
  onClick={() => navigate('/health/general-assessment')}
/>
```

### 3. Results Storage
```tsx
// Results are automatically stored in database
// Access via timeline_events table for history view
```

## Error Handling

```tsx
// Wrap API calls in try-catch
try {
  const response = await fetch('/api/general-assessment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  const data = await response.json();
  if (data.error) {
    throw new Error(data.error);
  }
  
  return data;
} catch (error) {
  console.error('Assessment failed:', error);
  // Show user-friendly error message
  showError('Unable to complete assessment. Please try again.');
}
```

## Responsive Design

All components should be mobile-friendly:
- Category cards stack on mobile
- Forms use full width on small screens
- Deep dive questions display clearly on all devices
- Results are readable without horizontal scrolling

## Accessibility

- All form inputs have proper labels
- Color contrasts meet WCAG standards
- Keyboard navigation works throughout
- Screen readers can understand the flow
- Loading states are announced

## Performance Optimization

- Lazy load category-specific components
- Debounce form inputs
- Cache assessment results locally
- Prefetch common next steps
- Minimize re-renders during deep dive

## Summary

The General Assessment system provides a user-friendly interface for health concerns that don't fit the 3D body model. With 7 categories including the new Physical category, smart form flows, and optional deep dive capabilities, users can get comprehensive health assessments for any type of concern. The system is completely separate from photo analysis and integrates seamlessly with the existing health tracking infrastructure.