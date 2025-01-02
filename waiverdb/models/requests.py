# SPDX-License-Identifier: LGPL-2.0-or-later
import annotated_types
from typing import Annotated, List, Optional, Tuple, Union
from datetime import datetime

from pydantic import BaseModel, Field, StringConstraints, RootModel, model_validator
from werkzeug.exceptions import BadRequest


RESULT_ID_CONFLICTS_WITH = ("subject_identifier", "subject_type", "subject", "testcase", "scenario")
SUBJECT_CONFLICTS_WITH = ("subject_identifier", "subject_type")


# WaiverDB < 0.11 compatibility
class TestSubject(BaseModel):
    type: Optional[str] = None
    item: Optional[str] = None
    original_spec_nvr: Optional[str] = None
    productmd_compose_id: Optional[str] = Field(alias='productmd.compose.id', default=None)
    __test__ = False        # to tell the PyTest that this is not a test class


class TestResult(BaseModel):
    testcase: str
    subject: TestSubject
    __test__ = False        # to tell the PyTest that this is not a test class


class CreateWaiver(BaseModel):
    subject_type: Optional[str] = None
    subject_identifier: Optional[str] = None
    testcase: Optional[str] = None
    subject: Optional[TestSubject] = None
    result_id: Optional[int] = None
    waived: bool = True
    product_version: Annotated[str, StringConstraints(min_length=1)]
    comment: Annotated[str, StringConstraints(min_length=1)]
    username: Optional[str] = None
    scenario: Optional[str] = None

    @model_validator(mode='after')
    def result_id_must_not_conflict(self):
        if self.result_id is None:
            if self.testcase is None:
                raise ValueError("Argument testcase is missing")
            return self
        if all(getattr(self, x) is None for x in RESULT_ID_CONFLICTS_WITH):
            return self
        raise ValueError(
            "result_id argument should not be used together with arguments: "
            f"{', '.join(RESULT_ID_CONFLICTS_WITH)}"
        )

    @model_validator(mode='after')
    def subject_must_not_conflict(self):
        if self.subject is None:
            return self
        if all(getattr(self, x) is None for x in SUBJECT_CONFLICTS_WITH):
            return self
        raise ValueError(
            "subject argument should not be used together with arguments: "
            f"{', '.join(SUBJECT_CONFLICTS_WITH)}"
        )

    @model_validator(mode='after')
    def subject_must_be_defined(self):
        if self.result_id is not None:
            return self
        if self.subject is not None:
            return self
        if all(getattr(self, x) is not None for x in SUBJECT_CONFLICTS_WITH):
            return self
        raise ValueError(
            "subject must be defined using result_id or subject or both "
            f"{', '.join(SUBJECT_CONFLICTS_WITH)}"
        )


CreateWaiverList = RootModel[Union[CreateWaiver, List[CreateWaiver]]]


class GetWaivers(BaseModel):
    subject_type: Optional[str] = None
    subject_identifier: Optional[str] = None
    testcase: Optional[str] = None
    product_version: Optional[str] = None
    username: Optional[str] = None
    include_obsolete: bool = False
    scenario: Optional[str] = None
    since: Optional[str] = None
    page: int = 1
    limit: int = 10
    proxied_by: Optional[str] = None


class GetPermissions(BaseModel):
    testcase: Optional[str] = None
    html: Optional[bool] = False


class WaiverFilter(BaseModel):
    subject_type: Optional[str] = None
    subject_identifier: Optional[str] = None
    testcase: Optional[str] = None
    scenario: Optional[str] = None
    product_version: Optional[str] = None
    username: Optional[str] = None
    proxied_by: Optional[str] = None
    since: Optional[str] = None


class FilterWaivers(BaseModel):
    filters: Annotated[List[WaiverFilter], annotated_types.Len(min_length=1)]
    include_obsolete: bool = False


class GetWaiversBySubjectAndTestcase(BaseModel):
    results: Optional[List[TestResult]] = None
    testcase: Optional[str] = None
    product_version: Optional[str] = None
    username: Optional[str] = None
    proxied_by: Optional[str] = None
    since: Optional[str] = None
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
