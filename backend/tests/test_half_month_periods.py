from datetime import date

import pytest

from apps.members.periods import get_half_month_period


@pytest.mark.parametrize(
    ('current', 'expected_start', 'expected_end'),
    [
        (date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 15)),
        (date(2026, 1, 15), date(2026, 1, 1), date(2026, 1, 15)),
        (date(2026, 1, 16), date(2026, 1, 16), date(2026, 1, 31)),
        (date(2026, 4, 30), date(2026, 4, 16), date(2026, 4, 30)),
        (date(2026, 2, 28), date(2026, 2, 16), date(2026, 2, 28)),
        (date(2024, 2, 29), date(2024, 2, 16), date(2024, 2, 29)),
    ],
)
def test_half_month_period_uses_real_calendar_end(
    current, expected_start, expected_end
):
    assert get_half_month_period(current) == (expected_start, expected_end)
