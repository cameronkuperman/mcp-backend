"""Core photo analysis constants and prompts"""
import os
from dotenv import load_dotenv

load_dotenv()

# Storage configuration
STORAGE_BUCKET = 'photo-uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']

# API Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Photo categorization prompt
PHOTO_CATEGORIZATION_PROMPT = """Analyze this medical photo and categorize it. 
Provide a JSON response with:
{
  "category": "medical_normal|medical_concerning|medical_urgent|non_medical",
  "confidence": 0.95,
  "subcategory": "specific_condition_type (e.g., 'dermatological_rash', 'orthopedic_fracture', 'vascular_varicose')",
  "quality_score": 85
}"""

# Enhanced photo analysis prompt with question detection
PHOTO_ANALYSIS_PROMPT = """You are an expert medical AI analyzing photos. 

FIRST STEP - QUESTION DETECTION:
Check if the user's description contains a question that needs answering.
Questions can be:
- Direct questions: "Is this serious?", "What is this?", "Should I see a doctor?", "Does this look normal?"
- Implied questions: "I'm worried about...", "I'm not sure if...", "Could this be...", "I wonder if..."
- Comparative questions: "Is this getting worse?", "Has this improved?", "Is it bigger than before?"
- Concern expressions: "This looks concerning", "I'm scared about this", "Is this dangerous?"

IF A QUESTION IS DETECTED:
- Set question_detected to true
- Provide a direct, specific answer in question_answer field addressing their concern
- The answer should be reassuring when appropriate but always medically accurate
- Continue with standard analysis

SECOND STEP - VISUAL ANALYSIS:
Focus on what's VISUALLY OBSERVABLE and MEASURABLE over time. Be specific with estimates even without measuring tools.
Analyze and provide:
1. PRIMARY ASSESSMENT: Most specific diagnosis possible based on visual evidence
2. CONFIDENCE: Your confidence level (0-100%)
3. KEY OBSERVATIONS: Most important visual findings that could change over time
4. TRACKABLE FEATURES: Identify the 3-5 most important things to monitor for THIS specific condition

For measurements, estimate using visual cues:
- Size: Compare to common references (fingernail ~10mm, penny ~20mm, etc)
- Colors: Describe precisely (e.g., "dark brown center, light brown periphery")
- Changes: What specific visual features would indicate improvement/worsening

Format your response as JSON:
{
  "question_detected": boolean,
  "question_answer": "Direct, specific answer to the user's question" (ONLY include this field if question_detected is true),
  "primary_assessment": "string",
  "confidence": number,
  "visual_observations": ["string"],
  "differential_diagnosis": ["string"],
  "recommendations": ["string"],
  "red_flags": ["string"],
  "trackable_metrics": [
    {
      "metric_name": "string",
      "current_value": number,
      "unit": "string",
      "suggested_tracking": "daily|weekly|monthly"
    }
  ],
  "follow_up_timing": "string",
  "urgency_level": "low|medium|high|urgent"
}"""

# Photo comparison prompt
PHOTO_COMPARISON_PROMPT = """You are analyzing progression by comparing NEW photos (shown first) to PREVIOUS photos (shown after separator).

IMPORTANT: The photos are ordered as:
1. FIRST SET: NEW/CURRENT photos - the most recent state
2. SEPARATOR: "--- COMPARED TO PREVIOUS/BASELINE PHOTOS BELOW ---"
3. SECOND SET: PREVIOUS/BASELINE photos - older comparison photos

Analyze the changes FROM the baseline (old) TO the current state (new).

Provide a detailed comparison focusing on:
1. OVERALL PROGRESSION: improving, stable, worsening, or mixed
2. SPECIFIC CHANGES: What exactly has changed between the photos
3. MEASUREMENTS: Estimate size/color/texture changes
4. CLINICAL SIGNIFICANCE: What do these changes mean medically
5. TRACKING METRICS: Update measurable values

Format as JSON:
{
  "progression_status": "improving|stable|worsening|mixed",
  "confidence": 0-100,
  "key_changes": [
    {
      "feature": "string",
      "previous_state": "string",
      "current_state": "string",
      "change_percentage": number,
      "clinical_significance": "string"
    }
  ],
  "overall_assessment": "string",
  "recommendations": ["string"],
  "next_comparison_timing": "string"
}"""

# Follow-up suggestion prompt
FOLLOW_UP_SUGGESTION_PROMPT = """Based on the analysis history and current condition status, provide intelligent follow-up recommendations.

Consider:
1. Progression trend (improving/worsening/stable)
2. Time since last photo
3. Condition severity
4. Optimal monitoring intervals

Provide recommendations for:
- Next photo timing
- What to watch for
- When to seek immediate care
- Tracking frequency adjustment

Format as structured JSON with specific, actionable guidance."""

# Report generation prompt
PHOTO_REPORT_PROMPT = """Generate a comprehensive medical report from these photo analyses.

Include:
1. SUMMARY: Overall condition assessment
2. PROGRESSION: Timeline of changes
3. KEY FINDINGS: Most important observations
4. METRICS: Trackable measurements over time
5. RECOMMENDATIONS: Next steps and monitoring plan

Use clear, professional medical language while remaining accessible to patients.
Format as a structured report with clear sections."""