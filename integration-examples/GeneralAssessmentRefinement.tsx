// General Assessment Refinement Component for Next.js Frontend
// Place this file in your Next.js app at: components/GeneralAssessmentRefinement.tsx
// This component handles answering follow-up questions to refine a general assessment

import React, { useState } from 'react';
import { ChevronRight, Brain, AlertCircle, TrendingUp, CheckCircle } from 'lucide-react';

interface RefinementProps {
  assessmentId: string;
  followUpQuestions: string[];
  originalConfidence: number;
  category: string;
  onRefinementComplete: (result: RefinementResult) => void;
  onSkip?: () => void;
}

interface RefinementResult {
  refinement_id: string;
  assessment_id: string;
  refined_analysis: any;
  confidence_improvement: number;
  original_confidence: number;
  refined_confidence: number;
  diagnostic_certainty: string;
  category: string;
}

interface Answer {
  question: string;
  answer: string;
}

export const GeneralAssessmentRefinement: React.FC<RefinementProps> = ({
  assessmentId,
  followUpQuestions,
  originalConfidence,
  category,
  onRefinementComplete,
  onSkip
}) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentQuestion = followUpQuestions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === followUpQuestions.length - 1;
  const progress = ((currentQuestionIndex + 1) / followUpQuestions.length) * 100;

  const handleNext = () => {
    if (!currentAnswer.trim()) {
      setError('Please provide an answer before continuing');
      return;
    }

    const newAnswer: Answer = {
      question: currentQuestion,
      answer: currentAnswer.trim()
    };

    const updatedAnswers = [...answers, newAnswer];
    setAnswers(updatedAnswers);
    setCurrentAnswer('');
    setError(null);

    if (isLastQuestion) {
      submitRefinement(updatedAnswers);
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const submitRefinement = async (allAnswers: Answer[]) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/general-assessment/refine`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          assessment_id: assessmentId,
          answers: allAnswers,
          user_id: localStorage.getItem('userId') // Adjust based on your auth setup
        })
      });

      if (!response.ok) {
        throw new Error('Failed to refine assessment');
      }

      const result: RefinementResult = await response.json();
      onRefinementComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    if (onSkip) {
      onSkip();
    }
  };

  const handleBack = () => {
    if (currentQuestionIndex > 0) {
      // Remove the last answer and go back
      const previousAnswers = answers.slice(0, -1);
      const previousAnswer = answers[answers.length - 1];
      setAnswers(previousAnswers);
      setCurrentAnswer(previousAnswer?.answer || '');
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-sm">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-blue-600" />
            <h2 className="text-xl font-semibold">Refine Your Assessment</h2>
          </div>
          {onSkip && (
            <button
              onClick={handleSkip}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Skip refinement
            </button>
          )}
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Question {currentQuestionIndex + 1} of {followUpQuestions.length}
        </p>
      </div>

      {/* Confidence Indicator */}
      <div className="mb-6 p-4 bg-blue-50 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">Current Confidence</p>
            <p className="text-2xl font-bold text-blue-600">{originalConfidence}%</p>
          </div>
          <TrendingUp className="w-8 h-8 text-green-500" />
          <div className="text-right">
            <p className="text-sm text-gray-600">Expected After Refinement</p>
            <p className="text-2xl font-bold text-green-600">
              {Math.min(originalConfidence + 15, 95)}%+
            </p>
          </div>
        </div>
      </div>

      {/* Question */}
      <div className="mb-6">
        <label className="block text-lg font-medium text-gray-900 mb-3">
          {currentQuestion}
        </label>
        <textarea
          value={currentAnswer}
          onChange={(e) => {
            setCurrentAnswer(e.target.value);
            setError(null);
          }}
          placeholder="Please provide as much detail as possible..."
          className={`w-full p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-500' : 'border-gray-300'
          }`}
          rows={4}
          disabled={isSubmitting}
        />
        {error && (
          <div className="mt-2 flex items-center gap-2 text-red-600">
            <AlertCircle className="w-4 h-4" />
            <p className="text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Previous Answers Summary */}
      {answers.length > 0 && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Your answers so far:</h3>
          <div className="space-y-2">
            {answers.map((ans, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                <div className="text-sm">
                  <span className="font-medium">Q{idx + 1}:</span> {ans.answer.substring(0, 50)}
                  {ans.answer.length > 50 && '...'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between">
        <button
          onClick={handleBack}
          disabled={currentQuestionIndex === 0 || isSubmitting}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Back
        </button>
        
        <button
          onClick={handleNext}
          disabled={isSubmitting}
          className={`px-6 py-2 rounded-lg flex items-center gap-2 text-white font-medium
            ${isSubmitting 
              ? 'bg-gray-400 cursor-not-allowed' 
              : isLastQuestion 
                ? 'bg-green-600 hover:bg-green-700' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
        >
          {isSubmitting ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              Refining...
            </>
          ) : isLastQuestion ? (
            <>
              Complete Refinement
              <CheckCircle className="w-4 h-4" />
            </>
          ) : (
            <>
              Next Question
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex gap-2">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div className="text-sm text-amber-800">
            <p className="font-medium mb-1">Why these questions?</p>
            <p>
              These follow-up questions help us narrow down the diagnosis and provide 
              more specific recommendations for your {category} concerns.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Example usage component showing the refined results
export const RefinementResults: React.FC<{ result: RefinementResult }> = ({ result }) => {
  const {
    refined_analysis,
    confidence_improvement,
    original_confidence,
    refined_confidence,
    diagnostic_certainty
  } = result;

  const getCertaintyColor = (certainty: string) => {
    switch (certainty) {
      case 'definitive': return 'text-green-600';
      case 'probable': return 'text-blue-600';
      case 'provisional': return 'text-amber-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-sm">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Refined Assessment Complete</h2>
        
        {/* Confidence Improvement */}
        <div className="p-4 bg-green-50 rounded-lg mb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Confidence Improved</p>
              <p className="text-3xl font-bold text-green-600">
                +{confidence_improvement}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Final Confidence</p>
              <p className="text-2xl font-bold">{refined_confidence}%</p>
            </div>
          </div>
        </div>

        {/* Diagnostic Certainty */}
        <div className="mb-4">
          <span className="text-sm text-gray-600">Diagnostic Certainty: </span>
          <span className={`font-semibold capitalize ${getCertaintyColor(diagnostic_certainty)}`}>
            {diagnostic_certainty}
          </span>
        </div>

        {/* Primary Assessment */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">Refined Assessment</h3>
          <p className="text-gray-800">
            {refined_analysis.refined_primary_assessment}
          </p>
        </div>

        {/* What This Means */}
        {refined_analysis.what_this_means && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold mb-2">What This Means</h3>
            <p className="text-gray-800">{refined_analysis.what_this_means}</p>
          </div>
        )}

        {/* Key Refinements */}
        {refined_analysis.key_refinements && refined_analysis.key_refinements.length > 0 && (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Key Findings from Follow-up</h3>
            <ul className="list-disc list-inside space-y-1">
              {refined_analysis.key_refinements.map((refinement: string, idx: number) => (
                <li key={idx} className="text-gray-700">{refinement}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Differential Diagnoses */}
        {refined_analysis.differential_diagnoses && refined_analysis.differential_diagnoses.length > 0 && (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Possible Conditions</h3>
            <div className="space-y-2">
              {refined_analysis.differential_diagnoses.map((dx: any, idx: number) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-start">
                    <span className="font-medium">{dx.condition}</span>
                    <span className="text-sm text-gray-600">{dx.probability}% likely</span>
                  </div>
                  {dx.supporting_evidence && (
                    <div className="mt-2 text-sm text-gray-600">
                      Evidence: {dx.supporting_evidence.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Steps */}
        {refined_analysis.next_steps && (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">Next Steps</h3>
            <div className="space-y-3">
              {refined_analysis.next_steps.immediate && (
                <div>
                  <p className="text-sm font-medium text-gray-600">Immediate:</p>
                  <p className="text-gray-800">{refined_analysis.next_steps.immediate}</p>
                </div>
              )}
              {refined_analysis.next_steps.short_term && (
                <div>
                  <p className="text-sm font-medium text-gray-600">Next 24-48 hours:</p>
                  <p className="text-gray-800">{refined_analysis.next_steps.short_term}</p>
                </div>
              )}
              {refined_analysis.next_steps.follow_up && (
                <div>
                  <p className="text-sm font-medium text-gray-600">Follow-up:</p>
                  <p className="text-gray-800">{refined_analysis.next_steps.follow_up}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Red Flags */}
        {refined_analysis.red_flags && refined_analysis.red_flags.length > 0 && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <h3 className="font-semibold text-red-800 mb-2">Warning Signs to Watch</h3>
            <ul className="list-disc list-inside space-y-1">
              {refined_analysis.red_flags.map((flag: string, idx: number) => (
                <li key={idx} className="text-red-700">{flag}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};