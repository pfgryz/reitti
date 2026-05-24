import pytest

from core.lazy_matrix import AsyncLazyMatrix, AsyncMatrixFieldView, LazyMatrix
from core.route_optimizer import TravelLeg


def test_lazy_matrix_caches() -> None:
    calls: list[tuple[int, int]] = []

    def fetch(i: int, j: int) -> int:
        calls.append((i, j))
        return i * 10 + j

    m = LazyMatrix(3, fetch)
    assert m.get(1, 2) == 12
    assert m.get(1, 2) == 12
    assert calls == [(1, 2)]


@pytest.mark.asyncio
async def test_async_lazy_matrix_and_field_view() -> None:
    calls: list[tuple[int, int]] = []

    async def fetch(i: int, j: int) -> TravelLeg:
        calls.append((i, j))
        return TravelLeg(float(i), float(j * 100), float(j * 100))

    source = AsyncLazyMatrix(2, fetch)
    times = AsyncMatrixFieldView(source, "time")
    dist = AsyncMatrixFieldView(source, "distance")

    assert await times.get(1, 1) == 1.0
    assert await dist.get(1, 1) == 100.0
    assert await times.get(1, 1) == 1.0
    assert calls == [(1, 1)]
