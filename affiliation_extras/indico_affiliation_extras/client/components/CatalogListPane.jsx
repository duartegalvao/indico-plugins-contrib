// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import _ from 'lodash';
import PropTypes from 'prop-types';
import React, {useState} from 'react';
import {Link} from 'react-router-dom';
import {Button, Icon} from 'semantic-ui-react';

import {RequestConfirmDelete} from 'indico/react/components';
import {Param, Translate} from 'indico/react/i18n';
import {handleAxiosError} from 'indico/utils/axios';

import './CatalogListPane.module.scss';

function CatalogRow({
  catalog,
  detailURL,
  editLabel,
  cloneLabel,
  deleteLabel,
  canEdit,
  canDelete,
  renderDescription,
  renderExtraActions,
  onCloneCatalog,
  onDeleteCatalog,
  setDeletePrompt,
}) {
  const cloneCatalog = async evt => {
    evt.target.dispatchEvent(new Event('indico:closeAutoTooltip'));
    try {
      await onCloneCatalog(catalog);
    } catch (err) {
      handleAxiosError(err);
    }
  };

  const deleteCatalog = async () => {
    try {
      await onDeleteCatalog(catalog);
    } catch (err) {
      handleAxiosError(err);
      return true;
    }
  };

  const openDeletePrompt = evt => {
    evt.target.dispatchEvent(new Event('indico:closeAutoTooltip'));
    setDeletePrompt({catalog, func: deleteCatalog});
  };

  return (
    <tr>
      <td>{canEdit ? <Link to={detailURL(catalog)}>{catalog.name}</Link> : catalog.name}</td>
      {renderDescription && <td className="text-superfluous">{renderDescription(catalog)}</td>}
      <td styleName="catalog-actions">
        <div className="thin toolbar right">
          {renderExtraActions?.(catalog)}
          {canEdit && (
            <Link to={detailURL(catalog)}>
              <Icon name="edit" color="blue" title={editLabel} />
            </Link>
          )}
          {onCloneCatalog && (
            <Icon name="clone" color="blue" title={cloneLabel} onClick={cloneCatalog} />
          )}
          {canDelete && (
            <Icon name="trash" color="red" title={deleteLabel} onClick={openDeletePrompt} />
          )}
        </div>
      </td>
    </tr>
  );
}

CatalogRow.propTypes = {
  catalog: PropTypes.object.isRequired,
  detailURL: PropTypes.func.isRequired,
  editLabel: PropTypes.string.isRequired,
  cloneLabel: PropTypes.string.isRequired,
  deleteLabel: PropTypes.string.isRequired,
  canEdit: PropTypes.bool,
  canDelete: PropTypes.bool,
  renderDescription: PropTypes.func,
  renderExtraActions: PropTypes.func,
  onCloneCatalog: PropTypes.func,
  onDeleteCatalog: PropTypes.func,
  setDeletePrompt: PropTypes.func.isRequired,
};

CatalogRow.defaultProps = {
  canEdit: true,
  canDelete: true,
  renderDescription: null,
  renderExtraActions: null,
  onCloneCatalog: null,
  onDeleteCatalog: null,
};

function CatalogSection({
  catalogs,
  newURL,
  detailURL,
  title,
  addLabel,
  noItemsMessage,
  editLabel,
  cloneLabel,
  deleteLabel,
  canEditCatalog,
  canDeleteCatalog,
  renderDescription,
  renderExtraActions,
  onCloneCatalog,
  onDeleteCatalog,
  setDeletePrompt,
}) {
  return (
    <section>
      <div className="flexrow f-a-center f-j-space-between">
        <h3>{title}</h3>
        {newURL && addLabel && (
          <Button
            as={Link}
            to={newURL()}
            icon="plus"
            content={addLabel}
            className="mini primary icon"
          />
        )}
      </div>
      {catalogs.length ? (
        <table className="i-table-widget">
          <tbody>
            {_.sortBy(catalogs, 'name').map(catalog => (
              <CatalogRow
                key={catalog.id}
                catalog={catalog}
                detailURL={detailURL}
                editLabel={editLabel}
                cloneLabel={cloneLabel}
                deleteLabel={deleteLabel}
                canEdit={canEditCatalog(catalog)}
                canDelete={canDeleteCatalog(catalog)}
                renderDescription={renderDescription}
                renderExtraActions={renderExtraActions}
                onCloneCatalog={onCloneCatalog}
                onDeleteCatalog={onDeleteCatalog}
                setDeletePrompt={setDeletePrompt}
              />
            ))}
          </tbody>
        </table>
      ) : (
        <div className="italic text-not-important">{noItemsMessage}</div>
      )}
    </section>
  );
}

CatalogSection.propTypes = {
  catalogs: PropTypes.array.isRequired,
  newURL: PropTypes.func,
  detailURL: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  addLabel: PropTypes.string,
  noItemsMessage: PropTypes.string.isRequired,
  editLabel: PropTypes.string.isRequired,
  cloneLabel: PropTypes.string.isRequired,
  deleteLabel: PropTypes.string.isRequired,
  canEditCatalog: PropTypes.func,
  canDeleteCatalog: PropTypes.func,
  renderDescription: PropTypes.func,
  renderExtraActions: PropTypes.func,
  onCloneCatalog: PropTypes.func,
  onDeleteCatalog: PropTypes.func,
  setDeletePrompt: PropTypes.func.isRequired,
};

CatalogSection.defaultProps = {
  newURL: null,
  addLabel: null,
  canEditCatalog: () => true,
  canDeleteCatalog: () => true,
  renderDescription: null,
  renderExtraActions: null,
  onCloneCatalog: null,
  onDeleteCatalog: null,
};

export default function CatalogListPane({sections, deleteConfirmText}) {
  const [deletePrompt, setDeletePrompt] = useState(null);

  return (
    <div styleName="catalog-list">
      <RequestConfirmDelete
        onClose={() => setDeletePrompt(null)}
        requestFunc={deletePrompt?.func || (() => null)}
        open={deletePrompt !== null}
      >
        {deletePrompt?.catalog ? (
          deleteConfirmText(deletePrompt.catalog)
        ) : (
          <Translate>
            Are you sure you want to delete the catalog{' '}
            <Param name="name" value="" wrapper={<strong />} />?
          </Translate>
        )}
      </RequestConfirmDelete>
      {sections.map((section, idx) => (
        <CatalogSection key={section.key ?? idx} setDeletePrompt={setDeletePrompt} {...section} />
      ))}
    </div>
  );
}

CatalogListPane.propTypes = {
  sections: PropTypes.arrayOf(PropTypes.object).isRequired,
  deleteConfirmText: PropTypes.func.isRequired,
};
