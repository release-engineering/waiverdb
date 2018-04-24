# SPDX-License-Identifier: GPL-2.0+

from flask_restful import fields

from waiverdb.models.waivers import subject_type_identifier_to_dict


class BackwardsCompatibleSubjectField(fields.Raw):

    def output(self, key, obj):
        waiver = obj
        return subject_type_identifier_to_dict(waiver.subject_type, waiver.subject_identifier)


waiver_fields = {
    'id': fields.Integer,
    'subject_type': fields.String,
    'subject_identifier': fields.String,
    'subject': BackwardsCompatibleSubjectField,
    'testcase': fields.String,
    'username': fields.String,
    'proxied_by': fields.String,
    'product_version': fields.String,
    'waived': fields.Boolean,
    'comment': fields.String,
    'timestamp': fields.DateTime(dt_format='iso8601'),
}
