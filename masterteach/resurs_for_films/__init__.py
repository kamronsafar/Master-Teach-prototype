"""
This package provides text analysis functionality for films and subtitles.
"""

from .analyzer import get_analyzer, analyze_text
from .subtit import get_global_analyzer

__all__ = ['get_analyzer', 'analyze_text', 'get_global_analyzer'] 