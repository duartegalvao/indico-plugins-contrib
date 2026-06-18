// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import _ from 'lodash';
import PropTypes from 'prop-types';
import React from 'react';
import {DndProvider} from 'react-dnd';
import {Form as FinalForm} from 'react-final-form';
import {HTML5Backend} from 'react-dnd-html5-backend';
import {Form, Segment} from 'semantic-ui-react';

import {ManagementPageSubTitle} from 'indico/react/components';
import {FinalCheckbox, FinalInput, FinalSubmitButton} from 'indico/react/forms';
import {Translate} from 'indico/react/i18n';

import FinalRoleList from '../components/RoleListField';

import '../components/CatalogDetailPane.module.scss';

const DEFAULT_ROLE = {
  id: null,
  code: '',
  name: '',
  position: 1,
};

export default function RoleCatalogDetailPane({catalog, isNew, onSubmit}) {
  const isCreate = isNew === true;
  const initialValues = {
    name: catalog?.name || '',
    allow_other_role: catalog?.allow_other_role || false,
    roles: catalog?.roles?.length
      ? _.sortBy(catalog.roles, 'position').map(role => ({
          id: role.id,
          code: role.code,
          name: role.name,
          position: role.position,
        }))
      : [DEFAULT_ROLE],
  };

  if (!catalog && !isCreate) {
    return (
      <Segment placeholder>
        <Translate>Role catalog not found</Translate>
      </Segment>
    );
  }

  const handleSubmit = async formData =>
    onSubmit({
      name: formData.name.trim(),
      allow_other_role: formData.allow_other_role,
      roles: formData.roles.map(role => ({
        id: role.id,
        code: role.code.trim(),
        name: role.name.trim(),
        position: role.position,
      })),
    });

  return (
    <div styleName="catalog-detail">
      <ManagementPageSubTitle
        title={isCreate ? Translate.string('New role catalog') : catalog.name}
      />
      <DndProvider backend={HTML5Backend}>
        <FinalForm
          onSubmit={handleSubmit}
          initialValues={initialValues}
          initialValuesEqual={_.isEqual}
          subscription={{}}
        >
          {fprops => (
            <Form onSubmit={fprops.handleSubmit}>
              <section>
                <h3>
                  <Translate>Name</Translate>
                </h3>
                <FinalInput
                  name="name"
                  required
                  placeholder={Translate.string('Enter a name for the role catalog')}
                  validate={value =>
                    value && value.trim()
                      ? undefined
                      : Translate.string('Role catalog name is required.')
                  }
                />
              </section>
              <section>
                <h3>
                  <Translate>Roles</Translate>
                </h3>
                <FinalCheckbox
                  name="allow_other_role"
                  label={Translate.string('Allow participants to specify another role')}
                />
                <FinalRoleList name="roles" required />
              </section>
              <div styleName="form-actions">
                <FinalSubmitButton label={Translate.string('Save changes')} disabledUntilChange />
              </div>
            </Form>
          )}
        </FinalForm>
      </DndProvider>
    </div>
  );
}

RoleCatalogDetailPane.propTypes = {
  catalog: PropTypes.object,
  isNew: PropTypes.bool,
  onSubmit: PropTypes.func.isRequired,
};

RoleCatalogDetailPane.defaultProps = {
  catalog: null,
  isNew: false,
};
