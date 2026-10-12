# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from datetime import timedelta
from hmac import compare_digest

from flask import request, session
from flask_pluginengine import current_plugin

from indico.util.date_time import now_utc
from indico.web.flask.util import url_for


def get_regform_url(regform, endpoint):
    args = {key: request.args[key] for key in ('form_token', 'invitation', 'token') if key in request.args}
    return url_for(endpoint, regform, **args)


def validate_passcode(regform, passcode):
    passcode = (passcode or '').strip()
    return bool(passcode) and compare_digest(regform.passcode_config.passcode.strip().encode(), passcode.encode())


def requires_passcode(regform, user, registration):
    if not regform.require_login or not user or registration:
        return False
    if regform.event.can_manage(user, permission='registration'):
        return False
    config = regform.passcode_config
    if not config or not config.is_enabled:
        return False
    grant = session.get('plugin_regform_passcode_grants', {}).get(str(regform.id))
    return (
        not isinstance(grant, dict)
        or grant.get('version') != config.version
        or grant.get('expires', 0) < now_utc().timestamp()
    )


def grant_passcode_access(regform):
    grants = session.get('plugin_regform_passcode_grants', {}).copy()
    duration = timedelta(minutes=current_plugin.settings.get('grant_duration'))
    grants[str(regform.id)] = {
        'expires': (now_utc() + duration).timestamp(),
        'version': regform.passcode_config.version,
    }
    session['plugin_regform_passcode_grants'] = grants
