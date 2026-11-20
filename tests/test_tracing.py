# SPDX-License-Identifier: GPL-2.0+

"""Tests for :mod:`waiverdb.tracing`."""

from importlib.metadata import version

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from packaging.requirements import Requirement


def test_sqlalchemy_version_supported_by_opentelemetry():
    """The instrumentor silently disables itself for unsupported versions."""
    installed = version("sqlalchemy")
    requirements = SQLAlchemyInstrumentor().instrumentation_dependencies()
    assert all(
        Requirement(requirement).specifier.contains(installed)
        for requirement in requirements
    ), f"SQLAlchemy {installed} is not supported by the OTel SQLAlchemy instrumentor"
