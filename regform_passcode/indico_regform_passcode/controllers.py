# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from flask import flash, redirect, session

from indico.modules.events.registration.controllers.display import RHRegistrationForm
from indico.util.i18n import _

from indico_regform_passcode.forms import PasscodeForm
from indico_regform_passcode.util import get_regform_url, grant_passcode_access, requires_passcode, validate_passcode


class RHUnlockRegistrationForm(RHRegistrationForm):
    def _process_POST(self):
        url = get_regform_url(self.regform, 'event_registration.display_regform')
        if not requires_passcode(self.regform, session.user, self.registration):
            return redirect(url, code=303)

        form = PasscodeForm()
        if form.validate_on_submit():
            if validate_passcode(self.regform, form.passcode.data):
                grant_passcode_access(self.regform)
            else:
                flash(_('Invalid passcode'), 'error')
        return redirect(url, code=303)
