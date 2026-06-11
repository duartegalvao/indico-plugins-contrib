# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

# Access-control tests for the management endpoints. They lock in that the
# regform-scoped endpoints are reachable by registration-form managers (not only
# admins) while still rejecting authenticated users without management rights.
# Access is checked before argument parsing, so a manager sending an empty body
# gets 422 (reached the handler) and a non-manager gets 403.

pytest_plugins = 'indico.modules.events.registration.testing.fixtures'


def _login(test_client, user):
    with test_client.session_transaction() as sess:
        sess.set_session_user(user)


def _regform_url(regform, endpoint):
    return f'/admin/plugins/affiliation_extras/events/{regform.event.id}/regforms/{regform.id}/{endpoint}'


def _catalog_create_url(prefix):
    return f'{prefix}/manage/affiliations/api/affiliations/catalogs'


def test_regform_affiliations_denies_non_manager(test_client, db, create_user, dummy_regform):
    _login(test_client, create_user(123))
    resp = test_client.get(_regform_url(dummy_regform, 'affiliations'))
    assert resp.status_code == 403


def test_regform_affiliations_allows_manager(test_client, db, dummy_user, dummy_regform):
    dummy_regform.event.update_principal(dummy_user, full_access=True)
    _login(test_client, dummy_user)
    resp = test_client.get(_regform_url(dummy_regform, 'affiliations'))
    assert resp.status_code == 200


def test_user_count_denies_non_manager(test_client, db, create_user, dummy_regform, no_csrf_check):
    _login(test_client, create_user(123))
    resp = test_client.post(_regform_url(dummy_regform, 'affiliation-user-count'), json={})
    assert resp.status_code == 403


def test_user_count_allows_manager(test_client, db, dummy_user, dummy_regform, no_csrf_check):
    dummy_regform.event.update_principal(dummy_user, full_access=True)
    _login(test_client, dummy_user)
    resp = test_client.post(_regform_url(dummy_regform, 'affiliation-user-count'), json={})
    assert resp.status_code == 200
    assert resp.json == {'count': 0}


def test_invite_denies_non_manager(test_client, db, create_user, dummy_regform, no_csrf_check):
    _login(test_client, create_user(123))
    resp = test_client.post(_regform_url(dummy_regform, 'invite'), json={})
    assert resp.status_code == 403


def test_invite_allows_manager(test_client, db, dummy_user, dummy_regform, no_csrf_check):
    dummy_regform.event.update_principal(dummy_user, full_access=True)
    _login(test_client, dummy_user)
    resp = test_client.post(_regform_url(dummy_regform, 'invite'), json={})
    assert resp.status_code == 422


def test_event_catalog_create_denies_non_manager(test_client, db, create_user, dummy_event, no_csrf_check):
    _login(test_client, create_user(123))
    resp = test_client.post(_catalog_create_url(f'/event/{dummy_event.id}'), json={})
    assert resp.status_code == 403


def test_event_catalog_create_allows_manager(test_client, db, dummy_user, dummy_event, no_csrf_check):
    dummy_event.update_principal(dummy_user, full_access=True)
    _login(test_client, dummy_user)
    resp = test_client.post(_catalog_create_url(f'/event/{dummy_event.id}'), json={})
    assert resp.status_code == 422


def test_category_catalog_create_denies_non_manager(test_client, db, create_user, dummy_category, no_csrf_check):
    _login(test_client, create_user(123))
    resp = test_client.post(_catalog_create_url(f'/category/{dummy_category.id}'), json={})
    assert resp.status_code == 403


def test_category_catalog_create_allows_manager(test_client, db, dummy_user, dummy_category, no_csrf_check):
    dummy_category.update_principal(dummy_user, full_access=True)
    _login(test_client, dummy_user)
    resp = test_client.post(_catalog_create_url(f'/category/{dummy_category.id}'), json={})
    assert resp.status_code == 422
