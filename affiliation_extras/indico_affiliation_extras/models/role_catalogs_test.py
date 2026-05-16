# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

import pytest

from indico_affiliation_extras.models.roles import Role, RoleCatalog


def _login(test_client, user):
    with test_client.session_transaction() as sess:
        sess.set_session_user(user)


def _role_catalog_payload(name='Catalog', roles=None):
    return {
        'name': name,
        'roles': roles
        or [
            {'id': None, 'code': 'chair', 'name': 'Chair', 'position': 1},
            {'id': None, 'code': 'delegate', 'name': 'Delegate', 'position': 2},
        ],
    }


def _create_role_catalog(db, *, name='Catalog'):
    catalog = RoleCatalog(name=name)
    catalog.roles = [
        Role(code='chair', name='Chair', position=1),
        Role(code='delegate', name='Delegate', position=2),
    ]
    db.session.add(catalog)
    db.session.flush()
    return catalog


@pytest.fixture
def admin_user(create_user):
    return create_user(42, admin=True)


def test_role_catalog_admin_page_renders_initial_catalogs(test_client, db, admin_user):
    catalog = _create_role_catalog(db, name='Conference roles')
    _login(test_client, admin_user)

    resp = test_client.get('/admin/affiliation-role-catalogs/')

    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert 'affiliation-role-catalogs' in data
    assert 'setupRoleCatalogs' in data
    assert catalog.name in data


@pytest.mark.usefixtures('no_csrf_check')
def test_role_catalog_api_crud_and_clone(test_client, db, admin_user):
    _login(test_client, admin_user)

    create_resp = test_client.post(
        '/api/admin/plugins/affiliation_extras/role-catalogs',
        json=_role_catalog_payload(name='Conference roles'),
    )
    assert create_resp.status_code == 201
    created = create_resp.json
    assert created['name'] == 'Conference roles'
    assert [role['code'] for role in created['roles']] == ['chair', 'delegate']

    roles = created['roles']
    edit_resp = test_client.patch(
        f'/api/admin/plugins/affiliation_extras/role-catalogs/{created["id"]}',
        json=_role_catalog_payload(
            name='Updated roles',
            roles=[
                {'id': roles[1]['id'], 'code': 'delegate', 'name': 'Lead delegate', 'position': 1},
                {'id': None, 'code': 'speaker', 'name': 'Speaker', 'position': 2},
            ],
        ),
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json['name'] == 'Updated roles'
    assert [(role['code'], role['name']) for role in edit_resp.json['roles']] == [
        ('delegate', 'Lead delegate'),
        ('speaker', 'Speaker'),
    ]

    list_resp = test_client.get('/api/admin/plugins/affiliation_extras/role-catalogs')
    assert list_resp.status_code == 200
    assert [catalog['name'] for catalog in list_resp.json] == ['Updated roles']

    clone_resp = test_client.post(f'/api/admin/plugins/affiliation_extras/role-catalogs/{created["id"]}/clone')
    assert clone_resp.status_code == 200
    assert clone_resp.json['name'] == 'Updated roles (1)'
    assert [(role['code'], role['name']) for role in clone_resp.json['roles']] == [
        ('delegate', 'Lead delegate'),
        ('speaker', 'Speaker'),
    ]

    delete_resp = test_client.delete(f'/api/admin/plugins/affiliation_extras/role-catalogs/{created["id"]}')
    assert delete_resp.status_code == 204
    assert RoleCatalog.get(created['id']) is None


@pytest.mark.usefixtures('no_csrf_check')
def test_role_catalog_api_rejects_duplicate_role_codes(test_client, admin_user):
    _login(test_client, admin_user)

    resp = test_client.post(
        '/api/admin/plugins/affiliation_extras/role-catalogs',
        json=_role_catalog_payload(
            roles=[
                {'id': None, 'code': 'chair', 'name': 'Chair', 'position': 1},
                {'id': None, 'code': 'CHAIR', 'name': 'Other chair', 'position': 2},
            ],
        ),
    )

    assert resp.status_code == 422
    assert 'Role codes must be unique within a catalog' in resp.get_data(as_text=True)


@pytest.mark.usefixtures('no_csrf_check')
def test_role_catalog_api_rejects_role_from_other_catalog(test_client, db, admin_user):
    catalog = _create_role_catalog(db, name='Catalog')
    other_catalog = _create_role_catalog(db, name='Other catalog')
    foreign_role = other_catalog.roles[0]
    _login(test_client, admin_user)

    resp = test_client.patch(
        f'/api/admin/plugins/affiliation_extras/role-catalogs/{catalog.id}',
        json=_role_catalog_payload(
            roles=[
                {'id': foreign_role.id, 'code': 'foreign', 'name': 'Foreign', 'position': 1},
            ],
        ),
    )

    assert resp.status_code == 422
    assert 'Role does not belong to this catalog' in resp.get_data(as_text=True)
