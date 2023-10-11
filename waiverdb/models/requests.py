# SPDX-License-Identifier: LGPL-2.0-or-later
from typing import List, Optional, Tuple, Union
from datetime import datetime

from pydantic import BaseModel, Field, root_validator, conlist, constr
from werkzeug.exceptions import BadRequest


RESULT_ID_CONFLICTS_WITH = ("subject_identifier", "subject_type", "subject", "testcase", "scenario")
SUBJECT_CONFLICTS_WITH = ("subject_identifier", "subject_type")


# WaiverDB < 0.11 compatibility
class TestSubject(BaseModel):
    type: Optional[str]
    item: Optional[str]
    original_spec_nvr: Optional[str]
    productmd_compose_id: Optional[str] = Field(alias='productmd.compose.id', default=None)
    __test__ = False        # to tell the PyTest that this is not a test class


class TestResult(BaseModel):
    testcase: str
    subject: TestSubject
    __test__ = False        # to tell the PyTest that this is not a test class


class CreateWaiver(BaseModel):
    subject_type: Optional[str]
    subject_identifier: Optional[str]
    testcase: Optional[str]
    subject: Optional[TestSubject]
    result_id: Optional[int]
    waived: bool = True
    product_version: constr(min_length=1)
    comment: constr(min_length=1)
    username: Optional[str] = None
    scenario: Optional[str] = None

    @root_validator
    def result_id_must_not_conflict(cls, values):
        if values.get("result_id") is None:
            if values.get("testcase") is None:
                raise ValueError("Argument testcase is missing")
            return values
        if all(values.get(x) is None for x in RESULT_ID_CONFLICTS_WITH):
            return values
        raise ValueError(
            "result_id argument should not be used together with arguments: "
            f"{', '.join(RESULT_ID_CONFLICTS_WITH)}"
        )

    @root_validator
    def subject_must_not_conflict(cls, values):
        if values.get("subject") is None:
            return values
        if all(values.get(x) is None for x in SUBJECT_CONFLICTS_WITH):
            return values
        raise ValueError(
            "subject argument should not be used together with arguments: "
            f"{', '.join(SUBJECT_CONFLICTS_WITH)}"
        )

    @root_validator
    def subject_must_be_defined(cls, values):
        if values.get("result_id") is not None:
            return values
        if values.get("subject") is not None:
            return values
        if all(values.get(x) is not None for x in SUBJECT_CONFLICTS_WITH):
            return values
        raise ValueError(
            "subject must be defined using result_id or subject or both "
            f"{', '.join(SUBJECT_CONFLICTS_WITH)}"
        )


class CreateWaiverList(BaseModel):
    __root__: Union[conlist(CreateWaiver, min_items=1), CreateWaiver]


class GetWaivers(BaseModel):
    subject_type: Optional[str]
    subject_identifier: Optional[str]
    testcase: Optional[str]
    product_version: Optional[str]
    username: Optional[str]
    include_obsolete: bool = False
    scenario: Optional[str] = None
    since: Optional[str]
    page: int = 1
    limit: int = 10
    proxied_by: Optional[str]


class GetPermissions(BaseModel):
    testcase: Optional[str]
    html: Optional[bool] = False


class WaiverFilter(BaseModel):
    subject_type: Optional[str]
    subject_identifier: Optional[str]
    testcase: Optional[str]
    scenario: Optional[str]
    product_version: Optional[str]
    username: Optional[str]
    proxied_by: Optional[str]
    since: Optional[str]


class FilterWaivers(BaseModel):
    filters: conlist(WaiverFilter, min_items=1)
    include_obsolete: bool = False


class GetWaiversBySubjectAndTestcase(BaseModel):
    results: Optional[List[TestResult]]
    testcase: Optional[str]
    product_version: Optional[str]
    username: Optional[str]
    proxied_by: Optional[str]
    since: Optional[str]
    include_obsolete: bool = False


def parse_since(since: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parses the 'since' query parameter, which is expected to be either a
    single ISO8601 timestamp representing the start of a time period::

        2017-02-13T23:37:58.193281

    or a comma-separated pair of timestamps representing the start and end of
    a range::

        2017-02-13T23:37:58.193281,2017-02-16T23:37:58.193281

    Returns a tuple (start, end) of datetime.datetime instances.
    """
    start = None
    end = None
    if ',' in since:
        start, end = since.split(',', 1)
    else:
        start = since
    try:
        if start:
            start = datetime.fromisoformat(start)
        if end:
            end = datetime.fromisoformat(end)
    except ValueError as e:
        raise BadRequest({'since': str(e)})
    return start, end
