# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from datetime import timedelta

import pytest

from indico.core.limiter import limiter
from indico.core.plugins import IndicoPlugin
from indico.modules.events.features.util import set_feature_enabled
from indico.util.date_time import now_utc

from indico_regform_passcode.models.passcodes import RegistrationFormPasscode


pytest_plugins = ['indico.modules.events.registration.testing.fixtures']


@pytest.fixture(autouse=True)
def clear_rate_limits(app):
    limiter.limiter.storage.reset()


@pytest.fixture(autouse=True)
def _plugin_manifest(mocker):
    mocker.patch.object(IndicoPlugin, 'manifest')


@pytest.fixture
def logged_in_user(dummy_user, test_client):
    with test_client.session_transaction() as sess:
        sess.set_session_user(dummy_user)


@pytest.fixture
def configured_regform(db, dummy_regform):
    set_feature_enabled(dummy_regform.event, 'registration', True)
    dummy_regform.require_login = True
    dummy_regform.start_dt = now_utc() - timedelta(days=2)
    config = RegistrationFormPasscode(regform=dummy_regform, passcode='guest-code')
    db.session.add(config)
    db.session.flush()
    return config


@pytest.fixture
def registration_manager(dummy_regform, dummy_user, test_client):
    set_feature_enabled(dummy_regform.event, 'registration', True)
    dummy_regform.event.update_principal(dummy_user, add_permissions={'registration'})
    with test_client.session_transaction() as sess:
        sess.set_session_user(dummy_user)
    test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
    with test_client.session_transaction() as sess:
        return {'X-CSRF-Token': sess['_csrf_token']}
