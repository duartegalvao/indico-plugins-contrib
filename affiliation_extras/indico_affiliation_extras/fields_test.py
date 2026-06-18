# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

import pytest
from marshmallow import ValidationError

from indico.modules.events.registration.models.form_fields import RegistrationFormField
from indico.modules.events.registration.models.registrations import RegistrationData
from indico.modules.users.models.affiliations import Affiliation

from indico_affiliation_extras.fields import (
    REPRESENTATION_AFFILIATION_PRELOAD_LIMIT,
    RepresentationField,
    iter_representation_reglist_items,
)
from indico_affiliation_extras.models.catalogs import AffiliationCatalog
from indico_affiliation_extras.models.lists import AffiliationList
from indico_affiliation_extras.models.roles import AffiliationRole, RoleCatalog
from indico_affiliation_extras.settings import event_settings


pytest_plugins = 'indico.modules.events.registration.testing.fixtures'


def _login(test_client, user):
    with test_client.session_transaction() as sess:
        sess.set_session_user(user)


def _create_role_catalog(db, *, name='Roles', allow_other_role=False):
    catalog = RoleCatalog(name=name, allow_other_role=allow_other_role)
    db.session.add(catalog)
    db.session.flush()
    return catalog


def _create_role(db, catalog, *, code='role', name='Role', position=1):
    role = AffiliationRole(catalog=catalog, code=code, name=name, position=position)
    db.session.add(role)
    db.session.flush()
    return role


def _create_affiliation_list(
    db,
    event,
    *,
    name='Representatives',
    is_enabled=True,
    affiliations=(),
    role_catalog=None,
):
    catalog = AffiliationCatalog(name='Catalog', event=event)
    db.session.add(catalog)
    db.session.flush()
    affiliation_list = AffiliationList(
        catalog=catalog, name=name, position=1, is_enabled=is_enabled, role_catalog=role_catalog
    )
    affiliation_list.affiliations.update(affiliations)
    db.session.add(affiliation_list)
    db.session.flush()
    event_settings.set(event, 'default_catalog_id', catalog.id)
    return affiliation_list


def _create_representation_field(db, regform, *, title='Representation'):
    field = RegistrationFormField(
        input_type=RepresentationField.name,
        title=title,
        parent=regform.sections[0],
        registration_form=regform,
    )
    field.data = {}
    field.versioned_data = {}
    db.session.add(field)
    db.session.flush()
    return field


@pytest.fixture
def representation_field(dummy_regform):
    field = RegistrationFormField(
        input_type=RepresentationField.name,
        title='Representation',
        parent=dummy_regform.sections[0],
        registration_form=dummy_regform,
    )
    field.versioned_data = {}
    return field


def test_representation_field_validates_required_representation_and_affiliation(representation_field):
    representation_field.is_required = True
    validator = representation_field.field_impl.get_validators(None)
    with pytest.raises(ValidationError, match='Please select a representation type'):
        validator({'representation_id': None, 'affiliation': {'id': None, 'text': ''}})
    with pytest.raises(ValidationError, match='Please select an affiliation from the list'):
        validator({'representation_id': 1, 'affiliation': {'id': None, 'text': ''}})


def test_representation_field_rejects_custom_affiliation(representation_field):
    validator = representation_field.field_impl.get_validators(None)
    with pytest.raises(ValidationError, match='Please select an affiliation from the list'):
        validator({'representation_id': 1, 'affiliation': {'id': None, 'text': 'CERN'}})


def test_representation_field_rejects_invalid_affiliation_list(db, representation_field, dummy_reg):
    with pytest.raises(ValidationError, match='Invalid representation type'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {'representation_id': 999999, 'affiliation': {'id': None, 'text': ''}},
        )


def test_representation_field_rejects_affiliation_not_in_affiliation_list(db, representation_field, dummy_reg):
    allowed = Affiliation(name='Allowed')
    forbidden = Affiliation(name='Forbidden')
    db.session.add_all([allowed, forbidden])
    db.session.flush()
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        affiliations={allowed},
    )

    with pytest.raises(ValidationError, match='Invalid affiliation'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {'representation_id': affiliation_list.id, 'affiliation': {'id': forbidden.id, 'text': forbidden.name}},
        )


