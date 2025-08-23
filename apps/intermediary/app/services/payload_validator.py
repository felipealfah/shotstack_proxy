"""
Payload validation and sanitization service
Handles pre-processing of payloads before Shotstack API calls
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import ValidationError
import logging
import json
import re

from app.models.shotstack_models import (
    ShotstackRenderRequest, 
    BatchRenderRequest, 
    BatchRenderArrayRequest,
    ValidationError as CustomValidationError,
    ValidationErrorResponse
)
from app.services.timeline_parser import TimelineParser

logger = logging.getLogger(__name__)

class PayloadSanitizer:
    """Handles automatic sanitization of common payload issues"""
    
    @staticmethod
    def sanitize_null_strings(data: Any) -> Any:
        """Convert string 'null' to None recursively"""
        if isinstance(data, dict):
            return {k: PayloadSanitizer.sanitize_null_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [PayloadSanitizer.sanitize_null_strings(item) for item in data]
        elif isinstance(data, str) and data.strip().lower() == 'null':
            return None
        return data
    
    @staticmethod 
    def clean_numeric_strings(data: Any) -> Any:
        """Clean numeric strings with trailing spaces"""
        if isinstance(data, dict):
            return {k: PayloadSanitizer.clean_numeric_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [PayloadSanitizer.clean_numeric_strings(item) for item in data]
        elif isinstance(data, str):
            # Check if it looks like a number with spaces
            stripped = data.strip()
            if re.match(r'^-?\d*\.?\d+$', stripped):
                try:
                    # If it's a valid number, clean it
                    return float(stripped) if '.' in stripped else int(stripped)
                except (ValueError, TypeError):
                    pass
            return data
        return data
    
    @staticmethod
    def normalize_boolean_strings(data: Any) -> Any:
        """Convert string booleans to actual booleans"""
        if isinstance(data, dict):
            return {k: PayloadSanitizer.normalize_boolean_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [PayloadSanitizer.normalize_boolean_strings(item) for item in data]
        elif isinstance(data, str):
            lower_val = data.strip().lower()
            if lower_val == 'true':
                return True
            elif lower_val == 'false':
                return False
            return data
        return data
    
    @staticmethod
    def convert_legacy_size_format(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy width/height to size object if needed"""
        if isinstance(data, dict) and 'output' in data:
            output = data['output']
            if isinstance(output, dict):
                # If both width/height and size exist, prefer size
                if 'size' not in output and ('width' in output or 'height' in output):
                    size_obj = {}
                    if 'width' in output:
                        size_obj['width'] = output.pop('width')
                    if 'height' in output:
                        size_obj['height'] = output.pop('height')
                    
                    if size_obj:
                        output['size'] = size_obj
                        logger.info(f"Converted legacy width/height to size object: {size_obj}")
        
        return data
    
    @classmethod
    def sanitize_payload(cls, payload: Any) -> Any:
        """Apply all sanitization steps"""
        logger.debug("Starting payload sanitization")
        
        # Step 1: Convert null strings
        payload = cls.sanitize_null_strings(payload)
        
        # Step 2: Clean numeric strings  
        payload = cls.clean_numeric_strings(payload)
        
        # Step 3: Normalize booleans
        payload = cls.normalize_boolean_strings(payload)
        
        # Step 4: Convert legacy formats
        if isinstance(payload, dict):
            payload = cls.convert_legacy_size_format(payload)
        elif isinstance(payload, list):
            payload = [cls.convert_legacy_size_format(item) if isinstance(item, dict) else item for item in payload]
        
        logger.debug("Payload sanitization completed")
        return payload

