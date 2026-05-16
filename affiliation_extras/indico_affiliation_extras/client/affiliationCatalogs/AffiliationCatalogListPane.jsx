// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import cloneCatalogURL from 'indico-url:plugin_affiliation_extras.api_clone_catalog';
import deleteCatalogURL from 'indico-url:plugin_affiliation_extras.api_delete_catalog';
import toggleDefaultCatalogURL from 'indico-url:plugin_affiliation_extras.api_toggle_default_catalog';
import catalogDetailURL from 'indico-url:plugin_affiliation_extras.catalog_detail';
import catalogListURL from 'indico-url:plugin_affiliation_extras.manage_affiliations';
import catalogNewURL from 'indico-url:plugin_affiliation_extras.create_catalog';

import PropTypes from 'prop-types';
import React from 'react';
import {Icon} from 'semantic-ui-react';

import {Param, Translate} from 'indico/react/i18n';
import {handleAxiosError, indicoAxios} from 'indico/utils/axios';

import CatalogListPane from '../components/CatalogListPane';

export default function AffiliationCatalogListPane({
  ownCatalogs,
  inheritedCatalogs,
  targetLocator,
  dispatch,
  defaultCatalogId,
  explicitDefaultCatalogId,
}) {
  const cloneCatalog = async catalog => {
    const {data: clonedCatalog} = await indicoAxios.post(
      cloneCatalogURL({catalog_id: catalog.id, ...targetLocator})
    );
    dispatch({type: 'ADD_CATALOG', catalog: clonedCatalog});
  };

  const deleteCatalog = async catalog => {
    await indicoAxios.delete(deleteCatalogURL({catalog_id: catalog.id, ...targetLocator}));
    dispatch({type: 'DELETE_CATALOG', id: catalog.id});
  };

  const toggleDefaultCatalog = async (catalog, evt) => {
    evt.target.dispatchEvent(new Event('indico:closeAutoTooltip'));
    try {
      const {data} = await indicoAxios.post(
        toggleDefaultCatalogURL({catalog_id: catalog.id, ...targetLocator})
      );
      dispatch({
        type: 'SET_DEFAULT_CATALOG',
        defaultCatalogId: data.default_catalog_id,
        explicitDefaultCatalogId: data.explicit_default_catalog_id,
      });
    } catch (err) {
      handleAxiosError(err);
    }
  };

  const renderOwner = catalog => {
    if (!catalog.owner) {
      return null;
    }
    return 'event_id' in catalog.owner.locator ? (
      <Translate>
        from event{' '}
        <Param
          name="title"
          value={catalog.owner.title}
          wrapper={<a href={catalogListURL(catalog.owner.locator)} />}
        />
      </Translate>
    ) : (
      <Translate>
        from category{' '}
        <Param
          name="title"
          value={catalog.owner.title}
          wrapper={<a href={catalogListURL(catalog.owner.locator)} />}
        />
      </Translate>
    );
  };

  const renderDefaultAction = catalog => {
    const isDefault = catalog.id === defaultCatalogId;
    const isInheritedDefault = isDefault && catalog.id !== explicitDefaultCatalogId;
    const defaultTitle = isInheritedDefault
      ? Translate.string('This is the inherited default catalog')
      : isDefault
        ? Translate.string('Clear default catalog')
        : Translate.string('Set as default catalog');

    return (
      <Icon
        name="pin"
        color={isDefault ? 'yellow' : undefined}
        title={defaultTitle}
        disabled={isInheritedDefault}
        onClick={evt => toggleDefaultCatalog(catalog, evt)}
      />
    );
  };

  const sections = [
    ...(inheritedCatalogs.length
      ? [
          {
            key: 'inherited',
            catalogs: inheritedCatalogs,
            title: Translate.string('Inherited catalogs'),
            noItemsMessage: '',
            detailURL: catalog => catalogListURL(catalog.owner.locator),
            editLabel: Translate.string('Edit catalog'),
            cloneLabel: Translate.string('Clone catalog'),
            deleteLabel: Translate.string('Delete catalog'),
            canEditCatalog: () => false,
            canDeleteCatalog: () => false,
            renderDescription: renderOwner,
            renderExtraActions: renderDefaultAction,
            onCloneCatalog: cloneCatalog,
          },
        ]
      : []),
    {
      key: 'own',
      catalogs: ownCatalogs,
      title: Translate.string('Catalogs'),
      newURL: () => catalogNewURL(targetLocator),
      detailURL: catalog => catalogDetailURL({catalog_id: catalog.id, ...targetLocator}),
      addLabel: Translate.string('Add new catalog'),
      noItemsMessage: Translate.string('No catalogs'),
      editLabel: Translate.string('Edit catalog'),
      cloneLabel: Translate.string('Clone catalog'),
      deleteLabel: Translate.string('Delete catalog'),
      renderExtraActions: renderDefaultAction,
      onCloneCatalog: cloneCatalog,
      onDeleteCatalog: deleteCatalog,
    },
  ];

  return (
    <CatalogListPane
      sections={sections}
      deleteConfirmText={catalog => (
        <Translate>
          Are you sure you want to delete the catalog{' '}
          <Param name="name" value={catalog.name} wrapper={<strong />} />?
        </Translate>
      )}
    />
  );
}

AffiliationCatalogListPane.propTypes = {
  ownCatalogs: PropTypes.array.isRequired,
  inheritedCatalogs: PropTypes.array.isRequired,
  targetLocator: PropTypes.object.isRequired,
  dispatch: PropTypes.func.isRequired,
  defaultCatalogId: PropTypes.number,
  explicitDefaultCatalogId: PropTypes.number,
};

AffiliationCatalogListPane.defaultProps = {
  defaultCatalogId: null,
  explicitDefaultCatalogId: null,
};
