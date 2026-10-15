# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from datetime import timedelta

import pytest

from indico.modules.events.features.util import set_feature_enabled
from indico.util.date_time import now_utc

from indico_regform_passcode.models.passcodes import RegistrationFormPasscode
from indico_regform_passcode.plugin import RegformPasscodePlugin


@pytest.mark.usefixtures('configured_regform')
class TestRHUnlockRegistrationForm:
    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_attempt_limit(self, dummy_regform, test_client):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        for _attempt in range(5):
            response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'wrong-code'})
            assert response.status_code == 303
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'guest-code'})
        assert response.status_code == 303
        response = test_client.get(url)
        assert b'Too many passcode attempts. Please try again in a minute.' in response.data
        assert b'id="regform-passcode"' in response.data
        with test_client.session_transaction() as sess:
            assert not sess.get('plugin_regform_passcode_grants')

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('change', ('ip', 'user', 'form'))
    def test_unlock_limit_scope(self, db, dummy_regform, dummy_user, create_user, create_regform, test_client, change):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        for _attempt in range(5):
            assert (
                test_client.post(
                    url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'wrong-code'}
                ).status_code
                == 303
            )
        user = create_user(1338) if change == 'user' else dummy_user
        with test_client.session_transaction() as sess:
            sess.set_session_user(user)
        if change == 'form':
            regform = create_regform(dummy_regform.event, require_login=True, start_dt=dummy_regform.start_dt)
            db.session.add(RegistrationFormPasscode(regform=regform, passcode='guest-code'))
            db.session.flush()
            url = f'/event/{regform.event_id}/registrations/{regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        response = test_client.post(
            url + 'passcode',
            data={'csrf_token': csrf_token, 'passcode': 'guest-code'},
            environ_overrides={'REMOTE_ADDR': '192.0.2.1'} if change == 'ip' else {},
        )
        assert response.status_code == 303
        response = test_client.get(url)
        if change == 'ip':
            assert b'Too many passcode attempts' in response.data
            assert b'id="regform-passcode"' in response.data
        else:
            assert b'id="registration-form-submission-container"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize(
        ('saved_code', 'submitted_code', 'valid'),
        (
            ('guest-code', None, False),
            ('guest-code', '', False),
            ('guest-code', 'wrong-code', False),
            ('guest-code', 'GUEST-code', False),
            ('guest-code', ' guest-code ', True),
            ('guest code', 'guestcode', False),
            ('guest-code', 'guest-code', True),
            ('café-🔑', 'cafe-🔑', False),
            ('café-🔑', 'café-🔑', True),
        ),
    )
    def test_unlock_validates_passcode(
        self, dummy_regform, test_client, configured_regform, saved_code, submitted_code, valid
    ):
        configured_regform.passcode = saved_code
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            data = {'csrf_token': sess['_csrf_token']}
        if submitted_code is not None:
            data['passcode'] = submitted_code

        response = test_client.post(url + 'passcode', data=data)
        assert response.status_code == 303
        assert response.location == url
        with test_client.session_transaction() as sess:
            assert (str(dummy_regform.id) in sess.get('plugin_regform_passcode_grants', {})) == valid
        response = test_client.get(url)
        if valid:
            assert b'id="registration-form-submission-container"' in response.data
        else:
            assert b'id="regform-passcode"' in response.data
            assert b'Invalid passcode' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    def test_configured_duration_applies_to_new_grants(self, dummy_regform, test_client, freeze_time):
        RegformPasscodePlugin.settings.set('grant_duration', 15)
        granted_at = now_utc()
        freeze_time(granted_at)
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'guest-code'})
        assert response.status_code == 303
        with test_client.session_transaction() as sess:
            assert (
                sess['plugin_regform_passcode_grants'][str(dummy_regform.id)]['expires']
                == (granted_at + timedelta(minutes=15)).timestamp()
            )

        RegformPasscodePlugin.settings.set('grant_duration', 60)
        freeze_time(granted_at + timedelta(minutes=16))
        assert b'id="regform-passcode"' in test_client.get(url).data
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'guest-code'})
        assert response.status_code == 303
        freeze_time(granted_at + timedelta(minutes=32))
        assert b'id="registration-form-submission-container"' in test_client.get(url).data

    @pytest.mark.usefixtures('smtp', 'logged_in_user')
    @pytest.mark.parametrize('private', (False, True))
    def test_submit_passcode_unlocks_form(self, dummy_regform, dummy_user, test_client, private):
        dummy_regform.private = private
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        query = {'form_token': str(dummy_regform.uuid)} if private else {}
        response = test_client.get(url, query_string=query)
        assert b'id="regform-passcode"' in response.data
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        assert csrf_token != '00000000-0000-0000-0000-000000000000'
        assert csrf_token.encode() in response.data

        response = test_client.post(
            url + 'passcode',
            query_string=query,
            data={
                'csrf_token': csrf_token,
                'passcode': 'guest-code',
            },
        )
        assert response.status_code == 303
        assert response.location == url + (f'?form_token={dummy_regform.uuid}' if private else '')

        response = test_client.get(response.location)
        assert response.status_code == 200
        assert b'id="registration-form-submission-container"' in response.data
        assert b'id="regform-passcode"' not in response.data

        dummy_regform.require_captcha = False
        response = test_client.post(
            url,
            query_string=query,
            headers={'X-CSRF-Token': csrf_token},
            json={
                'email': dummy_user.email,
                'first_name': dummy_user.first_name,
                'last_name': dummy_user.last_name,
            },
        )
        assert response.status_code == 200
        assert 'redirect' in response.json
        assert len(dummy_regform.registrations) == 1

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('csrf_token', (None, '00000000-0000-0000-0000-000000000000'))
    def test_unlock_requires_csrf(self, dummy_regform, test_client, csrf_token):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token} if csrf_token else {})
        assert response.status_code == 400
        response = test_client.get(url)
        assert b'id="regform-passcode"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_is_scoped_and_does_not_renew_grant(
        self, db, dummy_regform, create_regform, test_client, freeze_time
    ):
        other_regform = create_regform(dummy_regform.event, start_dt=dummy_regform.start_dt, require_login=True)
        db.session.add(RegistrationFormPasscode(regform=other_regform, passcode='another-code'))
        db.session.flush()
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'guest-code'})
        assert response.status_code == 303
        assert b'id="registration-form-submission-container"' in test_client.get(url).data
        with test_client.session_transaction() as sess:
            grants = sess['plugin_regform_passcode_grants'].copy()
        freeze_time(now_utc() + timedelta(minutes=20))
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})
        assert response.status_code == 303
        assert response.location == url
        with test_client.session_transaction() as sess:
            assert sess['plugin_regform_passcode_grants'] == grants

        response = test_client.get(f'/event/{other_regform.event_id}/registrations/{other_regform.id}/')
        assert b'id="regform-passcode"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_requires_matching_event(self, dummy_regform, create_event, test_client):
        other_event = create_event()
        set_feature_enabled(other_event, 'registration', True)
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']

        response = test_client.post(
            f'/event/{other_event.id}/registrations/{dummy_regform.id}/passcode', data={'csrf_token': csrf_token}
        )
        assert response.status_code == 404
        assert b'id="regform-passcode"' in test_client.get(url).data

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_requires_login_required_form(self, dummy_regform, test_client):
        dummy_regform.require_login = False
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})
        assert response.status_code == 303
        with test_client.session_transaction() as sess:
            assert 'plugin_regform_passcode_grants' not in sess

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_redirects_existing_registration(self, dummy_reg, test_client):
        regform = dummy_reg.registration_form
        url = f'/event/{regform.event_id}/registrations/{regform.id}/'
        response = test_client.get(url)
        assert b'Your registration has been completed' in response.data
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})
        assert response.status_code == 303
        assert response.location == url
        with test_client.session_transaction() as sess:
            assert 'plugin_regform_passcode_grants' not in sess

    def test_anonymous_user_must_log_in(self, dummy_regform, test_client):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        response = test_client.post(
            url + 'passcode',
            data={
                'csrf_token': '00000000-0000-0000-0000-000000000000',
            },
        )
        assert response.status_code == 302
        assert '/login/' in response.location
        assert b'id="regform-passcode"' not in response.data
        with test_client.session_transaction() as sess:
            assert 'plugin_regform_passcode_grants' not in sess

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('permission', ('registration', 'full_access'))
    def test_unlock_redirects_registration_manager(self, dummy_regform, dummy_user, test_client, permission):
        if permission == 'full_access':
            dummy_regform.event.update_principal(dummy_user, full_access=True)
        else:
            dummy_regform.event.update_principal(dummy_user, add_permissions={permission})
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})

        assert response.status_code == 303
        assert response.location == url
        with test_client.session_transaction() as sess:
            assert 'plugin_regform_passcode_grants' not in sess


