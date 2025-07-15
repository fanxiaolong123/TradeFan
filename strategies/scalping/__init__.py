"""剥头皮策略模块"""

from .high_frequency import ScalpingStrategy
from .scalping_strategy import ScalpingStrategy as AdvancedScalpingStrategy

__all__ = ['ScalpingStrategy', 'AdvancedScalpingStrategy']