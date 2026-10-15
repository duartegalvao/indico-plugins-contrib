# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from flask import request, session
from flask_pluginengine import render_plugin_template

from indico.core import signals
from indico.core.db import db
from indico.core.plugins import IndicoPlugin
from indico.modules.events.models.events import EventType
from indico.modules.events.registration.controllers.display import RHRegistrationForm
from indico.modules.events.registration.views import WPManageRegistration
from indico.web.util import ExpectedError

from indico_regform_passcode import _
from indico_regform_passcode.blueprint import blueprint
from indico_regform_passcode.forms import PasscodeForm, SettingsForm
from indico_regform_passcode.models.passcodes import RegistrationFormPasscode
from indico_regform_passcode.util import get_regform_url, requires_passcode
from indico_regform_passcode.views import (
    WPRegformPasscodeConference,
    WPRegformPasscodeSimpleEvent,
)


class RegformPasscodePlugin(IndicoPlugin):
    """Registration Form Passcode

    Protect registration forms with a passcode.
    """

    configurable = True
    settings_form = SettingsForm
    default_settings = {'grant_duration': 1440}  # 24 hours

    def init(self):
        super().init()
        self.inject_bundle('main.js', WPManageRegistration)
        self.connect(signals.rh.before_process, self._require_passcode, sender=RHRegistrationForm)
        self.template_hook('extra-regform-settings', self._passcode_settings)
        self.connect(signals.event.registration.after_registration_form_clone, self._clone_passcode_settings)

    def get_blueprints(self):
        return blueprint

    def _clone_passcode_settings(self, sender, new_form, **kwargs):
        if config := sender.passcode_config:
            db.session.add(
                RegistrationFormPasscode(
                    regform=new_form,
                    passcode=config.passcode,
                    is_enabled=config.is_enabled,
                    instructions=config.instructions,
                )
            )

    def _passcode_settings(self, regform, **kwargs):
        config = regform.passcode_config
        settings = {
            'is_enabled': bool(config and config.is_enabled and regform.require_login),
            'passcode': config.passcode if config else '',
            'instructions': config.instructions if config else '',
        }
        return render_plugin_template('management/settings_box.html', regform=regform, settings=settings)

    def _require_passcode(self, sender, rh, **kwargs):
        if not rh._can_register():
            return
        if request.method == 'GET':
            registration = rh.registration
        else:
            registration = rh.regform.get_registration(user=session.user) if session.user else None
        if not requires_passcode(rh.regform, session.user, registration):
            return
        if request.method == 'POST':
            raise ExpectedError(
                _(
                    'Your access to this registration form has expired or been revoked. '
                    'Reload the page and enter the passcode again before submitting your registration.'
                )
            )
        view_class = (
            WPRegformPasscodeConference if rh.event.type_ == EventType.conference else WPRegformPasscodeSimpleEvent
        )
        return view_class.render_template(
            'code.html',
            rh.event,
            regform=rh.regform,
            form=PasscodeForm(),
            action=get_regform_url(rh.regform, 'plugin_regform_passcode.unlock'),
        )
