# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from flask import session

from indico.core import signals
from indico.core.plugins import IndicoPlugin
from indico.modules.events.models.events import EventType
from indico.modules.events.registration.controllers.display import RHRegistrationForm

from indico_regform_passcode.blueprint import blueprint
from indico_regform_passcode.forms import PasscodeForm
from indico_regform_passcode.util import get_regform_url, requires_passcode
from indico_regform_passcode.views import WPRegformPasscodeConference, WPRegformPasscodeSimpleEvent


class RegformPasscodePlugin(IndicoPlugin):
    """Registration Form Passcode

    Protect registration forms with a passcode.
    """

    def init(self):
        super().init()
        self.connect(signals.rh.before_process, self._require_passcode, sender=RHRegistrationForm)

    def get_blueprints(self):
        return blueprint

    def _require_passcode(self, sender, rh, **kwargs):
        if not requires_passcode(rh.regform, session.user, rh.registration):
            return
        view_class = (WPRegformPasscodeConference if rh.event.type_ == EventType.conference
                      else WPRegformPasscodeSimpleEvent)
        return view_class.render_template('code.html', rh.event, regform=rh.regform, form=PasscodeForm(),
                                          action=get_regform_url(rh.regform, 'plugin_regform_passcode.unlock'))
