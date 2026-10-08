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
from indico.util.date_time import now_utc


@pytest.fixture
def logged_in_user(dummy_user, test_client):
    with test_client.session_transaction() as sess:
        sess.set_session_user(dummy_user)


class TestRegformPasscodePlugin:
    @pytest.mark.usefixtures('no_csrf_check', 'logged_in_user')
    @pytest.mark.parametrize('method', ('GET', 'POST'))
    @pytest.mark.parametrize('event_type', (EventType.lecture, EventType.meeting, EventType.conference))
    def test_new_registration_is_blocked(self, dummy_regform, test_client, method, event_type):
        dummy_regform.event.type_ = event_type
        dummy_regform.require_login = True
        set_feature_enabled(dummy_regform.event, 'registration', True)
        response = test_client.open(
            f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/', method=method
        )
        assert response.status_code == 200
        assert b'id="regform-passcode"' in response.data
        assert dummy_regform.title.encode() in response.data
        assert b'id="registration-form-submission-container"' not in response.data
        assert not dummy_regform.registrations

    def test_existing_registration_is_accessible(self, dummy_reg, test_client):
        dummy_reg.registration_form.require_login = True
        set_feature_enabled(dummy_reg.registration_form.event, 'registration', True)
        response = test_client.get(
            f'/event/{dummy_reg.event_id}/registrations/{dummy_reg.registration_form_id}/',
            query_string={'token': str(dummy_reg.uuid)},
        )
        assert response.status_code == 200
        assert b'Your registration has been completed' in response.data

    @pytest.mark.parametrize(('permission', 'bypass'), (
        (None, False),
        ('registration', True),
        ('registration_edit', False),
        ('registration_checkin', False),
        ('registration_moderation', False),
        ('full_access', True),
    ))
    def test_registration_management_bypass(self, dummy_regform, dummy_user, test_client, permission, bypass):
        dummy_regform.require_login = True
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
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
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
        dummy_regform.private = private
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        query = {'form_token': str(dummy_regform.uuid)} if private else {}
        response = test_client.get(url, query_string=query)
        assert b'id="regform-passcode"' in response.data
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        assert csrf_token != '00000000-0000-0000-0000-000000000000'
        assert csrf_token.encode() in response.data

        response = test_client.post(url + 'passcode', query_string=query, data={'csrf_token': csrf_token})
        assert response.status_code == 303
        assert response.location == url + (f'?form_token={dummy_regform.uuid}' if private else '')

        response = test_client.get(response.location)
        assert response.status_code == 200
        assert b'id="registration-form-submission-container"' in response.data
        assert b'id="regform-passcode"' not in response.data

        dummy_regform.require_captcha = False
        response = test_client.post(url, query_string=query, headers={'X-CSRF-Token': csrf_token}, json={
            'email': dummy_user.email, 'first_name': dummy_user.first_name, 'last_name': dummy_user.last_name,
        })
        assert response.status_code == 200
        assert 'redirect' in response.json
        assert len(dummy_regform.registrations) == 1

    @pytest.mark.usefixtures('logged_in_user')
    @pytest.mark.parametrize('csrf_token', (None, '00000000-0000-0000-0000-000000000000'))
    def test_unlock_requires_csrf(self, dummy_regform, test_client, csrf_token):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)

        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token} if csrf_token else {})
        assert response.status_code == 400
        response = test_client.get(url)
        assert b'id="regform-passcode"' in response.data

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_is_scoped_and_expires(self, dummy_regform, create_regform, test_client, freeze_time):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
        other_regform = create_regform(dummy_regform.event, start_dt=dummy_regform.start_dt, require_login=True)
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        test_client.get(url)
        with test_client.session_transaction() as sess:
            csrf_token = sess['_csrf_token']
        response = test_client.post(url + 'passcode', data={'csrf_token': csrf_token})
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

        freeze_time(now_utc() + timedelta(hours=2))
        assert b'id="regform-passcode"' in test_client.get(url).data

    def test_anonymous_user_must_log_in(self, dummy_regform, test_client):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
        url = f'/event/{dummy_regform.event_id}/registrations/{dummy_regform.id}/'
        response = test_client.get(url)
        assert response.status_code == 200
        assert b'Log in to proceed' in response.data
        assert b'id="regform-passcode"' not in response.data
        assert b'id="registration-form-submission-container"' not in response.data

        response = test_client.post(url + 'passcode', data={
            'csrf_token': '00000000-0000-0000-0000-000000000000',
        })
        assert response.status_code == 302
        assert '/login/' in response.location
        assert b'id="regform-passcode"' not in response.data
        with test_client.session_transaction() as sess:
            assert 'plugin_regform_passcode_grants' not in sess

    @pytest.mark.usefixtures('logged_in_user')
    def test_unlock_requires_matching_event(self, dummy_regform, create_event, test_client):
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.require_login = True
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
        set_feature_enabled(dummy_regform.event, 'registration', True)
        dummy_regform.start_dt = now_utc() - timedelta(days=1)
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
        set_feature_enabled(dummy_regform.event, 'registration', True)
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
        regform.require_login = True
        set_feature_enabled(regform.event, 'registration', True)
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
