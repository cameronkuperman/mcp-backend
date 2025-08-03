"""Enhanced photo analysis with comprehensive error handling and debugging"""
import traceback
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

# Import settings for debug flag
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

def debug_log(message: str, data: Any = None):
    """Enhanced debug logging"""
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] {message}")
    if data:
        print(f"  Data: {json.dumps(data, indent=2, default=str)[:1000]}")

def wrap_endpoint_with_error_handling(func):
    """Decorator to add comprehensive error handling to endpoints"""
    async def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        endpoint_name = func.__name__
        
        try:
            debug_log(f"Starting endpoint: {endpoint_name}", {
                "args": str(args)[:200],
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
            })
            
            result = await func(*args, **kwargs)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            debug_log(f"Endpoint completed: {endpoint_name}", {
                "duration_seconds": duration,
                "success": True
            })
            
            return result
            
        except HTTPException as e:
            # Re-raise HTTP exceptions as they already have proper error codes
            duration = (datetime.utcnow() - start_time).total_seconds()
            debug_log(f"HTTP Exception in {endpoint_name}", {
                "status_code": e.status_code,
                "detail": e.detail,
                "duration_seconds": duration
            })
            raise
            
        except httpx.HTTPStatusError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_detail = {
                "error": "external_service_error",
                "service": "OpenRouter",
                "status_code": e.response.status_code,
                "duration_seconds": duration
            }
            
            if e.response.status_code == 429:
                debug_log(f"Rate limit hit in {endpoint_name}", error_detail)
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "rate_limit",
                        "message": "AI service is temporarily busy. Please try again in 30 seconds.",
                        "retry_after": 30
                    }
                )
            elif e.response.status_code >= 500:
                debug_log(f"OpenRouter server error in {endpoint_name}", error_detail)
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "ai_service_unavailable",
                        "message": "AI service is temporarily unavailable. Please try again."
                    }
                )
            else:
                debug_log(f"OpenRouter client error in {endpoint_name}", error_detail)
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "ai_service_error",
                        "message": f"AI service error: {e.response.status_code}",
                        "debug": str(e) if DEBUG else None
                    }
                )
                
        except json.JSONDecodeError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            debug_log(f"JSON decode error in {endpoint_name}", {
                "error_msg": str(e),
                "line": e.lineno,
                "column": e.colno,
                "duration_seconds": duration,
                "content_preview": str(e.doc)[:500] if hasattr(e, 'doc') else None
            })
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "json_parse_error",
                    "message": "Failed to parse AI response. The AI provided an invalid format.",
                    "debug": {
                        "error": str(e),
                        "preview": str(e.doc)[:200] if hasattr(e, 'doc') and DEBUG else None
                    } if DEBUG else None
                }
            )
            
        except AttributeError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            debug_log(f"AttributeError in {endpoint_name}", {
                "error": str(e),
                "duration_seconds": duration,
                "traceback": traceback.format_exc() if DEBUG else None
            })
            
            # Check if it's the common dict/object confusion
            if "'dict' object has no attribute" in str(e):
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "data_access_error",
                        "message": "Internal error processing response data.",
                        "debug": str(e) if DEBUG else None
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "attribute_error",
                        "message": "Internal error accessing data.",
                        "debug": str(e) if DEBUG else None
                    }
                )
                
        except ValueError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            debug_log(f"ValueError in {endpoint_name}", {
                "error": str(e),
                "duration_seconds": duration
            })
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "message": str(e)
                }
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_type = type(e).__name__
            error_msg = str(e)
            
            debug_log(f"Unexpected {error_type} in {endpoint_name}", {
                "error_type": error_type,
                "error_msg": error_msg,
                "duration_seconds": duration,
                "traceback": traceback.format_exc()
            })
            
            # Log full traceback for debugging
            print(f"\nFull traceback for {endpoint_name}:")
            traceback.print_exc()
            
            # Return user-friendly error
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_error",
                    "message": "An unexpected error occurred. Our team has been notified.",
                    "request_id": f"{endpoint_name}_{start_time.timestamp()}",
                    "debug": {
                        "error_type": error_type,
                        "error_msg": error_msg[:200]
                    } if DEBUG else None
                }
            )
    
    # Preserve function metadata
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def validate_ai_response(response: Any, expected_fields: List[str]) -> Dict[str, Any]:
    """Validate AI response has expected structure"""
    if not isinstance(response, dict):
        raise ValueError(f"Expected dict response, got {type(response).__name__}")
    
    missing_fields = [field for field in expected_fields if field not in response]
    if missing_fields:
        debug_log("AI response missing expected fields", {
            "missing": missing_fields,
            "received_fields": list(response.keys()),
            "response_preview": str(response)[:500]
        })
        
        # Try to provide sensible defaults
        for field in missing_fields:
            if field in ['confidence', 'confidence_score']:
                response[field] = 50
            elif field in ['recommendations', 'red_flags', 'visual_observations']:
                response[field] = []
            elif field in ['primary_assessment', 'summary']:
                response[field] = "Analysis in progress"
            else:
                response[field] = {}
    
    return response


# Enhanced JSON extraction specifically for AI responses
def extract_json_from_ai_response(content: str) -> Optional[Dict]:
    """Extract JSON from AI response with enhanced error handling"""
    debug_log("Attempting to extract JSON from AI response", {
        "content_length": len(content),
        "content_preview": content[:200]
    })
    
    # Try the standard extraction first
    from utils.json_parser import extract_json_from_response
    try:
        result = extract_json_from_response(content)
        if result:
            debug_log("Successfully extracted JSON using standard parser")
            return result
    except Exception as e:
        debug_log(f"Standard JSON extraction failed: {e}")
    
    # Additional fallback strategies for AI responses
    
    # Strategy: Remove common AI prefixes/suffixes
    cleaned = content.strip()
    
    # Remove common AI response patterns
    patterns_to_remove = [
        r'^Here\'s the JSON response:?\s*',
        r'^Here is the analysis:?\s*',
        r'^```json\s*',
        r'\s*```$',
        r'^The analysis results?:?\s*',
    ]
    
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Try parsing the cleaned content
    try:
        result = json.loads(cleaned)
        debug_log("Successfully parsed JSON after cleaning")
        return result
    except:
        pass
    
    # Strategy: Extract using regex for complete JSON objects
    json_patterns = [
        r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # Nested objects
        r'\{[^{}]+\}',  # Simple objects
        r'\[[^\[\]]*\[[^\[\]]*\][^\[\]]*\]',  # Nested arrays
        r'\[[^\[\]]+\]',  # Simple arrays
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            try:
                result = json.loads(match)
                if isinstance(result, (dict, list)):
                    debug_log(f"Successfully extracted JSON using pattern: {pattern[:30]}...")
                    return result
            except:
                continue
    
    debug_log("All JSON extraction strategies failed", {
        "content_sample": content[:500]
    })
    
    return None