def test_representation_field_canonicalizes_and_snapshots_value(db, representation_field, dummy_reg):
    affiliation = Affiliation(name='CERN')
    db.session.add(affiliation)
    db.session.flush()
    role_catalog = _create_role_catalog(db)
    role = _create_role(db, role_catalog, code='chair', name='Chair')
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        name='Delegates',
        affiliations={affiliation},
        role_catalog=role_catalog,
    )

    rv = representation_field.field_impl.process_form_data(
        dummy_reg,
        {
            'representation_id': affiliation_list.id,
            'representation_name': '',
            'affiliation': {'id': affiliation.id, 'text': 'Wrong name'},
            'role': {'id': role.id, 'name': 'Wrong role'},
        },
    )

    assert rv['data'] == {
        'representation_id': affiliation_list.id,
        'representation_name': 'Delegates',
        'affiliation': {'id': affiliation.id, 'text': 'CERN'},
        'role': {'id': role.id, 'name': 'Chair'},
    }


def test_representation_field_rejects_role_not_in_selected_representation_type(db, representation_field, dummy_reg):
    role_catalog = _create_role_catalog(db, name='Allowed roles')
    other_role_catalog = _create_role_catalog(db, name='Other roles')
    other_role = _create_role(db, other_role_catalog, code='observer', name='Observer')
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        role_catalog=role_catalog,
    )

    with pytest.raises(ValidationError, match='Invalid role'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {
                'representation_id': affiliation_list.id,
                'affiliation': {'id': None, 'text': ''},
                'role': {'id': other_role.id, 'name': other_role.name},
            },
        )


def test_representation_field_requires_role_if_configured_and_available(db, representation_field, dummy_reg):
    representation_field.data = {'require_role': True}
    role_catalog = _create_role_catalog(db)
    _create_role(db, role_catalog, code='chair', name='Chair')
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        role_catalog=role_catalog,
    )

    with pytest.raises(ValidationError, match='Please select a role'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {
                'representation_id': affiliation_list.id,
                'affiliation': {'id': None, 'text': ''},
                'role': {'id': None, 'name': ''},
            },
        )


def test_representation_field_accepts_empty_role_when_not_required(db, representation_field, dummy_reg):
    role_catalog = _create_role_catalog(db)
    _create_role(db, role_catalog, code='chair', name='Chair')
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        name='Delegates',
        role_catalog=role_catalog,
    )

    rv = representation_field.field_impl.process_form_data(
        dummy_reg,
        {
            'representation_id': affiliation_list.id,
            'affiliation': {'id': None, 'text': ''},
            'role': {'id': None, 'name': ''},
        },
    )

    assert rv['data'] == {
        'representation_id': affiliation_list.id,
        'representation_name': 'Delegates',
        'affiliation': {'id': None, 'text': ''},
    }


def test_representation_field_keeps_unchanged_value_when_list_disabled(db, representation_field, dummy_reg):
    affiliation = Affiliation(name='CERN')
    db.session.add(affiliation)
    db.session.flush()
    affiliation_list = _create_affiliation_list(
        db, representation_field.registration_form.event, name='Delegates', affiliations={affiliation}
    )
    stored = {
        'representation_id': affiliation_list.id,
        'representation_name': 'Delegates',
        'affiliation': {'id': affiliation.id, 'text': 'CERN'},
    }
    old_data = RegistrationData(registration=dummy_reg, field_data=representation_field.current_data, data=stored)
    db.session.flush()
    # The list is disabled after submission; re-saving the registration (e.g. editing an
    # unrelated field) must not re-validate the unchanged value against the live config.
    affiliation_list.is_enabled = False
    db.session.flush()

    rv = representation_field.field_impl.process_form_data(dummy_reg, dict(stored), old_data=old_data)

    assert rv == {}


def test_representation_field_accepts_other_role_when_catalog_allows_it(db, representation_field, dummy_reg):
    role_catalog = _create_role_catalog(db, allow_other_role=True)
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        name='Delegates',
        role_catalog=role_catalog,
    )

    rv = representation_field.field_impl.process_form_data(
        dummy_reg,
        {
            'representation_id': affiliation_list.id,
            'affiliation': {'id': None, 'text': ''},
            'role': {'id': None, 'name': 'Beamline coordinator'},
        },
    )

    assert rv['data'] == {
        'representation_id': affiliation_list.id,
        'representation_name': 'Delegates',
        'affiliation': {'id': None, 'text': ''},
        'role': {'id': None, 'name': 'Beamline coordinator'},
    }


