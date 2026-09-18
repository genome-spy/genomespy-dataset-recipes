# mypy: ignore-errors
from __future__ import annotations

import math
from typing import Any

MISSING_VALUE_TOKENS = {"", "na", "n/a", "nan", "null", "none"}


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in MISSING_VALUE_TOKENS
