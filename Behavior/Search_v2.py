from dataclasses import dataclass, field
import time


@dataclass
class SearchConfig:
    min_angle: float  # degrees
    max_angle: float  # degrees
    start_angle: float  # degrees
    angular_velocity: float = 10.0  # degrees per second
    max_angular_velocity: float = 10  # hard cap deg/s
    initial_direction: int = field(default=1)  # +1 for up, -1 for down


class SearchController:
    """
    Time-based angular search pattern.
    Outputs angular offset in degrees, independent of loop frequency.
    """

    def __init__(self, config: SearchConfig):
        self._config = config
        self._current_angle: float = config.start_angle
        self._direction: int = config.initial_direction
        self._last_update_time: float = time.monotonic()
        # Clamp velocity to hard cap
        self._velocity = min(config.angular_velocity, config.max_angular_velocity)

    def reset(self) -> None:
        self._current_angle = self._config.start_angle
        self._direction = self._config.initial_direction
        self._last_update_time = time.monotonic()

    def update(self) -> dict:
        """
        Compute next angular position based on elapsed wall-clock time.
        Returns {"angle": float} in degrees.
        Time-deterministic: works correctly at any loop frequency.
        """
        now = time.monotonic()
        dt = now - self._last_update_time
        self._last_update_time = now

        # Clamp dt to avoid huge jumps on stall (max 100ms)
        dt = min(dt, 0.1)

        # Advance angle
        delta = self._velocity * dt * self._direction
        next_angle = self._current_angle + delta

        # Bounce at bounds
        if next_angle > self._config.max_angle:
            next_angle = self._config.max_angle
            self._direction = -1
        elif next_angle < self._config.min_angle:
            next_angle = self._config.min_angle
            self._direction = 1

        self._current_angle = next_angle
        return {"angle": next_angle}