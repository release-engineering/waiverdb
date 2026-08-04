# SPDX-License-Identifier: LGPL-2.0-or-later
from datetime import datetime
from typing import Annotated

import annotated_types
from pydantic import BaseModel, Field, RootModel, StringConstraints, model_validator
from werkzeug.exceptions import BadRequest

RESULT_ID_CONFLICTS_WITH = (
    "subject_identifier",
    "subject_type",
    "subject",
    "testcase",
    "scenario",
)
SUBJECT_CONFLICTS_WITH = ("subject_identifier", "subject_type")


# WaiverDB < 0.11 compatibility
class TestSubject(BaseModel):
    type: str | None = None
    item: str | None = None
    original_spec_nvr: str | None = None
    productmd_compose_id: str | None = Field(alias='productmd.compose.id', default=None)
    __test__ = False  # to tell the PyTest that this is not a test class


class TestResult(BaseModel):
    testcase: str
    subject: TestSubject
    __test__ = False  # to tell the PyTest that this is not a test class


class CreateWaiver(BaseModel):
    subject_type: str | None = None
    subject_identifier: str | None = None
    testcase: str | None = None
    subject: TestSubject | None = None
    result_id: int | None = None
    waived: bool = True
    product_version: Annotated[str, StringConstraints(min_length=1)]
    comment: Annotated[str, StringConstraints(min_length=1)]
    username: str | None = None
    scenario: str | None = None

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


CreateWaiverList = RootModel[CreateWaiver | list[CreateWaiver]]


class GetWaivers(BaseModel):
    subject_type: str | None = None
    subject_identifier: str | None = None
    testcase: str | None = None
    product_version: str | None = None
    username: str | None = None
    include_obsolete: bool = False
    scenario: str | None = None
    since: str | None = None
    page: int = 1
    limit: int = 10
    proxied_by: str | None = None


class GetPermissions(BaseModel):
    testcase: str | None = None
    html: bool | None = False


class WaiverFilter(BaseModel):
    subject_type: str | None = None
    subject_identifier: str | None = None
    testcase: str | None = None
    scenario: str | None = None
    product_version: str | None = None
    username: str | None = None
    proxied_by: str | None = None
    since: str | None = None


class FilterWaivers(BaseModel):
    filters: Annotated[list[WaiverFilter], annotated_types.Len(min_length=1)]
    include_obsolete: bool = False


class GetWaiversBySubjectAndTestcase(BaseModel):
    results: list[TestResult] | None = None
    testcase: str | None = None
    product_version: str | None = None
    username: str | None = None
    proxied_by: str | None = None
    since: str | None = None
    include_obsolete: bool = False


def parse_since(since: str) -> tuple[datetime | None, datetime | None]:
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
