"""
Legacy wrapper classes for backward compatibility.

These classes provide the exact same API as the original monolithic implementation
while internally delegating to the superior modular architecture.
"""

from ..utils.deprecation import deprecated_class
from ..core.config import AtlasConfig as ModularAtlasConfig
from ..core.constants import AtlasConstants as ModularAtlasConstants
from ..core.client import AtlasExplorer as ModularAtlasExplorer
from ..core.experiment import Experiment as ModularExperiment
from ..analysis.reports import SummaryReport as ModularSummaryReport


@deprecated_class(
    "Legacy monolithic AtlasConfig is deprecated for security and maintainability.",
    "atlasexplorer.AtlasConfig (modular version with enhanced security)",
    "3.0.0"
)
class LegacyAtlasConfig(ModularAtlasConfig):
    """
    Legacy wrapper for AtlasConfig - provides backward compatibility
    while delegating to the secure modular implementation.
    """
    pass


@deprecated_class(
    "Legacy monolithic AtlasConstants is deprecated.",
    "atlasexplorer.AtlasConstants (modular version)",
    "3.0.0"
)
class LegacyAtlasConstants(ModularAtlasConstants):
    """
    Legacy wrapper for AtlasConstants - provides backward compatibility
    while delegating to the modular implementation.
    """
    pass


@deprecated_class(
    "Legacy monolithic AtlasExplorer is deprecated for security and performance.",
    "atlasexplorer.AtlasExplorer (modular version with enhanced capabilities)",
    "3.0.0"
)
class LegacyAtlasExplorer(ModularAtlasExplorer):
    """
    Legacy wrapper for AtlasExplorer - provides backward compatibility
    while delegating to the enhanced modular implementation.
    """
    pass


@deprecated_class(
    "Legacy monolithic Experiment is deprecated.",
    "atlasexplorer.Experiment (modular version with enhanced validation)",
    "3.0.0"
)
class LegacyExperiment(ModularExperiment):
    """
    Legacy wrapper for Experiment - provides backward compatibility
    while delegating to the modular implementation.
    """
    def cleanSummaries(self):
        """Legacy method name compatibility for cleanSummaries."""
        warnings.warn(
            "cleanSummaries() method not implemented in modular version. "
            "Use Experiment.delete() or manage experiments through AtlasExplorer API.",
            DeprecationWarning,
            stacklevel=2
        )


@deprecated_class(
    "Legacy monolithic SummaryReport is deprecated.",
    "atlasexplorer.SummaryReport (modular version with enhanced analysis)",
    "3.0.0"
)
class LegacySummaryReport(ModularSummaryReport):
    """
    Legacy wrapper for SummaryReport - provides backward compatibility
    while delegating to the enhanced modular implementation.
    """
    
    def getMetricKeys(self):
        """Legacy method name compatibility."""
        return self.get_metric_keys()
    
    def getMetricValue(self, key):
        """Legacy method name compatibility."""
        return self.get_metric_value(key)
    
    def getTotalCycles(self):
        """Legacy method name compatibility."""
        return self.get_total_cycles()
    
    def getTotalInstructions(self):
        """Legacy method name compatibility."""
        return self.get_total_instructions()
    
    def printMetrics(self):
        """Legacy method name compatibility."""
        return self.print_metrics()
