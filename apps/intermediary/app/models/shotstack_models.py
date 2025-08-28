"""
Strict Pydantic models for Shotstack API validation
Replaces permissive Dict[str, Any] with specific validation models
"""
from typing import Optional, Union, List, Literal, Any, Dict
from pydantic import BaseModel, validator, HttpUrl, Field
from datetime import datetime

# ============================================================================
# ASSET MODELS - Specific validation for each asset type
# ============================================================================

class VideoAsset(BaseModel):
    """Video asset with strict validation"""
    type: Literal["video"] = "video"
    src: HttpUrl  # Required for video assets
    trim: Optional[float] = None
    volume: Optional[float] = Field(None, ge=0.0, le=1.0)  # 0-100%
    crop: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow additional Shotstack properties

class TitleAsset(BaseModel):
    """Title asset with text validation"""
    type: Literal["title"] = "title"
    text: str = Field(..., min_length=1, max_length=1000)  # Required, reasonable limits
    style: Optional[str] = "minimal"
    size: Optional[str] = None
    color: Optional[str] = None
    background: Optional[str] = None
    
    class Config:
        extra = "allow"

class AudioAsset(BaseModel):
    """Audio asset with strict validation"""
    type: Literal["audio"] = "audio" 
    src: HttpUrl  # Required for audio assets
    trim: Optional[float] = None
    volume: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    class Config:
        extra = "allow"

class ImageAsset(BaseModel):
    """Image asset with validation"""
    type: Literal["image"] = "image"
    src: HttpUrl  # Required for image assets
    crop: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class CaptionAsset(BaseModel):
    """Caption asset with validation - supports both text and automatic transcription"""
    type: Literal["caption"] = "caption"
    text: Optional[str] = Field(None, min_length=1)  # Optional when using src with alias
    src: Optional[str] = None  # For alias:// references (automatic transcription)
    style: Optional[str] = None
    font: Optional[Dict[str, Any]] = None
    stroke: Optional[Dict[str, Any]] = None
    
    @validator('text')
    def validate_text_or_src(cls, v, values):
        """Either text or src (with alias) must be provided"""
        src = values.get('src', '')
        if not v and not (src and src.startswith('alias://')):
            raise ValueError('Either text field or src with alias:// must be provided for caption')
        return v
    
    class Config:
        extra = "allow"

class LumaAsset(BaseModel):
    """Luma (transition) asset"""
    type: Literal["luma"] = "luma"
    src: HttpUrl
    
    class Config:
        extra = "allow"

class HtmlAsset(BaseModel):
    """HTML asset for custom content"""
    type: Literal["html"] = "html"
    html: str = Field(..., min_length=1)
    css: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    
    class Config:
        extra = "allow"

# Union of all asset types
AssetType = Union[
    VideoAsset, 
    TitleAsset, 
    AudioAsset, 
    ImageAsset, 
    CaptionAsset, 
    LumaAsset,
    HtmlAsset
]

# ============================================================================
# CLIP MODEL - With smart clips validation
# ============================================================================

class ClipModel(BaseModel):
    """Clip with comprehensive validation"""
    asset: AssetType
    start: Union[float, int] = Field(..., ge=0)  # Must be >= 0
    length: Union[float, int, Literal["auto", "end"]]
    
    @validator('start', pre=True)
    def validate_start(cls, v):
        """Convert string numbers to float, validate positive"""
        if isinstance(v, str):
            try:
                v_cleaned = v.strip()
                result = float(v_cleaned)
                if result < 0:
                    raise ValueError(f"Start time cannot be negative: {result}")
                return result
            except ValueError:
                if v.strip() == '':
                    raise ValueError("Start time cannot be empty")
                raise ValueError(f"Invalid start time format: '{v}'. Must be a number >= 0")
        return v
    
    @validator('length', pre=True)
    def validate_length(cls, v, values):
        """Validate length field with smart clips support"""
        # Handle string values
        if isinstance(v, str):
            v_cleaned = v.strip()
            
            # Handle "null" string
            if v_cleaned.lower() == "null":
                raise ValueError("Length cannot be string 'null'. Use null (without quotes) or a numeric value")
            
            # Handle smart clips
            if v_cleaned in ["auto", "end"]:
                # Validate that smart clips are used with appropriate assets
                asset = values.get('asset')
                if asset and hasattr(asset, 'type'):
                    # Special handling for caption with alias (automatic transcription)
                    if asset.type == 'caption' and v_cleaned == 'end':
                        # Allow 'end' length for caption with alias (automatic transcription)
                        if hasattr(asset, 'src') and asset.src and asset.src.startswith('alias://'):
                            return v_cleaned
                        else:
                            raise ValueError(f"Smart clip length 'end' for caption requires 'src' with alias:// reference")
                    elif asset.type in ['title', 'html']:
                        raise ValueError(f"Smart clip length '{v_cleaned}' is not supported for {asset.type} assets. Use a numeric value instead")
                    elif asset.type == 'caption' and v_cleaned == 'auto':
                        # Auto is still not supported for caption
                        raise ValueError(f"Smart clip length 'auto' is not supported for caption assets. Use 'end' with alias or numeric value")
                    elif asset.type in ['video', 'audio'] and not hasattr(asset, 'src'):
                        raise ValueError(f"Smart clip length '{v_cleaned}' requires a valid 'src' URL for {asset.type} assets")
                return v_cleaned
            
            # Try to convert to number
            try:
                result = float(v_cleaned)
                if result <= 0:
                    raise ValueError(f"Length must be positive: {result}")
                return result
            except ValueError:
                raise ValueError(f"Invalid length format: '{v}'. Use a number > 0, 'auto', or 'end'")
        
        # Handle numeric values
        if isinstance(v, (int, float)):
            if v <= 0:
                raise ValueError(f"Length must be positive: {v}")
            return v
            
        return v
    
    class Config:
        extra = "allow"

