# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

import json

import pytest
from lxml.html import fromstring

from indico.modules.events.features.util import set_feature_enabled

from indico_regform_passcode.models.passcodes import RegistrationFormPasscode


@pytest.fixture
def registration_manager(dummy_regform, dummy_user, test_client):
    set_feature_enabled(dummy_regform.event, 'registration', True)
    dummy_regform.event.update_principal(dummy_user, add_permissions={'registration'})
    with test_client.session_transaction() as sess:
        sess.set_session_user(dummy_user)
    test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
    with test_client.session_transaction() as sess:
        return {'X-CSRF-Token': sess['_csrf_token']}


@pytest.mark.usefixtures('registration_manager')
class TestPasscodeManagement:
    def test_configure_passcode(self, dummy_regform, test_client, registration_manager):
        dummy_regform.require_login = True
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        response = test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
        assert response.status_code == 200
        assert b'<ind-plugin-regform-passcode-settings' in response.data
        data = json.loads(fromstring(response.data).find('.//ind-plugin-regform-passcode-settings').get('settings'))
        assert data == {'is_enabled': False, 'passcode': '', 'instructions': ''}
        instructions = '<p>Find the code in your email.</p><script>alert(1)</script>'
        response = test_client.post(
            url,
            headers=registration_manager,
            json={
                'is_enabled': True,
                'passcode': 'guest-code',
                'instructions': instructions,
                'invalidate_grants': True,
            },
        )
        assert response.status_code == 200
        assert response.is_json
        config = dummy_regform.passcode_config
        assert config.is_enabled
        assert config.passcode == 'guest-code'
        assert config.instructions == instructions
        assert config.version == 1
        response = test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
        data = json.loads(fromstring(response.data).find('.//ind-plugin-regform-passcode-settings').get('settings'))
        assert data == {'is_enabled': True, 'passcode': 'guest-code', 'instructions': instructions}
        overview = test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
        assert b'Passcode protection' in overview.data
        assert url.encode() in overview.data
        assert b'Enabled' in overview.data

        response = test_client.post(url, headers=registration_manager, json={'instructions': instructions})
        assert response.status_code == 200
        assert not config.is_enabled
        assert config.passcode == 'guest-code'
        assert config.instructions == instructions

    @pytest.mark.parametrize('existing_config', (False, True))
    def test_edit_instructions_without_enabling_passcode(
        self, db, dummy_regform, test_client, registration_manager, existing_config
    ):
        dummy_regform.require_login = True
        if existing_config:
            db.session.add(
                RegistrationFormPasscode(
                    regform=dummy_regform,
                    passcode='saved-code',
                    is_enabled=False,
                    version=3,
                )
            )
            db.session.flush()
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        response = test_client.post(
            url,
            headers=registration_manager,
            json={
                'instructions': '<p>Read your invitation email.</p>',
                'is_enabled': False,
                'passcode': 'ignored-code',
                'invalidate_grants': True,
            },
        )
        assert response.status_code == 200
        config = dummy_regform.passcode_config
        assert config.instructions == '<p>Read your invitation email.</p>'
        assert not config.is_enabled
        assert config.passcode == ('saved-code' if existing_config else '')
        assert config.version == (3 if existing_config else 1)

    @pytest.mark.parametrize('require_login', (False, True))
    @pytest.mark.parametrize('passcode', ('', '   '))
    def test_enabling_requires_login_and_passcode(
        self, dummy_regform, test_client, registration_manager, require_login, passcode
    ):
        dummy_regform.require_login = require_login
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        response = test_client.get(f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/')
        assert response.status_code == 200
        data = json.loads(fromstring(response.data).find('.//ind-plugin-regform-passcode-settings').get('settings'))
        assert not data['is_enabled']
        response = test_client.post(
            url,
            headers=registration_manager,
            json={
                'is_enabled': True,
                'passcode': passcode,
                'instructions': '<p>Read your email.</p>',
            },
        )
        assert response.status_code == 422
        if require_login:
            assert 'passcode' in response.json['webargs_errors']
            assert dummy_regform.passcode_config is None
        else:
            assert '_schema' in response.json['webargs_errors']
            assert dummy_regform.passcode_config is None

    def test_login_requirement_cannot_be_bypassed(self, db, dummy_regform, test_client, registration_manager):
        dummy_regform.require_login = False
        config = RegistrationFormPasscode(regform=dummy_regform, passcode='saved-code', version=3)
        db.session.add(config)
        db.session.flush()
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        response = test_client.post(
            url,
            headers=registration_manager,
            json={
                'is_enabled': True,
                'passcode': 'new-code',
                'invalidate_grants': True,
                'instructions': '<p>Read your email.</p>',
            },
        )
        assert response.status_code == 422
        assert config.is_enabled
        assert config.passcode == 'saved-code'
        assert config.version == 3
        assert config.instructions == ''

    @pytest.mark.parametrize(
        ('change_code', 'invalidate', 'version'),
        (
            (False, True, 1),
            (True, False, 1),
            (True, True, 2),
        ),
    )
    def test_change_passcode(
        self, db, dummy_regform, test_client, registration_manager, change_code, invalidate, version
    ):
        dummy_regform.require_login = True
        config = RegistrationFormPasscode(regform=dummy_regform, passcode='old-code')
        db.session.add(config)
        db.session.flush()
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        data = {
            'is_enabled': True,
            'passcode': 'new-code' if change_code else 'old-code',
            'instructions': '<p>Updated instructions</p>',
            'invalidate_grants': invalidate,
        }
        response = test_client.post(url, headers=registration_manager, json=data)
        assert response.status_code == 200
        assert config.version == version
        assert config.instructions == '<p>Updated instructions</p>'
