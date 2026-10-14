# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from datetime import timedelta

import pytest

from indico.modules.events.features.util import set_feature_enabled
from indico.modules.events.models.events import EventType
from indico.modules.events.registration.models.invitations import RegistrationInvitation
from indico.util.date_time import now_utc

from indico_regform_passcode.models.passcodes import RegistrationFormPasscode
from indico_regform_passcode.plugin import RegformPasscodePlugin


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


class TestPasscodeConfiguration:
    @pytest.mark.usefixtures('logged_in_user')
    def test_form_without_passcode_configuration_is_accessible(self, dummy_regform, test_client):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
        response = test_client.get(f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/')
        assert response.status_code == 200
        assert b'id="registration-form-submission-container"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('is_enabled', (False, True))
    def test_passcode_configuration_controls_gate(self, db, dummy_regform, test_client, is_enabled):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
        db.session.add(
            RegistrationFormPasscode(
                regform=dummy_regform,
                passcode='guest-code',
                is_enabled=is_enabled,
                instructions='<p>Check <strong>your invitation</strong>.</p><img src="x" onerror="alert(1)">',
            )
        )
        db.session.flush()
        response = test_client.get(f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/')
        assert response.status_code == 200
        if is_enabled:
            assert b'id="regform-passcode"' in response.data
            assert b'<strong>your invitation</strong>' in response.data
            assert b'onerror=' not in response.data
        else:
            assert b'id="registration-form-submission-container"' in response.data


@pytest.mark.usefixtures('configured_regform')
class TestRegformPasscodePlugin:
    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('availability', ('unopened', 'closed', 'full', 'purged'))
    def test_unavailable_form_does_not_prompt_for_passcode(
        self, db, dummy_regform, create_user, create_registration, test_client, availability
    ):
        if availability == 'unopened':
            dummy_regform.start_dt = now_utc() + timedelta(days=1)
            message = b'The registration period has not started yet.'
        elif availability == 'closed':
            dummy_regform.end_dt = now_utc() - timedelta(days=1)
            message = b'The registration period has passed.'
        elif availability == 'full':
            dummy_regform.registration_limit = 1
            db.session.add(create_registration(create_user(1338), dummy_regform))
            message = b'There are no more places available.'
        else:
            dummy_regform.is_purged = True
            message = b'Registration is disabled due to an expired retention period'
        db.session.flush()

        response = test_client.get(f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/')

        assert response.status_code == 200
        assert message in response.data
        assert b'id="regform-passcode"' not in response.data
        assert b'id="registration-form-submission-container"' not in response.data

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('availability', ('unopened', 'closed', 'full'))
    def test_invitation_to_inactive_form_still_requires_passcode(
        self, db, dummy_regform, dummy_user, create_user, create_registration, test_client, availability
    ):
        if availability == 'unopened':
            dummy_regform.start_dt = now_utc() + timedelta(days=1)
        elif availability == 'closed':
            dummy_regform.end_dt = now_utc() - timedelta(days=1)
        else:
            dummy_regform.registration_limit = 1
            db.session.add(create_registration(create_user(1338), dummy_regform))
        invitation = RegistrationInvitation(
            registration_form=dummy_regform,
            email=dummy_user.email,
            first_name=dummy_user.first_name,
            last_name=dummy_user.last_name,
            affiliation='',
        )
        db.session.add(invitation)
        db.session.flush()

        response = test_client.get(
            f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/',
            query_string={'invitation': str(invitation.uuid)},
        )

        assert response.status_code == 200
        assert b'id="regform-passcode"' in response.data
        assert b'id="registration-form-submission-container"' not in response.data

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
    def test_old_grant_version_is_rejected(self, dummy_regform, test_client, configured_regform):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        assert (
            test_client.post(
                url + 'passcode',
                data={
                    'csrf_token': csrf_token,
                    'passcode': 'guest-code',
                },
            ).status_code
            == 303
        )
        configured_regform.version += 1
        response = test_client.get(url)
        assert b'id="regform-passcode"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('invalidated', ('expired', 'revoked'))
    @pytest.mark.parametrize('private', (False, True))
    def test_invalidated_grant_blocks_submission(
        self, dummy_regform, dummy_user, test_client, configured_regform, freeze_time, invalidated, private
    ):
        dummy_regform.private = private
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        query = {'form_token': str(dummy_regform.uuid)} if private else {}
        test_client.get(url, query_string=query)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        response = test_client.post(
            url + 'passcode', query_string=query, data={'csrf_token': csrf_token, 'passcode': 'guest-code'}
        )
        assert response.status_code == 303
        assert b'id="registration-form-submission-container"' in test_client.get(url, query_string=query).data

        if invalidated == 'expired':
            freeze_time(now_utc() + timedelta(days=2))
        else:
            configured_regform.version += 1

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
        assert response.status_code == 418
        assert response.json == {
            'message': 'Your access to this registration form has expired or been revoked. '
            'Reload the page and enter the passcode again before submitting your registration.'
        }
        assert not dummy_regform.registrations
        assert b'id="regform-passcode"' in test_client.get(url, query_string=query).data

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

    @pytest.mark.usefixtures('no_csrf_check', 'logged_in_user')
    @pytest.mark.parametrize('method', ('GET', 'POST'))
    @pytest.mark.parametrize('event_type', (EventType.lecture, EventType.meeting, EventType.conference))
    def test_new_registration_is_blocked(self, dummy_regform, test_client, method, event_type):
        dummy_regform.event.type_ = event_type
        response = test_client.open(f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/', method=method)
        if method == 'POST':
            assert response.status_code == 418
            assert 'enter the passcode again' in response.json['message']
            assert not dummy_regform.registrations
            return
        assert response.status_code == 200
        assert b'id="regform-passcode"' in response.data
        assert dummy_regform.title.encode() in response.data
        assert b'id="registration-form-submission-container"' not in response.data
        assert not dummy_regform.registrations

    @pytest.mark.usefixtures('smtp', 'logged_in_user')
    def test_another_registration_token_does_not_authorize_submission(
        self, db, dummy_regform, dummy_user, create_user, create_registration, test_client
    ):
        other_registration = create_registration(create_user(1338), dummy_regform)
        db.session.add(other_registration)
        db.session.flush()
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        assert b'id="regform-passcode"' in test_client.get(url).data
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        query = {'token': str(other_registration.uuid)}
        data = {
            'email': dummy_user.email,
            'first_name': dummy_user.first_name,
            'last_name': dummy_user.last_name,
        }

        response = test_client.post(url, query_string=query, headers={'X-CSRF-Token': csrf_token}, json=data)

        assert response.status_code == 418
        assert 'enter the passcode again' in response.json['message']
        assert dummy_regform.get_registration(user=dummy_user) is None
        assert dummy_regform.registrations == [other_registration]
        assert b'Your registration has been completed' in test_client.get(url, query_string=query).data

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token, 'passcode': 'guest-code'})
        assert response.status_code == 303
        response = test_client.post(url, query_string=query, headers={'X-CSRF-Token': csrf_token}, json=data)
        assert response.status_code == 200
        assert dummy_regform.get_registration(user=dummy_user) is not None

    @pytest.mark.usefixtures('logged_in_user')
    def test_existing_registration_submission_preserves_core_error(self, dummy_reg, test_client):
        regform = dummy_reg.registration_form
        url = f'/event/{regform.event_id}/registrations/{regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
            assert 'plugin_regform_passcode_grants' not in sess

        response = test_client.post(url, headers={'X-CSRF-Token': csrf_token}, json={})

        assert response.status_code == 418
        assert response.json['message'] == 'You cannot register for this event'
        assert regform.registrations == [dummy_reg]

    @pytest.mark.usefixtures('smtp')
    def test_anonymous_submission_without_login_requirement(self, dummy_regform, dummy_user, test_client):
        dummy_regform.require_login = False
        dummy_regform.require_captcha = False
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'

        response = test_client.post(
            url,
            headers={'X-CSRF-Token': '00000000-0000-0000-0000-000000000000'},
            json={
                'email': dummy_user.email,
                'first_name': dummy_user.first_name,
                'last_name': dummy_user.last_name,
            },
        )

        assert response.status_code == 200
        assert 'redirect' in response.json
        assert len(dummy_regform.registrations) == 1
        assert dummy_regform.registrations[0].email == dummy_user.email

    def test_existing_registration_is_accessible(self, dummy_reg, test_client):
        response = test_client.get(
            f'/event/{dummy_reg.event_id}/registrations/{dummy_reg.registration_form_id}/',
            query_string={'token': str(dummy_reg.uuid)},
        )
        assert response.status_code == 200
        assert b'Your registration has been completed' in response.data

    @pytest.mark.parametrize(
        ('permission', 'bypass'),
        (
            (None, False),
            ('registration', True),
            ('registration_edit', False),
            ('registration_checkin', False),
            ('registration_moderation', False),
            ('full_access', True),
        ),
    )
    def test_registration_management_bypass(self, dummy_regform, dummy_user, test_client, permission, bypass):
        if permission == 'full_access':
            dummy_regform.event.update_principal(dummy_user, full_access=True)
        elif permission:
            dummy_regform.event.update_principal(dummy_user, add_permissions={permission})
        with test_client.session_transaction() as sess:
            sess.set_session_user(dummy_user)

        response = test_client.get(f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/')

        assert response.status_code == 200
        if bypass:
            assert b'id="registration-form-submission-container"' in response.data
            assert f'data-event-id="{dummy_regform.event_id}"'.encode() in response.data
            assert f'data-regform-id="{dummy_regform.id}"'.encode() in response.data
            with test_client.session_transaction() as sess:
                csrf_token = sess['_csrf_token']
            url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
            response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})
            assert response.status_code == 303
            assert response.location == url
            with test_client.session_transaction() as sess:
                assert 'plugin_regform_passcode_grants' not in sess
        else:
            assert b'id="regform-passcode"' in response.data
            assert b'id="registration-form-submission-container"' not in response.data

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

    def test_anonymous_user_must_log_in(self, dummy_regform, test_client):
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        response = test_client.get(url)
        assert response.status_code == 200
        assert b'Log in to proceed' in response.data
        assert b'id="regform-passcode"' not in response.data
        assert b'id="registration-form-submission-container"' not in response.data

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

    @pytest.mark.parametrize('logged_in', (False, True))
    def test_form_without_login_requirement_is_not_protected(self, dummy_regform, dummy_user, test_client, logged_in):
        dummy_regform.require_login = False
        if logged_in:
            with test_client.session_transaction() as sess:
                sess.set_session_user(dummy_user)
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        response = test_client.get(url)
        assert response.status_code == 200
        assert b'id="registration-form-submission-container"' in response.data
        assert b'id="regform-passcode"' not in response.data

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
