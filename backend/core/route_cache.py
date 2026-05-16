from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class RouteCache(Generic[T]):
    def __init__(self, max_size: int = 100000) -> None:
        self._max_size = max_size
        self._store: OrderedDict[tuple, T] = OrderedDict()

    def get(self, key: tuple) -> T | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        value = self._store[key]
        if hasattr(value, "model_copy"):
            return value.model_copy()
        return value

    def set(self, key: tuple, value: T) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)
