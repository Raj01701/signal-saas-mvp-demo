"""Chart computation shared by the routes, with an in-memory LRU cache.

Charts are deterministic for the same birth data, settings and engine version, so
the cache key is a hash of the first two (one process runs one engine version).
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult
from jyotish_engine.settings import Preset, Settings, preset


def resolve_settings(settings: Settings | None, preset_name: Preset | None) -> Settings:
    if settings is not None:
        return settings
    return preset(preset_name) if preset_name is not None else Settings()


class ChartCache:
    def __init__(self, size: int) -> None:
        self._size = size
        self._items: OrderedDict[str, ChartResult] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    @staticmethod
    def key(birth: BirthInput, settings: Settings) -> str:
        text = birth.model_dump_json() + settings.model_dump_json()
        return hashlib.sha256(text.encode()).hexdigest()

    def chart(self, birth: BirthInput, settings: Settings) -> ChartResult:
        key = self.key(birth, settings)
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                self.hits += 1
                return self._items[key]
        chart = compute_chart(birth, settings)
        with self._lock:
            self.misses += 1
            self._items[key] = chart
            while len(self._items) > self._size:
                self._items.popitem(last=False)
        return chart
