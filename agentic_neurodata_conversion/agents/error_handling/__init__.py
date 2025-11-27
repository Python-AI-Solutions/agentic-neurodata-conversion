"""Error handling and recovery modules.

This package contains modules for:
- Adaptive retry strategies
- Error recovery and analysis
- Automatic correction systems
"""

from .adaptive_retry import AdaptiveRetryStrategy
from .autocorrect import SmartAutoCorrectionSystem
from .recovery import IntelligentErrorRecovery

__all__ = [
    "AdaptiveRetryStrategy",
    "SmartAutoCorrectionSystem",
    "IntelligentErrorRecovery",
]
