"""Vertical options spread strategy implementations."""

from src.strategies.base import OptionStrategy
from src.strategies.bull_call_spread import BullCallSpread
from src.strategies.bear_put_spread import BearPutSpread

__all__ = [
    "OptionStrategy",
    "BullCallSpread",
    "BearPutSpread"
]
