# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from indico.core.plugins import IndicoPluginBlueprint

from indico_regform_passcode.controllers import RHUnlockRegistrationForm


blueprint = IndicoPluginBlueprint('regform_passcode', __name__, url_prefix='/event/<int:event_id>')
blueprint.add_url_rule(
    '/registrations/<int:reg_form_id>/passcode', 'unlock', RHUnlockRegistrationForm, methods=('POST',)
)
