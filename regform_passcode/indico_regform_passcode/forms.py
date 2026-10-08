# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from wtforms import IntegerField, PasswordField
from wtforms.validators import InputRequired, NumberRange

from indico.util.i18n import _
from indico.web.forms.base import IndicoForm


class SettingsForm(IndicoForm):
    grant_duration = IntegerField(
        _('Passcode access duration (minutes)'),
        validators=[InputRequired(), NumberRange(min=1)],
        description=_('How long access lasts after entering the passcode. Changes apply only to new grants.'),
    )


class PasscodeForm(IndicoForm):
    passcode = PasswordField(_('Passcode'))