class TimelineValidator:
    """Additional timeline-specific validation"""
    
    @staticmethod
    def validate_timeline_duration(timeline: Dict[str, Any]) -> Optional[str]:
        """Test if timeline can be parsed by TimelineParser"""
        try:
            duration = TimelineParser.extract_total_duration(timeline)
            if duration <= 0:
                return "Timeline duration must be greater than 0 seconds"
            if duration > 3600:  # 1 hour limit
                return f"Timeline duration ({duration}s) exceeds maximum of 3600 seconds (1 hour)"
            return None  # No error
        except Exception as e:
            return f"Timeline structure error: {str(e)}"
    
    @staticmethod
    def validate_asset_consistency(timeline: Dict[str, Any]) -> List[str]:
        """Validate asset consistency within timeline"""
        errors = []
        
        try:
            tracks = timeline.get('tracks', [])
            for track_idx, track in enumerate(tracks):
                clips = track.get('clips', [])
                for clip_idx, clip in enumerate(clips):
                    asset = clip.get('asset', {})
                    asset_type = asset.get('type')
                    
                    # Check required fields per asset type
                    location = f"timeline.tracks[{track_idx}].clips[{clip_idx}]"
                    
                    if asset_type in ['video', 'audio', 'image']:
                        if not asset.get('src'):
                            errors.append(f"{location}: {asset_type} asset missing required 'src' field")
                    
                    elif asset_type in ['title', 'caption']:
                        if not asset.get('text'):
                            errors.append(f"{location}: {asset_type} asset missing required 'text' field")
                    
                    elif asset_type == 'html':
                        if not asset.get('html'):
                            errors.append(f"{location}: html asset missing required 'html' field")
                    
                    # Validate length compatibility
                    clip_length = clip.get('length')
                    if clip_length in ['auto', 'end'] and asset_type in ['title', 'caption', 'html']:
                        errors.append(f"{location}: Smart clip length '{clip_length}' not supported for {asset_type} assets")
        
        except Exception as e:
            errors.append(f"Timeline structure validation failed: {str(e)}")
        
        return errors

