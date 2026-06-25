import math
import hashlib
import redis


class DistributedBloomFilter:
    def __init__(
        self,
        redis_host='localhost',
        redis_port=6379,
        capacity=1_000_000,
        error_rate=0.01,
    ):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            protocol=2,
        )
        self.capacity = capacity
        self.error_rate = error_rate
        self.bit_size = self._optimal_bit_size(capacity, error_rate)
        self.hash_count = self._optimal_hash_count(self.bit_size, capacity)
        self.key = "nightcrawler:bloom_filter"
        print(
            f"[bloom] Ready — {self.bit_size:,} bits "
            f"(~{self.bit_size // 8 / 1024 / 1024:.1f} MB), "
            f"{self.hash_count} hash functions"
        )

    # ── Math ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _optimal_bit_size(capacity: int, error_rate: float) -> int:
        """m = -n * ln(p) / (ln 2)^2"""
        return int(-capacity * math.log(error_rate) / (math.log(2) ** 2))

    @staticmethod
    def _optimal_hash_count(bit_size: int, capacity: int) -> int:
        """k = (m/n) * ln 2"""
        return max(1, int((bit_size / capacity) * math.log(2)))

    def _bit_positions(self, url: str) -> list[int]:
        """Return k bit positions for the given URL using double hashing."""
        positions = []
        for i in range(self.hash_count):
            hash_input = f"{url}:{i}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            positions.append(hash_value % self.bit_size)
        return positions

    # ── Core ops ──────────────────────────────────────────────────────────────

    def add(self, url: str) -> None:
        positions = self._bit_positions(url)
        pipe = self.redis.pipeline()
        for position in positions:
            pipe.setbit(self.key, position, 1)
        pipe.execute()

    def might_exist(self, url: str) -> bool:
        positions = self._bit_positions(url)
        pipe = self.redis.pipeline()
        for position in positions:
            pipe.getbit(self.key, position)
        results = pipe.execute()
        return all(results)

    def clear(self) -> None:
        self.redis.delete(self.key)
        print("[bloom] Filter cleared")