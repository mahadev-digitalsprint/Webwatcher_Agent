from collections import defaultdict
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: dict[str, float] = field(default_factory=dict)

    def inc(self, key: str, value: int = 1) -> None:
        self.counters[key] += value

    def set_gauge(self, key: str, value: float) -> None:
        self.gauges[key] = value

    def snapshot(self) -> dict[str, dict]:
        return {"counters": dict(self.counters), "gauges": dict(self.gauges)}


metrics = MetricsRegistry()


class Timer:
    def __init__(self, metric_name: str) -> None:
        self.metric_name = metric_name
        self._start = 0.0

    def __enter__(self) -> "Timer":
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        duration_ms = (perf_counter() - self._start) * 1000
        metrics.set_gauge(self.metric_name, duration_ms)

