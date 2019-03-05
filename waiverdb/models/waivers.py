# SPDX-License-Identifier: GPL-2.0+

import datetime
from .base import db
from sqlalchemy import or_, and_, false


def subject_dict_to_type_identifier(subject):
    """
    WaiverDB < 0.11 accepted an arbitrary dict for the 'subject'.
    Now we expect a specific type and identifier.
    This maps from the old style to the new, for backwards compatibility.
    """
    # handling the special cases...
    if (subject.get('type') in ['koji_build', 'brew-build']
            and 'item' in subject
            and isinstance(subject['item'], str)):
        return ('koji_build', subject['item'])
    elif 'original_spec_nvr' in subject and isinstance(subject['original_spec_nvr'], str):
        return ('koji_build', subject['original_spec_nvr'])
    elif 'productmd.compose.id' in subject and isinstance(subject['productmd.compose.id'], str):
        return ('compose', subject['productmd.compose.id'])
    # then handling the general case...
    elif 'item' in subject and isinstance(subject['item'], str):
        return (subject.get('type'), subject['item'])
    else:
        raise ValueError('Subject type should be non empty string, actual value is: %r' % subject)


def subject_type_identifier_to_dict(subject_type, subject_identifier):
    """
    Inverse of the above function.
    This is for backwards compatibility in *responses*.
    """
    if subject_type == 'compose':
        return {'productmd.compose.id': subject_identifier}
    elif subject_type and isinstance(subject_type, str):
        return {'type': subject_type, 'item': subject_identifier}
    else:
        raise ValueError(('Subject type should be non empty string, '
                          'actual value is: %r') % subject_type)


class Waiver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_type = db.Column(db.Text, nullable=False, index=True)
    subject_identifier = db.Column(db.Text, nullable=False, index=True)
    testcase = db.Column(db.Text, nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    proxied_by = db.Column(db.String(255))
    product_version = db.Column(db.String(200), nullable=False)
    waived = db.Column(db.Boolean, nullable=False, default=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (
        db.Index('ix_waiver_subject_type_identifier', subject_type, subject_identifier),
    )

    def __init__(self, subject_type, subject_identifier, testcase, username, product_version,
                 waived=False, comment=None, proxied_by=None):
        self.subject_type = subject_type
        self.subject_identifier = subject_identifier
        self.testcase = testcase
        self.username = username
        self.product_version = product_version
        self.waived = waived
        self.comment = comment
        self.proxied_by = proxied_by

    def __repr__(self):
        return ('%s(subject_type=%r, subject_identifier=%r, testcase=%r, username=%r, '
                'product_version=%r, waived=%r)'
                % (self.__class__.__name__, self.subject_type, self.subject_identifier,
                   self.testcase, self.username, self.product_version, self.waived))

    @classmethod
    def by_results(cls, query, results):
        """
        Filter ``query`` by matching with at least one filter in ``results``.

        If ``results`` is empty, ``query`` is not filtered.

        Args:
            query (flask_sqlalchemy.BaseQuery)
            results (list): each item should be dict containing
                "subject" (dict) and "testcase" (str), both optional

        Returns:
            Filtered query.
        """
        clauses = []
        for result in results:
            subject = result.get('subject', None)
            testcase = result.get('testcase', None)
            if not subject and not testcase:
                continue
            inner_clauses = []
            if subject:
                try:
                    subject_type, subject_identifier = subject_dict_to_type_identifier(subject)
                except ValueError:
                    inner_clauses.append(false())
                else:
                    inner_clauses.append(cls.subject_type == subject_type)
                    inner_clauses.append(cls.subject_identifier == subject_identifier)
            if testcase:
                inner_clauses.append(cls.testcase == testcase)
            clauses.append(and_(*inner_clauses))

        return query.filter(or_(*clauses))
