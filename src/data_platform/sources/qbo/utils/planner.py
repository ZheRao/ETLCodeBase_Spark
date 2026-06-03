"""
src.data_platform.sources.qbo.utils.planner

Purpose:
    - job planner creates spark jobs as a list of dictionaries, so the meta-data (invariants) of each job is encoded into one single element of the list

Exposed API:
    - `create_jobs` - returns a list of dictionaries with keys `['company', 'start', 'end']`
    - `enrich_qbo_report_task`: enrich global task planner output with QBO report ingestion specific context
    - `group_qbo_tasks_by_company`: group a list of tasks by company name/code

Exposed Structures:
    - `QBOReportIngestionTask` - data structure for quarter task planners for QBO report ingestion pipeline

Note for creating jobs:
    - Must have 
        - company
        - start
        - end
    - Other consideration
        - auth token: instead of appending the token to each task and take up a lot of space,   
        just broadcast the auth dictionary, after refresh every company, to ingest Spark jobs
        - bronze path: can be derived from company + start_year + start_month
        - silver path: Spark partitioned by Company and Fiscal Year - broadcast to jobs
"""

from __future__ import annotations
import datetime as dt
from pathlib import Path
from typing import TypedDict, Sequence, Optional

from dataclasses import dataclass
from collections import defaultdict

from data_platform.core.utils.contracts import PeriodScopeTask
from data_platform.core.utils.filesystem import read_configs

# task schedule schema contract
class FlattenTask(TypedDict):
    company: str
    start: str   # ISO date
    end: str     # ISO date

## hypter parameters
_LAST_DAY = {3: 31, 6: 30, 9: 30, 12: 31} # mapping exact date of quarter end for exact ending dates
_QUARTER_START_MONTHS = (1, 4, 7, 10)

def create_jobs(
    companies: Sequence[str],
    scope: Optional[Sequence[int]] = None,
) -> list[FlattenTask]:
    """
    Create a list of tasks for partitioned flattening of PL/GL report, converting semi-structured JSON file into tabular format for Parquet storage, example:
        {
            "company": "xxx",
            "start": "2024-10-01",
            "end": "2024-12-31",
        }
    """
    # set default scope if not passed
    if not scope:
        scope = [2025, 2026]
    today = dt.date.today()
    tasks: list[FlattenTask] = []
    for company in companies:
        # because FY starts in November of last calender year, include the quarter that begins Oct 1 because the bronze filenames are quarter-based and start in October
        earlist_fy = min(scope)     
        start = dt.date(earlist_fy-1, 10, 1)    
        end = dt.date(earlist_fy-1, 12, 31)
        tasks.append({
            "company": company, 
            "start": start.isoformat(),
            "end": end.isoformat(),
        })
        # create task for every quarter in the scope - skip quarters that hasn't come 
        for year in scope:  
            for month in _QUARTER_START_MONTHS:
                if dt.date(year, month, 1) > today: # skip creating this task if the intended quarter start date is after today - avoid extracting empty data
                    continue 
                start = dt.date(year, month, 1)
                end = dt.date(year, month+2, _LAST_DAY[month+2])
                tasks.append({
                    "company": company, 
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                })
    return tasks

# new planner for report ingestion

@dataclass(frozen=True)
class QBOReportIngestionTask:
    context: PeriodScopeTask
    source_url: str
    source_dataset: str 
    minor_version: int
    out_path: str

def enrich_qbo_report_task(
    *,
    tasks: list[PeriodScopeTask],
    source_dataset: str,
    bronze_root: Path
) -> list[QBOReportIngestionTask]:
    """
    Complete task context for QBO report ingestion tasks

    Args:
        `tasks`: list of global task planner outputs, including `company, dataset, start, end, period_grain`
        `source_dataset`: target report name, e.g., 'PL' or 'GL'
        `bronze_root`: root path to bronze data storage

    Returns:
        `QBOReportIngestionTask` objects including `source_url`, `source_dataset`, `minor_version`, `out_path` as additional context

    Requirements
        - `.../sources/qbo/json_configs/system/qbo.json` config exists
            - minor version config is `int` stored as `str`
        - `source_dataset` is one of ['PL', 'GL']
    
    Note
        - out_path is `bronze_root/QBO/{report_name}/company=.../fiscal_year=.../month=.../api_response.json`
    """
    supported_datasets = ["PL", "GL"] 
    if source_dataset not in supported_datasets:
        raise ValueError(
            f"Unsupported QBO Report Ingestion Dataset.\n\n"
            f"      dataset requested = {source_dataset}.\n"
            f"      supported datasets = {supported_datasets}.\n"
        )
    qbo_config = read_configs(source_system="qbo", config_type="system", name="qbo.json")
    url, minor_version = qbo_config["base_url"], int(qbo_config["minor_version"])
    qbo_report_name_mapping = qbo_config["source_name_mapping"]
    report_name = qbo_report_name_mapping[source_dataset]
    qbo_tasks = []
    for task in tasks:
        start_month = task.start.split("-")[1]
        out_path = (
            f"{bronze_root}/"
            f"QBO/"
            f"{report_name}/"
            f"company={task.company}/"
            f"fiscal_year={task.fiscal_year}/"
            f"month={start_month}/"
            f"api_response.json"
        )
        qbo_tasks.append(
            QBOReportIngestionTask(
                context=task,
                source_url=url,
                source_dataset=report_name,
                minor_version=minor_version,
                out_path=out_path
            )
        )
    return qbo_tasks

def group_qbo_tasks_by_company(
    qbo_tasks: list[QBOReportIngestionTask]
) -> dict[str, QBOReportIngestionTask]:
    """
    Group tasks into a dictioary with `{"company": [qbo_tasks]}`

    Args:
        `qbo_tasks`: list of QBOReportIngestionTask objects where `obj.context.company` contains the company name/code

    Returns:
        Grouped `{"company": [qbo_tasks]}` dictionary
    """
    groups = defaultdict(list)
    for task in qbo_tasks:
        company = task.context.company
        groups[company].append(task)
    return dict(groups)