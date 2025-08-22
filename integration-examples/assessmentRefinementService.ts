// Assessment Refinement Service for Next.js Frontend
// Place this file in your Next.js app at: services/assessmentRefinementService.ts

interface Answer {
  question: string;
  answer: string;
}

interface RefinementRequest {
  assessment_id: string;
  answers: Answer[];
  user_id?: string;
}

interface RefinementResponse {
  refinement_id: string;
  assessment_id: string;
  refined_analysis: {
    refined_primary_assessment: string;
    confidence: number;
    diagnostic_certainty: 'provisional' | 'probable' | 'definitive';
    differential_diagnoses: Array<{
      condition: string;
      probability: number;
      supporting_evidence: string[];
    }>;
    key_refinements: string[];
    updated_recommendations: string[];
    immediate_actions: string[];
    red_flags: string[];
    urgency: 'low' | 'medium' | 'high' | 'emergency';
    next_steps: {
      immediate: string;
      short_term: string;
      follow_up: string;
    };
    severity_level: 'low' | 'moderate' | 'high' | 'urgent';
    confidence_level: 'low' | 'medium' | 'high';
    what_this_means: string;
    tracking_metrics: string[];
    follow_up_timeline: {
      check_progress: string;
      see_doctor_if: string;
    };
  };
  confidence_improvement: number;
  original_confidence: number;
  refined_confidence: number;
  diagnostic_certainty: string;
  category: string;
  status: string;
}

interface GeneralAssessmentResponse {
  assessment_id: string;
  analysis: {
    primary_assessment: string;
    confidence: number;
    key_findings: string[];
    possible_causes: Array<{
      condition: string;
      likelihood: number;
      explanation: string;
    }>;
    recommendations: string[];
    urgency: string;
    follow_up_questions: string[];
    severity_level: string;
    confidence_level: string;
    what_this_means: string;
    immediate_actions: string[];
    red_flags: string[];
    tracking_metrics: string[];
    follow_up_timeline: {
      check_progress: string;
      see_doctor_if: string;
    };
  };
}

class AssessmentRefinementService {
  private apiUrl: string;

  constructor(apiUrl?: string) {
    this.apiUrl = apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  /**
   * Refine an existing general assessment with follow-up answers
   */
  async refineAssessment(request: RefinementRequest): Promise<RefinementResponse> {
    const response = await fetch(`${this.apiUrl}/api/general-assessment/refine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to refine assessment: ${error}`);
    }

    return response.json();
  }

  /**
   * Get the original assessment to extract follow-up questions
   */
  async getAssessment(assessmentId: string): Promise<GeneralAssessmentResponse | null> {
    // This would typically fetch from your database or API
    // For now, returning null as a placeholder
    // In production, you'd fetch this from your Supabase database or API
    console.log('Fetching assessment:', assessmentId);
    return null;
  }

  /**
   * Check if an assessment has follow-up questions available
   */
  hasFollowUpQuestions(assessment: GeneralAssessmentResponse): boolean {
    return !!(
      assessment?.analysis?.follow_up_questions &&
      assessment.analysis.follow_up_questions.length > 0
    );
  }

  /**
   * Calculate expected confidence improvement
   */
  calculateExpectedImprovement(originalConfidence: number): number {
    // Generally expect 15-30% improvement, capped at 95%
    const improvement = Math.min(15, 95 - originalConfidence);
    return Math.max(improvement, 5); // At least 5% improvement
  }

  /**
   * Format refinement results for display
   */
  formatRefinementResults(response: RefinementResponse) {
    const {
      refined_analysis,
      confidence_improvement,
      original_confidence,
      refined_confidence,
      diagnostic_certainty,
    } = response;

    return {
      summary: {
        title: 'Assessment Refined Successfully',
        confidenceGain: `+${confidence_improvement}%`,
        newConfidence: `${refined_confidence}%`,
        certainty: diagnostic_certainty,
      },
      diagnosis: {
        primary: refined_analysis.refined_primary_assessment,
        differential: refined_analysis.differential_diagnoses,
        keyFindings: refined_analysis.key_refinements,
      },
      recommendations: {
        immediate: refined_analysis.immediate_actions,
        updated: refined_analysis.updated_recommendations,
        nextSteps: refined_analysis.next_steps,
      },
      warnings: {
        redFlags: refined_analysis.red_flags,
        urgency: refined_analysis.urgency,
        trackingMetrics: refined_analysis.tracking_metrics,
      },
      explanation: refined_analysis.what_this_means,
    };
  }

  /**
   * Determine if refinement is worth pursuing based on confidence
   */
  shouldRefine(originalConfidence: number): {
    shouldRefine: boolean;
    reason: string;
  } {
    if (originalConfidence < 60) {
      return {
        shouldRefine: true,
        reason: 'Low confidence - refinement strongly recommended',
      };
    } else if (originalConfidence < 80) {
      return {
        shouldRefine: true,
        reason: 'Moderate confidence - refinement could provide clarity',
      };
    } else {
      return {
        shouldRefine: false,
        reason: 'High confidence - refinement optional',
      };
    }
  }
}

// Export singleton instance
export const assessmentRefinementService = new AssessmentRefinementService();

// Export class for custom instantiation
export { AssessmentRefinementService };

// Export types
export type {
  Answer,
  RefinementRequest,
  RefinementResponse,
  GeneralAssessmentResponse,
};