# ============================================================================
# TRACK MODEL
# ============================================================================

class TrackModel(BaseModel):
    """Track containing clips"""
    clips: List[ClipModel] = Field(..., min_items=1)  # At least one clip required
    
    @validator('clips')
    def validate_clips(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Each track must have at least one clip")
        return v
    
    class Config:
        extra = "allow"

# ============================================================================
# TIMELINE MODEL  
# ============================================================================

class TimelineModel(BaseModel):
    """Complete timeline validation"""
    background: Optional[str] = "#000000"
    tracks: List[TrackModel] = Field(..., min_items=1)
    
    @validator('tracks')
    def validate_tracks(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Timeline must have at least one track")
        return v
    
    @validator('background', pre=True)
    def validate_background(cls, v):
        """Validate background color format"""
        if v is None:
            return "#000000"
        if isinstance(v, str):
            v = v.strip()
            if v.lower() == "null":
                return "#000000"  # Default fallback
            # Basic hex color validation
            if v.startswith('#') and len(v) in [4, 7]:
                return v
            elif v.startswith('#'):
                raise ValueError(f"Invalid hex color format: {v}. Use #RGB or #RRGGBB")
            else:
                # Allow named colors
                return v
        return v
    
    class Config:
        extra = "allow"

# ============================================================================
# OUTPUT MODEL
# ============================================================================

class OutputModel(BaseModel):
    """Output configuration validation"""
    format: Literal["mp4", "gif", "jpg", "png", "bmp", "mp3", "wav"] = "mp4"
    resolution: Optional[Literal["preview", "mobile", "sd", "hd", "1080"]] = "sd"
    quality: Optional[Literal["preview", "low", "medium", "high"]] = "medium"
    fps: Optional[Union[int, float]] = Field(None, ge=1, le=60)
    
    # Handle legacy width/height format
    width: Optional[Union[int, str]] = None
    height: Optional[Union[int, str]] = None
    
    # Modern size object
    size: Optional[Dict[str, Union[int, str]]] = None
    
    # Destinations for GCS transfer
    destinations: Optional[List[Dict[str, Any]]] = None
    
    @validator('width', 'height', pre=True)
    def validate_dimensions(cls, v):
        """Convert string dimensions to int"""
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"Invalid dimension: {v}. Must be a number")
        return v
    
    class Config:
        extra = "allow"

# ============================================================================
# MAIN RENDER REQUEST MODEL
# ============================================================================

class ShotstackRenderRequest(BaseModel):
    """Complete render request with full validation"""
    timeline: TimelineModel
    output: OutputModel
    webhook: Optional[HttpUrl] = None
    
    class Config:
        extra = "forbid"  # Reject unknown fields for main request
        
    @validator('timeline')
    def validate_timeline_not_empty(cls, v):
        """Additional timeline validation"""
        if not v.tracks:
            raise ValueError("Timeline cannot be empty")
        
        # Count total clips
        total_clips = sum(len(track.clips) for track in v.tracks)
        if total_clips == 0:
            raise ValueError("Timeline must have at least one clip")
        
        return v

# ============================================================================
# BATCH RENDER REQUEST MODEL  
# ============================================================================

class BatchRenderRequest(BaseModel):
    """Batch render with individual validation"""
    renders: List[ShotstackRenderRequest] = Field(..., min_items=1, max_items=50)
    
    @validator('renders')
    def validate_batch_size(cls, v):
        if len(v) > 50:
            raise ValueError("Batch size cannot exceed 50 renders")
        if len(v) == 0:
            raise ValueError("Batch must contain at least one render")
        return v
    
    class Config:
        extra = "forbid"

# For N8N array format
BatchRenderArrayRequest = List[ShotstackRenderRequest]

# ============================================================================
# ERROR MODELS
# ============================================================================

class ValidationError(BaseModel):
    """Individual validation error"""
    field: str
    value: Any
    error_type: str
    message: str
    suggestion: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    """Structured validation error response"""
    success: bool = False
    error: str = "Payload validation failed"
    validation_errors: List[ValidationError]
    total_errors: int
    rejected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        extra = "forbid"