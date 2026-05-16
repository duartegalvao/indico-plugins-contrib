// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import cloneRoleCatalogAPIURL from 'indico-url:plugin_affiliation_extras.api_clone_role_catalog';
import roleCatalogAPIURL from 'indico-url:plugin_affiliation_extras.api_role_catalog';
import roleCatalogsAPIURL from 'indico-url:plugin_affiliation_extras.api_role_catalogs';
import roleCatalogNewURL from 'indico-url:plugin_affiliation_extras.create_role_catalog';
import roleCatalogDetailURL from 'indico-url:plugin_affiliation_extras.role_catalog_detail';
import roleCatalogListURL from 'indico-url:plugin_affiliation_extras.manage_role_catalogs';

import PropTypes from 'prop-types';
import React, {useEffect, useReducer} from 'react';
import {useHistory} from 'react-router';
import {BrowserRouter as Router, Route, Switch} from 'react-router-dom';
import {Message} from 'semantic-ui-react';

import {ManagementPageBackButton} from 'indico/react/components';
import {handleSubmitError} from 'indico/react/forms';
import {Param, Translate} from 'indico/react/i18n';
import {routerPathFromFlask, useNumericParam} from 'indico/react/util/routing';
import {indicoAxios} from 'indico/utils/axios';

import CatalogListPane from '../components/CatalogListPane';

import RoleCatalogDetailPane from './RoleCatalogDetailPane';

function reducer(state, action) {
  switch (action.type) {
    case 'ADD_CATALOG':
      return {
        ...state,
        catalogs: [...state.catalogs, action.catalog],
        message: Translate.string('Role catalog "{name}" was added', {
          name: action.catalog.name,
        }),
      };
    case 'UPDATE_CATALOG':
      return {
        ...state,
        catalogs: state.catalogs.map(catalog =>
          catalog.id === action.catalog.id ? action.catalog : catalog
        ),
        message: Translate.string('Role catalog "{name}" was updated', {
          name: action.catalog.name,
        }),
      };
    case 'DELETE_CATALOG':
      return {
        ...state,
        catalogs: state.catalogs.filter(catalog => catalog.id !== action.id),
        message: Translate.string('Role catalog deleted'),
      };
    case 'RESET_MESSAGE':
      return {
        ...state,
        message: null,
      };
    default:
      return state;
  }
}

function RoleCatalogEditRoute({catalogs, dispatch}) {
  const catalogId = useNumericParam('role_catalog_id');
  const catalog = catalogs.find(item => item.id === catalogId);

  const saveCatalog = async payload => {
    try {
      const {data: updatedCatalog} = await indicoAxios.patch(
        roleCatalogAPIURL({role_catalog_id: catalogId}),
        payload
      );
      dispatch({type: 'UPDATE_CATALOG', catalog: updatedCatalog});
    } catch (err) {
      return handleSubmitError(err);
    }
  };

  return (
    <>
      <ManagementPageBackButton url={roleCatalogListURL()} />
      <RoleCatalogDetailPane catalog={catalog} onSubmit={saveCatalog} />
    </>
  );
}

function RoleCatalogCreateRoute({dispatch}) {
  const history = useHistory();

  const createCatalog = async payload => {
    try {
      const {data: createdCatalog} = await indicoAxios.post(roleCatalogsAPIURL(), payload);
      dispatch({type: 'ADD_CATALOG', catalog: createdCatalog});
      history.push(roleCatalogListURL());
    } catch (err) {
      return handleSubmitError(err);
    }
  };

  return (
    <>
      <ManagementPageBackButton url={roleCatalogListURL()} />
      <RoleCatalogDetailPane catalog={null} isNew onSubmit={createCatalog} />
    </>
  );
}

export default function RoleCatalogManagement({initialCatalogs}) {
  const [state, dispatch] = useReducer(reducer, {catalogs: initialCatalogs, message: null});

  useEffect(() => {
    if (state.message) {
      setTimeout(() => dispatch({type: 'RESET_MESSAGE'}), 2500);
    }
  }, [state.message]);

  const cloneCatalog = async catalog => {
    const {data: clonedCatalog} = await indicoAxios.post(
      cloneRoleCatalogAPIURL({role_catalog_id: catalog.id})
    );
    dispatch({type: 'ADD_CATALOG', catalog: clonedCatalog});
  };

  const deleteCatalog = async catalog => {
    await indicoAxios.delete(roleCatalogAPIURL({role_catalog_id: catalog.id}));
    dispatch({type: 'DELETE_CATALOG', id: catalog.id});
  };

  return (
    <>
      {state.message && (
        <Message success>
          <Message.Content>{state.message}</Message.Content>
        </Message>
      )}
      <Router>
        <Switch>
          <Route
            exact
            path={routerPathFromFlask(roleCatalogNewURL, [])}
            render={() => <RoleCatalogCreateRoute dispatch={dispatch} />}
          />
          <Route
            exact
            path={routerPathFromFlask(roleCatalogDetailURL, ['role_catalog_id'])}
            render={() => <RoleCatalogEditRoute catalogs={state.catalogs} dispatch={dispatch} />}
          />
          <Route
            exact
            path={routerPathFromFlask(roleCatalogListURL, [])}
            render={() => (
              <CatalogListPane
                sections={[
                  {
                    key: 'role-catalogs',
                    catalogs: state.catalogs,
                    newURL: roleCatalogNewURL,
                    detailURL: catalog => roleCatalogDetailURL({role_catalog_id: catalog.id}),
                    title: Translate.string('Role catalogs'),
                    addLabel: Translate.string('Add new role catalog'),
                    noItemsMessage: Translate.string('No role catalogs'),
                    editLabel: Translate.string('Edit role catalog'),
                    cloneLabel: Translate.string('Clone role catalog'),
                    deleteLabel: Translate.string('Delete role catalog'),
                    onCloneCatalog: cloneCatalog,
                    onDeleteCatalog: deleteCatalog,
                  },
                ]}
                deleteConfirmText={catalog => (
                  <Translate>
                    Are you sure you want to delete the role catalog{' '}
                    <Param name="name" value={catalog.name} wrapper={<strong />} />?
                  </Translate>
                )}
              />
            )}
          />
        </Switch>
      </Router>
    </>
  );
}

RoleCatalogEditRoute.propTypes = {
  catalogs: PropTypes.array.isRequired,
  dispatch: PropTypes.func.isRequired,
};

RoleCatalogCreateRoute.propTypes = {
  dispatch: PropTypes.func.isRequired,
};

RoleCatalogManagement.propTypes = {
  initialCatalogs: PropTypes.array.isRequired,
};