class PayloadValidator:
    """Main validation orchestrator"""
    
    @staticmethod
    def format_pydantic_error(error: ValidationError) -> List[CustomValidationError]:
        """Convert Pydantic ValidationError to our custom format"""
        formatted_errors = []
        
        for error_detail in error.errors():
            field_path = '.'.join(str(part) for part in error_detail['loc'])
            error_type = error_detail['type']
            message = error_detail['msg']
            
            # Try to get the problematic value
            try:
                input_value = error_detail.get('input', 'Unknown')
            except:
                input_value = 'Unknown'
            
            # Generate helpful suggestions
            suggestion = PayloadValidator._generate_suggestion(error_type, field_path, message)
            
            formatted_errors.append(CustomValidationError(
                field=field_path,
                value=input_value,
                error_type=error_type,
                message=message,
                suggestion=suggestion
            ))
        
        return formatted_errors
    
    @staticmethod
    def _generate_suggestion(error_type: str, field_path: str, message: str) -> Optional[str]:
        """Generate helpful suggestions based on error type"""
        suggestions = {
            'value_error': {
                'start time cannot be negative': "Use 0 or a positive number for start time",
                'length must be positive': "Use a positive number, 'auto', or 'end' for length",
                'invalid start time format': "Use a numeric value like 0, 1.5, or 10",
                'length cannot be string': "Remove quotes around null or use a number",
                'smart clip length': "Use numeric length for title/caption assets, or switch to video/audio asset"
            },
            'type_error': {
                'str expected': "Provide a text string value",
                'float expected': "Provide a numeric value like 1.5 or 10",
                'url expected': "Provide a valid HTTP/HTTPS URL"
            },
            'missing': "This field is required - please provide a value"
        }
        
        # Check for specific error patterns
        message_lower = message.lower()
        if error_type in suggestions:
            error_suggestions = suggestions[error_type]
            if isinstance(error_suggestions, dict):
                for pattern, suggestion in error_suggestions.items():
                    if pattern in message_lower:
                        return suggestion
            else:
                return error_suggestions
        
        # Field-specific suggestions
        if 'src' in field_path:
            return "Provide a valid HTTP/HTTPS URL pointing to your media file"
        elif 'text' in field_path:
            return "Provide the text content you want to display"
        elif 'start' in field_path:
            return "Use 0 for the beginning, or specify when this clip should start in seconds"
        elif 'length' in field_path:
            return "Specify how long this clip should play in seconds, or use 'auto' for video/audio"
        
        return None
    
    @classmethod
    def validate_single_render(cls, payload: Dict[str, Any], sanitize: bool = True) -> Union[ShotstackRenderRequest, ValidationErrorResponse]:
        """Validate a single render request"""
        try:
            # Step 1: Sanitize if enabled
            if sanitize:
                payload = PayloadSanitizer.sanitize_payload(payload)
            
            # Step 2: Additional timeline validation
            if 'timeline' in payload:
                timeline_error = TimelineValidator.validate_timeline_duration(payload['timeline'])
                if timeline_error:
                    return ValidationErrorResponse(
                        error="Timeline validation failed",
                        validation_errors=[CustomValidationError(
                            field="timeline",
                            value=payload['timeline'],
                            error_type="timeline_error", 
                            message=timeline_error,
                            suggestion="Check your clip timings and ensure total duration is reasonable"
                        )],
                        total_errors=1
                    )
                
                # Asset consistency validation
                asset_errors = TimelineValidator.validate_asset_consistency(payload['timeline'])
                if asset_errors:
                    formatted_errors = []
                    for i, error_msg in enumerate(asset_errors):
                        formatted_errors.append(CustomValidationError(
                            field=f"timeline.consistency_{i}",
                            value="Multiple fields",
                            error_type="asset_consistency",
                            message=error_msg,
                            suggestion="Ensure all required fields are provided for each asset type"
                        ))
                    
                    return ValidationErrorResponse(
                        error="Asset validation failed",
                        validation_errors=formatted_errors,
                        total_errors=len(formatted_errors)
                    )
            
            # Step 3: Pydantic validation
            validated = ShotstackRenderRequest(**payload)
            return validated
            
        except ValidationError as e:
            logger.warning(f"Payload validation failed: {str(e)}")
            formatted_errors = cls.format_pydantic_error(e)
            
            return ValidationErrorResponse(
                error=f"Payload validation failed - {len(formatted_errors)} issue{'s' if len(formatted_errors) != 1 else ''} found",
                validation_errors=formatted_errors,
                total_errors=len(formatted_errors)
            )
        
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
            return ValidationErrorResponse(
                error="Unexpected validation error",
                validation_errors=[CustomValidationError(
                    field="payload",
                    value=payload,
                    error_type="unexpected_error",
                    message=str(e),
                    suggestion="Check payload format and try again"
                )],
                total_errors=1
            )
    
    @classmethod
    def validate_batch_render(cls, payload: Dict[str, Any], sanitize: bool = True) -> Union[BatchRenderRequest, ValidationErrorResponse]:
        """Validate batch render request (structured format)"""
        try:
            if sanitize:
                payload = PayloadSanitizer.sanitize_payload(payload)
            
            validated = BatchRenderRequest(**payload)
            return validated
            
        except ValidationError as e:
            logger.warning(f"Batch validation failed: {str(e)}")
            formatted_errors = cls.format_pydantic_error(e)
            
            return ValidationErrorResponse(
                error=f"Batch validation failed - {len(formatted_errors)} issue{'s' if len(formatted_errors) != 1 else ''} found",
                validation_errors=formatted_errors,
                total_errors=len(formatted_errors)
            )
    
    @classmethod  
    def validate_batch_array(cls, payload: List[Dict[str, Any]], sanitize: bool = True) -> Union[List[ShotstackRenderRequest], ValidationErrorResponse]:
        """Validate batch array format (N8N style)"""
        try:
            if sanitize:
                payload = PayloadSanitizer.sanitize_payload(payload)
            
            # Validate each render individually to get specific errors
            validation_errors = []
            validated_renders = []
            
            for i, render_payload in enumerate(payload):
                result = cls.validate_single_render(render_payload, sanitize=False)  # Already sanitized
                if isinstance(result, ValidationErrorResponse):
                    # Add index to field paths
                    for error in result.validation_errors:
                        error.field = f"renders[{i}].{error.field}"
                        validation_errors.append(error)
                else:
                    validated_renders.append(result)
            
            if validation_errors:
                return ValidationErrorResponse(
                    error=f"Batch array validation failed - {len(validation_errors)} issue{'s' if len(validation_errors) != 1 else ''} found",
                    validation_errors=validation_errors,
                    total_errors=len(validation_errors)
                )
            
            return validated_renders
            
        except Exception as e:
            logger.error(f"Unexpected batch array validation error: {str(e)}")
            return ValidationErrorResponse(
                error="Unexpected batch array validation error",
                validation_errors=[CustomValidationError(
                    field="batch_array",
                    value=payload,
                    error_type="unexpected_error",
                    message=str(e),
                    suggestion="Check batch array format and try again"
                )],
                total_errors=1
            )