def test_representation_field_accepts_required_other_role_when_catalog_allows_it(db, representation_field, dummy_reg):
    representation_field.data = {'require_role': True}
    affiliation = Affiliation(name='CERN')
    db.session.add(affiliation)
    db.session.flush()
    role_catalog = _create_role_catalog(db, allow_other_role=True)
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        name='Delegates',
        affiliations={affiliation},
        role_catalog=role_catalog,
    )

    validator = representation_field.field_impl.get_validators(None)
    value = {
        'representation_id': affiliation_list.id,
        'affiliation': {'id': affiliation.id, 'text': affiliation.name},
        'role': {'id': None, 'name': 'Beamline coordinator'},
    }

    validator(value)
    rv = representation_field.field_impl.process_form_data(dummy_reg, value)

    assert rv['data']['role'] == {'id': None, 'name': 'Beamline coordinator'}


def test_representation_field_rejects_other_role_when_catalog_disallows_it(db, representation_field, dummy_reg):
    role_catalog = _create_role_catalog(db)
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        role_catalog=role_catalog,
    )

    with pytest.raises(ValidationError, match='Invalid role'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {
                'representation_id': affiliation_list.id,
                'affiliation': {'id': None, 'text': ''},
                'role': {'id': None, 'name': 'Beamline coordinator'},
            },
        )


def test_representation_field_requires_other_role_title_when_selected(db, representation_field, dummy_reg):
    role_catalog = _create_role_catalog(db, allow_other_role=True)
    affiliation_list = _create_affiliation_list(
        db,
        representation_field.registration_form.event,
        role_catalog=role_catalog,
    )

    with pytest.raises(ValidationError, match='Please enter a role'):
        representation_field.field_impl.process_form_data(
            dummy_reg,
            {
                'representation_id': affiliation_list.id,
                'affiliation': {'id': None, 'text': ''},
                'role': {'id': None, 'name': '   '},
            },
        )


def test_representation_field_renders_summary_and_reglist_data(representation_field):
    registration_data = RegistrationData(
        field_data=representation_field.current_data,
        data={
            'representation_id': 1,
            'representation_name': 'Delegates',
            'affiliation': {'id': 2, 'text': 'CERN'},
            'role': {'id': 3, 'name': 'Chair'},
        },
    )

    summary = representation_field.field_impl.render_summary_data(registration_data)
    reglist_column = representation_field.field_impl.render_reglist_column(registration_data)

    assert summary == 'Delegates - CERN - Chair'
    assert reglist_column.content == 'Delegates - CERN - Chair'
    assert reglist_column.text_value == 'Delegates - CERN - Chair'


def test_representation_field_adds_split_reglist_columns(db, dummy_regform, dummy_reg):
    field = _create_representation_field(db, dummy_regform)
    other_field = _create_representation_field(db, dummy_regform, title='Alternate representation')
    dummy_reg.data.append(
        RegistrationData(
            field_data=field.current_data,
            data={
                'representation_id': 1,
                'representation_name': 'Delegates',
                'affiliation': {'id': 2, 'text': 'CERN'},
                'role': {'id': 3, 'name': 'Chair'},
            },
        )
    )
    db.session.flush()

    item_classes = {item.name: item for item in iter_representation_reglist_items(dummy_regform)}
    type_item = item_classes[f'affiliation_extras_representation_{field.id}_type'](dummy_regform.event, dummy_regform)
    affiliation_item = item_classes[f'affiliation_extras_representation_{field.id}_affiliation'](
        dummy_regform.event, dummy_regform
    )
    role_item = item_classes[f'affiliation_extras_representation_{field.id}_role'](dummy_regform.event, dummy_regform)

    assert list(item_classes) == [
        f'affiliation_extras_representation_{field.id}_type',
        f'affiliation_extras_representation_{field.id}_affiliation',
        f'affiliation_extras_representation_{field.id}_role',
        f'affiliation_extras_representation_{other_field.id}_type',
        f'affiliation_extras_representation_{other_field.id}_affiliation',
        f'affiliation_extras_representation_{other_field.id}_role',
    ]
    assert type_item.title == 'Representation: Type'
    assert affiliation_item.title == 'Representation: Affiliation'
    assert role_item.title == 'Representation: Role'
    assert type_item.load_data([dummy_reg])[dummy_reg].content == 'Delegates'
    assert affiliation_item.load_data([dummy_reg])[dummy_reg].content == 'CERN'
    assert role_item.load_data([dummy_reg])[dummy_reg].content == 'Chair'


