"""Request models for all API endpoints"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Chat and Oracle Models
class ChatRequest(BaseModel):
    query: Optional[str] = None  # Support both query and message
    message: Optional[str] = None  # Frontend uses 'message'
    user_id: Optional[str] = None  # Make optional for anonymous
    conversation_id: str
    category: str = "health-scan"
    model: Optional[str] = None
    context: Optional[str] = None  # Frontend sends context

class GenerateSummaryRequest(BaseModel):
    conversation_id: Optional[str] = None
    quick_scan_id: Optional[str] = None
    user_id: str

# Health Scan Models
class QuickScanRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None

class DeepDiveStartRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None  # Will default to google/gemini-2.5-pro
    fallback_model: Optional[str] = None  # For retry support

class DeepDiveContinueRequest(BaseModel):
    session_id: str
    answer: str
    question_number: int
    fallback_model: Optional[str] = None  # For retry support

class DeepDiveCompleteRequest(BaseModel):
    session_id: str
    final_answer: Optional[str] = None
    fallback_model: Optional[str] = None  # For retry support

class DeepDiveThinkHarderRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    model: str = "x-ai/grok-4"  # Grok 4 for maximum reasoning in deep dive

class DeepDiveAskMoreRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    current_confidence: Optional[int] = None  # Frontend sends this
    target_confidence: int = 95
    confidence: Optional[int] = None  # Frontend alternate name
    target: Optional[int] = None  # Frontend alternate name
    max_questions: int = 5

class QuickScanThinkHarderRequest(BaseModel):
    scan_id: str
    user_id: Optional[str] = None
    model: str = "openai/o4-mini"  # Default to GPT-4 for enhanced analysis

class QuickScanO4MiniRequest(BaseModel):
    scan_id: str
    user_id: Optional[str] = None
    model: str = "openai/o4-mini"  # Regular o4-mini for balanced cost/performance

class QuickScanUltraThinkRequest(BaseModel):
    scan_id: Optional[str] = None  # For quick scans
    deep_dive_id: Optional[str] = None  # For deep dives
    user_id: Optional[str] = None
    model: str = "x-ai/grok-4"  # Grok 4 for maximum reasoning

class QuickScanAskMoreRequest(BaseModel):
    scan_id: str
    user_id: Optional[str] = None
    target_confidence: int = 90
    max_questions: int = 3  # Quick scan should have fewer questions

# Health Story Model
class HealthStoryRequest(BaseModel):
    user_id: str
    date_range: Optional[Dict[str, str]] = None  # {"start": "ISO date", "end": "ISO date"}
    include_data: Optional[Dict[str, bool]] = None  # Which data sources to include

# Report Generation Models
class ReportAnalyzeRequest(BaseModel):
    user_id: Optional[str] = None
    context: Dict[str, Any] = {}
    available_data: Optional[Dict[str, List[str]]] = None

class ComprehensiveReportRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    photo_session_ids: Optional[List[str]] = None

class UrgentTriageRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None

class PhotoProgressionRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None

class SymptomTimelineRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    symptom_focus: Optional[str] = None

class SpecialistReportRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    specialty: Optional[str] = None
    photo_session_ids: Optional[List[str]] = None

class AnnualSummaryRequest(BaseModel):
    analysis_id: str
    user_id: str  # Required for annual
    year: Optional[int] = None

class TimePeriodReportRequest(BaseModel):
    user_id: str
    include_wearables: Optional[bool] = False

# Doctor and Sharing Models
class DoctorNotesRequest(BaseModel):
    doctor_npi: str
    specialty: str
    notes: str
    sections_reviewed: List[str]
    diagnosis: Optional[str] = None
    plan_modifications: Optional[Dict[str, Any]] = None
    follow_up_instructions: Optional[str] = None

class ShareReportRequest(BaseModel):
    shared_by_npi: str
    recipient_npi: str
    access_level: str = "read_only"  # read_only, full_access
    expiration_days: int = 30
    notes: Optional[str] = None
    base_url: str

class RateReportRequest(BaseModel):
    doctor_npi: str
    usefulness_score: int  # 1-5
    accuracy_score: int    # 1-5
    time_saved: int       # minutes
    would_recommend: bool
    feedback: Optional[str] = None

# Tracking Models
class TrackingSuggestRequest(BaseModel):
    source_type: str  # 'quick_scan' or 'deep_dive'
    source_id: str
    user_id: str

class TrackingConfigureRequest(BaseModel):
    suggestion_id: str
    user_id: str
    metric_name: str  # User can edit
    y_axis_label: str  # User can edit
    show_on_homepage: bool = True

class TrackingDataPointRequest(BaseModel):
    configuration_id: str
    user_id: str
    value: float
    notes: Optional[str] = None
    recorded_at: Optional[str] = None  # ISO timestamp, defaults to now

# Photo Analysis Models
class PhotoCategorizeResponse(BaseModel):
    category: str
    confidence: float
    subcategory: Optional[str] = None
    session_context: Optional[Dict[str, Any]] = None

class PhotoUploadResponse(BaseModel):
    session_id: str
    uploaded_photos: List[Dict[str, Any]]
    requires_action: Optional[Dict[str, Any]] = None

class PhotoAnalysisRequest(BaseModel):
    session_id: str
    photo_ids: List[str]
    context: Optional[str] = None
    comparison_photo_ids: Optional[List[str]] = None
    temporary_analysis: bool = False

class PhotoAnalysisResponse(BaseModel):
    analysis_id: str
    analysis: Dict[str, Any]
    comparison: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None

class PhotoSessionResponse(BaseModel):
    id: str
    condition_name: str
    created_at: str
    last_photo_at: Optional[str] = None
    photo_count: int
    analysis_count: int
    is_sensitive: bool
    latest_summary: Optional[str] = None
    thumbnail_url: Optional[str] = None

class PhotoAnalysisReportRequest(BaseModel):
    user_id: str
    session_ids: List[str]
    include_visual_timeline: bool = True
    include_tracking_data: bool = True
    time_range_days: Optional[int] = None  # None means all time

# Health Analysis Models
class HealthAnalysisRequest(BaseModel):
    user_id: str
    week_of: Optional[str] = None
    include_predictions: bool = True
    include_patterns: bool = True
    
class RefreshAnalysisRequest(BaseModel):
    user_id: str
    include_predictions: bool = True
    include_patterns: bool = True
    include_strategies: bool = True

# Specialist Report Models
class SpecialtyTriageRequest(BaseModel):
    user_id: str
    quick_scan_ids: Optional[List[str]] = None
    deep_dive_ids: Optional[List[str]] = None
    primary_concern: Optional[str] = None
    symptoms: Optional[List[str]] = None
    urgency: Optional[str] = None

# General Assessment Models
class FlashAssessmentRequest(BaseModel):
    user_query: str
    user_id: Optional[str] = None

class GeneralAssessmentRequest(BaseModel):
    category: str  # energy, mental, sick, medication, multiple, unsure, physical
    form_data: Dict[str, Any]
    user_id: Optional[str] = None

class GeneralDeepDiveStartRequest(BaseModel):
    category: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None
    fallback_model: Optional[str] = None

class GeneralDeepDiveContinueRequest(BaseModel):
    session_id: str
    answer: str
    question_number: int
    fallback_model: Optional[str] = None

class GeneralDeepDiveCompleteRequest(BaseModel):
    session_id: str
    final_answer: Optional[str] = None
    fallback_model: Optional[str] = None