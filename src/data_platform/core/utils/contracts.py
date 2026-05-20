"""
src.data_platform.core.utils.contracts

Purpose:
    - standardized and reusable data structure

Exposed API:
    - ``   - 

Exposed Structures:
    - scope contracts:
        - `` - data structure for task planners

Note:
    - only support 'quarter' for now

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PeriodScopeTask:
    company: str
    dataset: str

    start: str
    end: str

    period_grain: Literal[
        "month",
        "quarter",
        "year",
        "custom",
    ]