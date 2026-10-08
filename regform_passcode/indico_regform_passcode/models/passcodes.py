# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from indico.core.db import db
from indico.util.string import format_repr


class RegistrationFormPasscode(db.Model):
    __tablename__ = 'passcodes'
    __table_args__ = {'schema': 'plugin_regform_passcode'}

    #: The registration form protected by this passcode.
    regform_id = db.Column(
        db.Integer,
        db.ForeignKey('event_registration.forms.id', ondelete='CASCADE'),
        primary_key=True,
        autoincrement=False,
    )
    #: The passcode required to access the registration form.
    passcode = db.Column(db.String, nullable=False)
    #: The passcode version used to invalidate grants after a code change.
    version = db.Column(db.Integer, nullable=False, default=1)

    regform = db.relationship(
        'RegistrationForm',
        lazy=True,
        backref=db.backref('passcode_config', uselist=False, lazy=True, cascade='all, delete-orphan'),
    )

    def __repr__(self):
        return format_repr(self, 'regform_id')
