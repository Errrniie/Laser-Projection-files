from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    """Search pattern configuration. All units in mm."""
    min_z: float = 0.0       # mm (Z_MIN)
    max_z: float = 20.0      # mm (Z_MAX)
    start_z: float = 10.0    # mm (starting position)
    step_size: float = 1.0   # mm per step
    initial_direction: int = field(default=1)  # +1 for up, -1 for down


class SearchController:
    """
    Step-based search pattern.
    Outputs relative Z delta in mm for each step.
    Waits for motion completion before returning next step.
    Pattern: start_z → max_z → min_z → max_z (repeating)
    """

    def __init__(self, config: SearchConfig):
        self._config = config
        self._current_z: float = config.start_z
        self._direction: int = config.initial_direction
        self._step_size: float = config.step_size

    def reset(self) -> None:
        self._current_z = self._config.start_z
        self._direction = self._config.initial_direction

    def update(self) -> dict:
        """
        Compute next step delta.
        Returns {"z_delta": float} in mm.
        Called once per motion cycle - caller must wait for completion before calling again.
        """
        # Compute next position
        delta = self._step_size * self._direction
        next_z = self._current_z + delta

        # Bounce at bounds
        if next_z >= self._config.max_z:
            next_z = self._config.max_z
            delta = next_z - self._current_z
            self._direction = -1
        elif next_z <= self._config.min_z:
            next_z = self._config.min_z
            delta = next_z - self._current_z
            self._direction = 1

        self._current_z = next_z
        return {"z_delta": delta, "z_absolute": next_z}