def test_representation_field_view_data_preloads_small_affiliation_list(db, dummy_regform):
    field = _create_representation_field(db, dummy_regform)
    affiliations = {Affiliation(name=f'Affiliation {i:02d}') for i in range(REPRESENTATION_AFFILIATION_PRELOAD_LIMIT)}
    db.session.add_all(affiliations)
    db.session.flush()
    _create_affiliation_list(db, dummy_regform.event, affiliations=affiliations)

    [representation_type] = field.view_data['representationTypes']
    assert [item['name'] for item in representation_type['affiliations']] == [
        f'Affiliation {i:02d}' for i in range(REPRESENTATION_AFFILIATION_PRELOAD_LIMIT)
    ]


def test_representation_field_view_data_does_not_preload_large_affiliation_list(db, dummy_regform):
    field = _create_representation_field(db, dummy_regform)
    affiliations = {
        Affiliation(name=f'Affiliation {i:02d}') for i in range(REPRESENTATION_AFFILIATION_PRELOAD_LIMIT + 1)
    }
    db.session.add_all(affiliations)
    db.session.flush()
    _create_affiliation_list(db, dummy_regform.event, affiliations=affiliations)

    [representation_type] = field.view_data['representationTypes']
    assert 'affiliations' not in representation_type


def test_representation_field_view_data_includes_roles(db, dummy_regform):
    field = _create_representation_field(db, dummy_regform)
    role_catalog = _create_role_catalog(db)
    _create_role(db, role_catalog, code='observer', name='Observer', position=2)
    _create_role(db, role_catalog, code='chair', name='Chair', position=1)
    _create_affiliation_list(db, dummy_regform.event, role_catalog=role_catalog)

    [representation_type] = field.view_data['representationTypes']

    assert representation_type['roles'] == [
        {'id': role.id, 'name': role.name} for role in sorted(role_catalog.roles, key=lambda role: role.position)
    ]


def test_representation_field_view_data_includes_other_role_setting(db, dummy_regform):
    field = _create_representation_field(db, dummy_regform)
    role_catalog = _create_role_catalog(db, allow_other_role=True)
    _create_affiliation_list(db, dummy_regform.event, role_catalog=role_catalog)

    [representation_type] = field.view_data['representationTypes']

    assert representation_type['allowOtherRole'] is True


def test_search_keeps_server_side_search_for_non_empty_queries(test_client, db, dummy_regform):
    field = _create_representation_field(db, dummy_regform)
    allowed = Affiliation(name='CERN Allowed')
    blocked = Affiliation(name='CERN Blocked')
    db.session.add_all([allowed, blocked])
    db.session.flush()
    affiliation_list = _create_affiliation_list(db, dummy_regform.event, affiliations={allowed})

    resp = test_client.get(
        f'/event/{dummy_regform.event.id}/affiliation-extras/registration/{dummy_regform.id}/'
        f'affiliations/{field.id}/list/{affiliation_list.id}?q=CERN'
    )

    assert resp.status_code == 200
    assert [item['name'] for item in resp.json] == ['CERN Allowed']


def test_search_rejects_affiliation_list_from_other_event(test_client, db, dummy_regform, create_event):
    field = _create_representation_field(db, dummy_regform)
    other_affiliation_list = _create_affiliation_list(db, create_event())

    resp = test_client.get(
        f'/event/{dummy_regform.event.id}/affiliation-extras/registration/{dummy_regform.id}/'
        f'affiliations/{field.id}/list/{other_affiliation_list.id}?q=CERN'
    )

    assert resp.status_code == 404


def test_management_search_allows_private_regform_for_managers(test_client, db, dummy_user, dummy_regform):
    dummy_regform.private = True
    dummy_regform.event.update_principal(dummy_user, full_access=True)
    field = _create_representation_field(db, dummy_regform)
    affiliation_list = _create_affiliation_list(db, dummy_regform.event)
    _login(test_client, dummy_user)

    resp = test_client.get(
        f'/event/{dummy_regform.event.id}/manage/affiliation-extras/registration/{dummy_regform.id}/'
        f'affiliations/{field.id}/list/{affiliation_list.id}?q=test'
    )

    assert resp.status_code == 200
