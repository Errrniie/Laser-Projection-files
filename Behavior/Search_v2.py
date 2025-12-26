from dataclasses import dataclass, field
from Config.Seach_Config import min_z, max_z, start_z, step

@dataclass
class SearchConfig:
    min_z: float
    max_z: float
    start_z: float
    step: float
    initial_direction: int = field(default=1)  # +1 for up, -1 for down


class SearchController:
    def __init__(self, config: SearchConfig):
        self._config = config
        self.reset()

    def reset(self):
        self._current_z = self._config.start_z
        self._direction = self._config.initial_direction

    def update(self):
        """
        Computes the next scan Z position and returns a motion intent dict: {"z": float}.
        Does NOT move, block, or control time. Pure logic only.
        """
        min_z, max_z, step = self._config.min_z, self._config.max_z, self._config.step
        z = self._current_z
        direction = self._direction

        # Compute next Z position and reverse direction only at bounds
        next_z = z + step * direction

        # Clamp, reverse at bounds
        if next_z > max_z:
            next_z = max_z
            direction = -1
        elif next_z < min_z:
            next_z = min_z
            direction = 1

        # Update internal state for next call
        self._current_z = next_z
        self._direction = direction

        return {"z": next_z}