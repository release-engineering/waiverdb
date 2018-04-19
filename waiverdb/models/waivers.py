# SPDX-License-Identifier: GPL-2.0+

import datetime
from .base import db, EqualityComparableJSONType
from sqlalchemy import or_, and_, cast


class Waiver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(EqualityComparableJSONType, nullable=False)
    testcase = db.Column(db.Text, nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    proxied_by = db.Column(db.String(255))
    product_version = db.Column(db.String(200), nullable=False)
    waived = db.Column(db.Boolean, nullable=False, default=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (
        db.Index('ix_waiver_subject', cast(subject, db.Text)),
    )

    def __init__(self, subject, testcase, username, product_version, waived=False,
                 comment=None, proxied_by=None):
        self.subject = subject
        self.testcase = testcase
        self.username = username
        self.product_version = product_version
        self.waived = waived
        self.comment = comment
        self.proxied_by = proxied_by

    def __repr__(self):
        return '%s(subject=%r, testcase=%r, username=%r, product_version=%r, waived=%r)' % (
            self.__class__.__name__, self.subject, self.testcase, self.username,
            self.product_version, self.waived)

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
            if subject or testcase:
                clauses.append(and_(
                    not subject or cls.subject == subject,
                    not testcase or cls.testcase == testcase
                ))

        return query.filter(or_(*clauses))
