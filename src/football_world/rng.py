import hashlib


class DeterministicRng:
    """Counter-based RNG whose state is entirely represented by seed and counter."""

    def __init__(self, seed: int, counter: int = 0) -> None:
        self.seed, self.counter = seed, counter

    def random(self, domain: str) -> float:
        raw = hashlib.sha256(f"{self.seed}:{self.counter}:{domain}".encode()).digest()
        self.counter += 1
        return int.from_bytes(raw[:8], "big") / 2**64

