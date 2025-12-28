from collections import deque
from typing import Any


class RingBuffer(deque[Any]):
    """
    Inherits deque, pops the oldest data to make room
    for the newest data when size is reached.
    """

    def __init__(self, size: int) -> None:
        super().__init__(maxlen=size)
        self.size = size

    def append(self, item: Any) -> None:
        super().append(item)

    def get(self) -> list[Any]:
        """Returns a list of items (newest items)."""
        return list(self)


# testing
if __name__ == "__main__":
    size_val = 5
    ring = RingBuffer(size_val)
    for x in range(9):
        ring.append(x)
        print(ring.get())
