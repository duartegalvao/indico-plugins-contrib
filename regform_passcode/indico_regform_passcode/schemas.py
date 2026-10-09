# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from marshmallow import ValidationError, fields, post_load, validates_schema

from indico.core.marshmallow import mm

from indico_regform_passcode import _


class PasscodeSettingsArgs(mm.Schema):
    class Meta:
        rh_context = ('regform',)

    is_enabled = fields.Boolean(load_default=False)
    passcode = fields.String(load_default='')
    invalidate_grants = fields.Boolean(load_default=False)
    instructions = fields.String(load_default='')

    @validates_schema
    def _validate_passcode(self, data, **kwargs):
        if not self.context['regform'].require_login:
            raise ValidationError(_('Passcode protection requires participants to log in.'))
        if data['is_enabled'] and not data['passcode'].strip():
            raise ValidationError(_('This field is required.'), field_name='passcode')

    @post_load
    def _preserve_disabled_passcode(self, data, **kwargs):
        if not data['is_enabled']:
            config = self.context['regform'].passcode_config
            data['passcode'] = config.passcode if config else ''
            data['invalidate_grants'] = False
        return data
