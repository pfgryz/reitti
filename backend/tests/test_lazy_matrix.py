import pytest

from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView, LazyMatrix


def test_lazy_matrix_fetches_once() -> None:
    calls: list[tuple[int, int]] = []

    def fetch(i: int, j: int) -> int:
        calls.append((i, j))
        return i * 10 + j

    matrix = LazyMatrix(3, fetch)
    assert matrix.get(1, 2) == 12
    assert matrix.get(1, 2) == 12
    assert calls == [(1, 2)]


@pytest.mark.asyncio
async def test_async_lazy_matrix_fetches_once() -> None:
    calls: list[tuple[int, int]] = []

    async def fetch(i: int, j: int) -> int:
        calls.append((i, j))
        return i + j

    matrix = AsyncLazyMatrix(3, fetch)
    assert await matrix.get(0, 2) == 2
    assert await matrix.get(0, 2) == 2
    assert calls == [(0, 2)]


@pytest.mark.asyncio
async def test_async_matrix_field_view_shares_cache() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Row:
        time: float
        distance: float

    async def fetch(i: int, j: int) -> Row:
        return Row(time=float(i), distance=float(j * 100))

    source = AsyncLazyMatrix(2, fetch)
    times = AsyncMatrixFieldView(source, "time")
    distances = AsyncMatrixFieldView(source, "distance")

    assert await times.get(1, 1) == 1.0
    assert await distances.get(1, 1) == 100.0
    assert source.is_cached(1, 1)
