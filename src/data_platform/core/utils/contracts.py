"""
src.data_platform.core.utils.contracts

Purpose:
    - standardized and reusable data structure

Exposed API:
    - `create_quarter_tasks` - create quarterly tasks for all companies

Exposed Structures:
    - scope contracts:
        - `PeriodScopeTask` - data structure for quarter task planners

Note:
    - only support 'quarter' for now

"""

from __future__ import annotations
import datetime as dt

from dataclasses import dataclass
from typing import Literal, Optional, Sequence


@dataclass(frozen=True)
class PeriodScopeTask:
    company: str

    start: str
    end: str

    fiscal_year: int

    period_grain: Literal[
        "month",
        "quarter",
        "year",
        "custom",
    ]

def _infer_fiscal_year(
    date_value: dt.date,
    fiscal_year_start_month: int = 11,
) -> int:
    """
    Given a date and fiscal year cut off month, determine the fiscal year of the date
    """

    if date_value.month >= fiscal_year_start_month:
        return date_value.year + 1

    return date_value.year

def _detemine_quarter_end_date(
    start: dt.date
) -> dt.date:
    """
    Given the start date of the fiscal quarter, determine the end date of the fiscal quarter
    """
    year = start.year
    month = start.month + 3
    if month > 12:
        year += 1
        month = month % 12
    end = dt.date(year, month, 1) - dt.timedelta(days=1)
    return end

def create_quarter_tasks(
    *,
    companies: Sequence[str],
    start_year: int = 2025,
    fiscal_year_start_month: int = 11
) -> list[PeriodScopeTask]:
    """
    Create tasks as `PeriodScopeTask` for every quarter since `start_year`

    Args:
        `companies`: list of company names
        `start_year`: optional start year for the pipeline job, default: 2025, this is fiscal year
        `fiscal_year_start_momth`: optional cut off month for fiscal years, default 11 (November)

    Returns:
        `PeriodScopeTask` objects including `company, dataset, start, end, period_grain` where dates are in ISO format

    Note
        - system assumes 29 days in Feburary
    """

    tasks: list[PeriodScopeTask] = []

    today = dt.date.today()

    # determine start calendar date for the start_year
    period_start = dt.date(start_year-1, fiscal_year_start_month, 1)

    for company in companies:

        start_date = period_start

        while start_date < today:

            end_date = _detemine_quarter_end_date(start=start_date)

            tasks.append(
                PeriodScopeTask(
                    company=company,

                    start=start_date.isoformat(),
                    end=end_date.isoformat(),

                    fiscal_year=_infer_fiscal_year(
                        start_date,
                        fiscal_year_start_month,
                    ),

                    period_grain="quarter",
                )
            )

            start_date = end_date
        
    return tasks