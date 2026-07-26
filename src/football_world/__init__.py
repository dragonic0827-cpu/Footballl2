"""Public API for the football history simulation core."""

from .engine import WorldEngine, build_early_world, build_playable_world
from .model import ConsistencyViolation, WorldState

__all__ = ["ConsistencyViolation", "WorldEngine", "WorldState", "build_early_world", "build_playable_world"]
