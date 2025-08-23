"""
Payload validation middleware for FastAPI
Handles pre-processing validation before endpoints
"""
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json
from typing import Callable

from app.services.payload_validator import PayloadValidator
from app.models.shotstack_models import ValidationErrorResponse
from app.config import settings

logger = logging.getLogger(__name__)

class PayloadValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate render payloads before processing"""
    
    def __init__(self, app, enabled: bool = True, sanitize: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.sanitize = sanitize
        
        # Endpoints that should have validation
        self.validation_endpoints = {
            "/api/v1/render": "single",
            "/api/v1/batch-render": "batch_structured", 
            "/api/v1/batch-render-array": "batch_array"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware logic"""
        
        # Skip validation if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Check if this endpoint needs validation
        path = request.url.path
        validation_type = self.validation_endpoints.get(path)
        
        if not validation_type or request.method != "POST":
            return await call_next(request)
        
        # Skip validation for certain conditions
        if await self._should_skip_validation(request):
            return await call_next(request)
        
        try:
            # Get request body
            body = await request.body()
            if not body:
                return await call_next(request)
            
            # Parse JSON
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in request to {path}: {str(e)}")
                return self._create_validation_error_response(
                    "Invalid JSON format",
                    f"Request body contains invalid JSON: {str(e)}", 
                    "Ensure your request body is valid JSON"
                )
            
            # Validate based on endpoint type
            validation_result = await self._validate_payload(payload, validation_type)
            
            if isinstance(validation_result, ValidationErrorResponse):
                logger.info(f"Payload validation failed for {path}: {validation_result.total_errors} errors")
                return JSONResponse(
                    status_code=400,
                    content=validation_result.dict()
                )
            
            # Validation passed - modify request body with sanitized data
            if self.sanitize and hasattr(validation_result, 'dict'):
                # For single renders
                sanitized_json = json.dumps(validation_result.dict())
            elif isinstance(validation_result, list):
                # For batch arrays
                sanitized_json = json.dumps([item.dict() for item in validation_result])
            else:
                sanitized_json = body.decode('utf-8')
            
            # Create new request with sanitized body
            request._body = sanitized_json.encode('utf-8')
            
            logger.debug(f"Payload validation passed for {path}")
            
        except Exception as e:
            logger.error(f"Validation middleware error for {path}: {str(e)}")
            # Continue without validation on unexpected errors
            pass
        
        return await call_next(request)
    
    async def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request"""
        
        # Skip for health checks or internal requests
        if hasattr(request.state, 'skip_validation'):
            return request.state.skip_validation
        
        # Skip if validation is disabled via header (for testing)
        if request.headers.get('X-Skip-Validation') == 'true':
            logger.warning("Validation skipped via X-Skip-Validation header")
            return True
        
        return False
    
    async def _validate_payload(self, payload, validation_type: str):
        """Validate payload based on type"""
        
        try:
            if validation_type == "single":
                return PayloadValidator.validate_single_render(payload, self.sanitize)
            
            elif validation_type == "batch_structured":
                return PayloadValidator.validate_batch_render(payload, self.sanitize)
            
            elif validation_type == "batch_array":
                if not isinstance(payload, list):
                    return self._create_validation_error_response(
                        "Invalid batch array format",
                        "Expected an array of render objects",
                        "Wrap your render objects in an array: [{ timeline: {...}, output: {...} }]"
                    )
                return PayloadValidator.validate_batch_array(payload, self.sanitize)
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return self._create_validation_error_response(
                "Validation system error",
                str(e),
                "Please try again or contact support if the issue persists"
            )
    
    def _create_validation_error_response(self, error: str, message: str, suggestion: str = None) -> ValidationErrorResponse:
        """Create a validation error response"""
        from app.models.shotstack_models import ValidationError as CustomValidationError
        
        return ValidationErrorResponse(
            error=error,
            validation_errors=[CustomValidationError(
                field="request",
                value="N/A",
                error_type="request_error",
                message=message,
                suggestion=suggestion
            )],
            total_errors=1
        )

# ============================================================================
# CONFIGURATION FUNCTIONS
# ============================================================================

def create_validation_middleware(enabled: bool = None, sanitize: bool = None):
    """Factory function to create validation middleware with config"""
    
    if enabled is None:
        enabled = getattr(settings, 'VALIDATION_ENABLED', True)
    
    if sanitize is None:
        sanitize = getattr(settings, 'SANITIZATION_ENABLED', True)
    
    logger.info(f"Creating payload validation middleware: enabled={enabled}, sanitize={sanitize}")
    
    def middleware_factory(app):
        return PayloadValidationMiddleware(app, enabled=enabled, sanitize=sanitize)
    
    return middleware_factory

# ============================================================================
# UTILITY FUNCTIONS FOR TESTING
# ============================================================================

async def validate_payload_direct(payload, validation_type: str = "single"):
    """Direct validation function for testing/debugging"""
    
    if validation_type == "single":
        return PayloadValidator.validate_single_render(payload)
    elif validation_type == "batch_structured":
        return PayloadValidator.validate_batch_render(payload) 
    elif validation_type == "batch_array":
        return PayloadValidator.validate_batch_array(payload)
    else:
        raise ValueError(f"Unknown validation type: {validation_type}")

async def test_payload_sanitization(payload):
    """Test sanitization without full validation"""
    from app.services.payload_validator import PayloadSanitizer
    return PayloadSanitizer.sanitize_payload(payload)