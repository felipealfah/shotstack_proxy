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
            aliases_map = {}
            
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
            
            # PRIMEIRO PASSO: Mapear todos os aliases e suas durações
            for track_index, track in enumerate(tracks):
                if not isinstance(track, dict) or 'clips' not in track:
                    continue
                    
                clips = track['clips']
                if not isinstance(clips, list):
                    continue
                    
                for clip_index, clip in enumerate(clips):
                    if not isinstance(clip, dict):
                        continue
                    
                    # Verificar se clip tem alias
                    clip_alias = clip.get('alias')
                    if clip_alias:
                        clip_start = clip.get('start', 0)
                        clip_length = clip.get('length', 'auto')
                        
                        try:
                            clip_start = float(clip_start) if clip_start is not None else 0
                        except (ValueError, TypeError):
                            clip_start = 0
                        
                        # Para clips com length="auto", estimar duração baseada no asset
                        if clip_length == "auto":
                            asset = clip.get('asset', {})
                            asset_type = asset.get('type', '')
                            
                            # Estimativas para diferentes tipos de asset
                            if asset_type == 'audio':
                                # Para áudio, assumir uma duração padrão se não conseguirmos detectar
                                estimated_duration = 10  # 10 segundos como fallback
                                logger.info(f"Audio asset alias '{clip_alias}': estimated {estimated_duration}s")
                            else:
                                estimated_duration = 5  # 5 segundos para outros tipos
                                logger.info(f"Asset alias '{clip_alias}' type '{asset_type}': estimated {estimated_duration}s")
                                
                            clip_end = clip_start + estimated_duration
                            aliases_map[clip_alias] = {
                                'start': clip_start,
                                'duration': estimated_duration,
                                'end': clip_end
                            }
                        else:
                            try:
                                clip_length = float(clip_length) if clip_length is not None else 0
                                clip_end = clip_start + clip_length
                                aliases_map[clip_alias] = {
                                    'start': clip_start,
                                    'duration': clip_length,
                                    'end': clip_end
                                }
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid length for alias '{clip_alias}'")
                                continue
            
            logger.info(f"Found aliases: {list(aliases_map.keys())}")
            
            # SEGUNDO PASSO: Calcular duração máxima considerando aliases
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
                    
                    # Validate start time
                    try:
                        clip_start = float(clip_start) if clip_start is not None else 0
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid start time in track {track_index}, clip {clip_index}")
                        clip_start = 0
                    
                    # Process length (pode ser número, "auto", "end", ou referência a alias)
                    if isinstance(clip_length, str):
                        if clip_length == "end":
                            # Procurar por alias://referência no asset src
                            asset = clip.get('asset', {})
                            asset_src = asset.get('src', '')
                            
                            if asset_src.startswith('alias://'):
                                alias_ref = asset_src.replace('alias://', '')
                                if alias_ref in aliases_map:
                                    # length="end" significa duração total do alias referenciado
                                    referenced_duration = aliases_map[alias_ref]['duration']
                                    clip_end = clip_start + referenced_duration
                                    logger.info(f"Clip references alias '{alias_ref}': duration {referenced_duration}s")
                                else:
                                    logger.warning(f"Alias reference '{alias_ref}' not found, using default 5s")
                                    clip_end = clip_start + 5  # fallback
                            else:
                                logger.warning(f"length='end' but no alias reference found, using default 5s")
                                clip_end = clip_start + 5  # fallback
                                
                        elif clip_length == "auto":
                            # Auto significa detectar automaticamente, usar estimativa
                            clip_end = clip_start + 5  # fallback para auto
                        else:
                            # String que pode ser número
                            try:
                                clip_length_num = float(clip_length)
                                clip_end = clip_start + clip_length_num
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid string length in track {track_index}, clip {clip_index}: '{clip_length}'")
                                clip_end = clip_start + 5  # fallback
                    else:
                        # Length numérico
                        try:
                            clip_length = float(clip_length) if clip_length is not None else 0
                            clip_end = clip_start + clip_length
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid numeric length in track {track_index}, clip {clip_index}: '{clip_length}'")
                            clip_end = clip_start + 5  # fallback
                    
                    max_duration = max(max_duration, clip_end)
                    logger.debug(f"Track {track_index}, clip {clip_index}: start={clip_start}s, end={clip_end}s")
            
            # Convert to integer seconds (round up for safety)
            total_duration = max(int(max_duration) + (1 if max_duration != int(max_duration) else 0), 1)
            
            logger.info(f"Timeline total duration calculated: {total_duration} seconds (with alias resolution)")
            return total_duration
            
        except Exception as e:
            logger.error(f"Error parsing timeline duration: {str(e)}")
            # Retorna duração mínima de 5 segundos como fallback de segurança
            logger.warning("Returning fallback duration of 5 seconds")
            return 5
    
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