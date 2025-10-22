"""
History Parse Package - Basin-specific parsers for *-list.txt files.
"""
from .base import BaseHistoryParser
from .basin_wp import WesternPacificParser
from .basin_sh import SouthernHemisphereParser
from .basin_ep import EasternPacificParser
from .basin_io import IndianOceanParser


def get_parser_for_basin(basin: str) -> BaseHistoryParser:
    """
    Get the appropriate parser for a basin.
    
    Args:
        basin: Basin code (WP, SH, EP, IO, AL, CP)
    
    Returns:
        Parser instance for the basin
    """
    parser_map = {
        'WP': WesternPacificParser,
        'SH': SouthernHemisphereParser,
        'EP': EasternPacificParser,
        'IO': IndianOceanParser,
        'AL': EasternPacificParser,  # Atlantic uses similar format
        'CP': WesternPacificParser,  # Central Pacific uses similar format
    }
    
    parser_class = parser_map.get(basin, BaseHistoryParser)
    return parser_class()


__all__ = [
    'BaseHistoryParser',
    'WesternPacificParser',
    'SouthernHemisphereParser',
    'EasternPacificParser',
    'IndianOceanParser',
    'get_parser_for_basin',
]
