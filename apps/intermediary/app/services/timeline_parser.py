"""
Timeline Parser Service for Shotstack timelines
Extracts video duration and other metadata from timeline JSON
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TimelineParser:
    """
    Parser for Shotstack timeline JSON format
    Extracts total video duration and other metadata
    """
    
    @staticmethod
    def extract_total_duration(timeline: Dict[str, Any]) -> int:
        """
        Extract total video duration from Shotstack timeline
        
        Args:
            timeline: Shotstack timeline dictionary
            
        Returns:
            int: Total duration in seconds
            
        Examples:
            >>> timeline = {
            ...     "tracks": [{
            ...         "clips": [{
            ...             "start": 0,
            ...             "length": 30,
            ...             "asset": {"type": "title", "text": "Test"}
            ...         }]
            ...     }]
            ... }
            >>> TimelineParser.extract_total_duration(timeline)
            30
        """
        try:
            max_duration = 0
            
            if not timeline or not isinstance(timeline, dict):
                logger.warning("Invalid timeline format - not a dictionary")
                return 0
                
            if 'tracks' not in timeline:
                logger.warning("Timeline missing 'tracks' key")
                return 0
                
            tracks = timeline['tracks']
            if not isinstance(tracks, list):
                logger.warning("Timeline 'tracks' is not a list")
                return 0
                
            for track_index, track in enumerate(tracks):
                if not isinstance(track, dict):
                    logger.warning(f"Track {track_index} is not a dictionary")
                    continue
                    
                if 'clips' not in track:
                    logger.warning(f"Track {track_index} missing 'clips' key")
                    continue
                    
                clips = track['clips']
                if not isinstance(clips, list):
                    logger.warning(f"Track {track_index} 'clips' is not a list")
                    continue
                    
                for clip_index, clip in enumerate(clips):
                    if not isinstance(clip, dict):
                        logger.warning(f"Track {track_index}, clip {clip_index} is not a dictionary")
                        continue
                        
                    # Extract clip timing
                    clip_start = clip.get('start', 0)
                    clip_length = clip.get('length', 0)
                    
                    # Validate numeric values
                    try:
                        clip_start = float(clip_start) if clip_start is not None else 0
                        clip_length = float(clip_length) if clip_length is not None else 0
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid numeric values in track {track_index}, clip {clip_index}")
                        continue
                    
                    clip_end = clip_start + clip_length
                    max_duration = max(max_duration, clip_end)
                    
                    logger.debug(f"Track {track_index}, clip {clip_index}: start={clip_start}s, length={clip_length}s, end={clip_end}s")
            
            # Convert to integer seconds (round up for safety)
            total_duration = int(max_duration) if max_duration == int(max_duration) else int(max_duration) + 1
            
            logger.info(f"Timeline total duration calculated: {total_duration} seconds")
            return total_duration
            
        except Exception as e:
            logger.error(f"Error parsing timeline duration: {str(e)}")
            return 0
    
    @staticmethod
    def validate_timeline(timeline: Dict[str, Any]) -> bool:
        """
        Validate if timeline has the minimum required structure
        
        Args:
            timeline: Shotstack timeline dictionary
            
        Returns:
            bool: True if timeline is valid
        """
        try:
            if not timeline or not isinstance(timeline, dict):
                return False
                
            if 'tracks' not in timeline:
                return False
                
            tracks = timeline['tracks']
            if not isinstance(tracks, list) or len(tracks) == 0:
                return False
                
            # At least one track should have clips
            for track in tracks:
                if isinstance(track, dict) and 'clips' in track:
                    clips = track['clips']
                    if isinstance(clips, list) and len(clips) > 0:
                        return True
            
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def get_asset_types(timeline: Dict[str, Any]) -> list:
        """
        Extract all asset types used in the timeline
        
        Args:
            timeline: Shotstack timeline dictionary
            
        Returns:
            list: List of asset types (e.g., ['title', 'video', 'audio'])
        """
        asset_types = set()
        
        try:
            if not timeline or 'tracks' not in timeline:
                return []
                
            for track in timeline['tracks']:
                if not isinstance(track, dict) or 'clips' not in track:
                    continue
                    
                for clip in track['clips']:
                    if isinstance(clip, dict) and 'asset' in clip:
                        asset = clip['asset']
                        if isinstance(asset, dict) and 'type' in asset:
                            asset_types.add(asset['type'])
            
            return sorted(list(asset_types))
            
        except Exception as e:
            logger.error(f"Error extracting asset types: {str(e)}")
            return []