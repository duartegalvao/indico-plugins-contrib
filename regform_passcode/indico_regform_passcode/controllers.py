# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from flask import flash, jsonify, redirect, session

from indico.core.db import db
from indico.core.limiter import make_rate_limiter
from indico.modules.events.registration.controllers.display import RHRegistrationForm
from indico.modules.events.registration.controllers.management import RHManageRegFormBase
from indico.web.args import use_rh_args

from indico_regform_passcode import _
from indico_regform_passcode.forms import PasscodeForm
from indico_regform_passcode.models.passcodes import RegistrationFormPasscode
from indico_regform_passcode.schemas import PasscodeSettingsArgs
from indico_regform_passcode.util import get_regform_url, grant_passcode_access, requires_passcode, validate_passcode


passcode_rate_limiter = make_rate_limiter('regform-passcode', '5/minute', by_ip=False)


class RHUnlockRegistrationForm(RHRegistrationForm):
    def _process_POST(self):
        url = get_regform_url(self.regform, 'event_registration.display_regform')
        if not requires_passcode(self.regform, session.user, self.registration):
            return redirect(url, code=303)

        form = PasscodeForm()
        if form.validate_on_submit():
            if not passcode_rate_limiter.hit(session.user.id, self.regform.id):
                flash(_('Too many passcode attempts. Please try again in a minute.'), 'error')
            elif validate_passcode(self.regform, form.passcode.data):
                grant_passcode_access(self.regform)
            else:
                flash(_('Invalid passcode'), 'error')
        return redirect(url, code=303)


class RHManagePasscode(RHManageRegFormBase):
    @use_rh_args(PasscodeSettingsArgs, location='json')
    def _process_POST(self, data):
        config = self.regform.passcode_config
        invalidate_grants = data.pop('invalidate_grants')
        if not config:
            config = RegistrationFormPasscode(regform=self.regform)
            db.session.add(config)
        elif config.passcode != data['passcode'] and invalidate_grants:
            config.invalidate_grants()
        config.populate_from_dict(data)
        flash(_('Passcode settings saved'), 'success')
        return jsonify(success=True)
