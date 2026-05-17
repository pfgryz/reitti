from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")
FetchFn = Callable[[int, int], T]
AsyncFetchFn = Callable[[int, int], Awaitable[T]]


class LazyMatrix(Generic[T]):
    def __init__(self, size: int, fetch: FetchFn[T]) -> None:
        if size < 0:
            raise ValueError("size must be non-negative")
        self._size = size
        self._fetch = fetch
        self._cache: dict[tuple[int, int], T] = {}

    @property
    def size(self) -> int:
        return self._size

    def is_cached(self, i: int, j: int) -> bool:
        self._check_indices(i, j)
        return (i, j) in self._cache

    def get(self, i: int, j: int) -> T:
        self._check_indices(i, j)
        key = (i, j)
        if key not in self._cache:
            self._cache[key] = self._fetch(i, j)
        return self._cache[key]

    def __getitem__(self, key: tuple[int, int]) -> T:
        i, j = key
        return self.get(i, j)

    def _check_indices(self, i: int, j: int) -> None:
        if not (0 <= i < self._size and 0 <= j < self._size):
            raise IndexError(f"indices ({i}, {j}) out of range for size {self._size}")


class AsyncLazyMatrix(Generic[T]):
    def __init__(self, size: int, fetch: AsyncFetchFn[T]) -> None:
        if size < 0:
            raise ValueError("size must be non-negative")
        self._size = size
        self._fetch = fetch
        self._cache: dict[tuple[int, int], T] = {}

    @property
    def size(self) -> int:
        return self._size

    def is_cached(self, i: int, j: int) -> bool:
        self._check_indices(i, j)
        return (i, j) in self._cache

    async def get(self, i: int, j: int) -> T:
        self._check_indices(i, j)
        key = (i, j)
        if key not in self._cache:
            self._cache[key] = await self._fetch(i, j)
        return self._cache[key]

    def _check_indices(self, i: int, j: int) -> None:
        if not (0 <= i < self._size and 0 <= j < self._size):
            raise IndexError(f"indices ({i}, {j}) out of range for size {self._size}")


class AsyncMatrixFieldView(Generic[T, R]):
    def __init__(self, source: AsyncLazyMatrix[T], field: str) -> None:
        self._source = source
        self._field = field

    @property
    def size(self) -> int:
        return self._source.size

    def is_cached(self, i: int, j: int) -> bool:
        return self._source.is_cached(i, j)

    async def get(self, i: int, j: int) -> R:
        row = await self._source.get(i, j)
        return getattr(row, self._field)