@pytest.mark.usefixtures('registration_manager')
class TestRHManagePasscode:
    def test_configure_passcode(self, dummy_regform, test_client, registration_manager):
        dummy_regform.require_login = True
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
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
        with test_client.session_transaction() as sess:
            assert ('success', 'Passcode settings saved') in sess['_flashes']
        config = dummy_regform.passcode_config
        assert config.is_enabled
        assert config.passcode == 'guest-code'
        assert config.instructions == instructions
        assert config.version == 1
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

    def test_change_passcode_with_stale_version(self, db, dummy_regform, test_client, registration_manager):
        dummy_regform.require_login = True
        config = RegistrationFormPasscode(regform=dummy_regform, passcode='old-code')
        db.session.add(config)
        db.session.flush()
        RegistrationFormPasscode.query.filter_by(regform_id=dummy_regform.id).update(
            {'passcode': 'first-code', 'version': 2}, synchronize_session=False
        )
        assert config.version == 1
        url = f'/event/{dummy_regform.event_id}/manage/registration/{dummy_regform.id}/passcode'
        response = test_client.post(
            url,
            headers=registration_manager,
            json={'is_enabled': True, 'passcode': 'second-code', 'invalidate_grants': True},
        )
        assert response.status_code == 200
        db.session.refresh(config)
        assert config.passcode == 'second-code'
        assert config.version == 3
