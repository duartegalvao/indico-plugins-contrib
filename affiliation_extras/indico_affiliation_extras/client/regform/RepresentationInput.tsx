// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import searchAffiliationsURL from 'indico-url:plugin_affiliation_extras.search_registration_affiliation';
import searchAffiliationsManagementURL from 'indico-url:plugin_affiliation_extras.search_registration_affiliation_management';
import manageAffiliationsURL from 'indico-url:plugin_affiliation_extras.manage_affiliations';

import React from 'react';
import {Dropdown, Form, Message} from 'semantic-ui-react';
import {useSelector} from 'react-redux';

import {AffiliationField} from 'indico/react/components';
import {FinalCheckbox, FinalField} from 'indico/react/forms';
import {Param, Translate} from 'indico/react/i18n';
import {getStaticData} from 'indico/modules/events/registration/form/selectors';

import RadioGroup from '../components/RadioGroup';
import './RepresentationInput.module.scss';

type RepresentationType = {
  id: number;
  name: string;
  affiliations?: Array<{id: number; name: string}>;
  roles?: RoleValue[];
};
type AffiliationValue = {id: number | null; text: string};
type RoleValue = {id: number | null; name: string};
type StaticData = {
  eventId: number;
  regformId: number;
  management?: boolean;
};
type RepresentationValue = {
  representationId: number | null;
  representationName: string;
  affiliation: AffiliationValue;
  role?: RoleValue;
};

const EMPTY_AFFILIATION: AffiliationValue = {id: null, text: ''};
const EMPTY_ROLE: RoleValue = {id: null, name: ''};
const EMPTY_VALUE: RepresentationValue = {
  representationId: null,
  representationName: '',
  affiliation: EMPTY_AFFILIATION,
  role: EMPTY_ROLE,
};

type RepresentationInputComponentProps = {
  id: string;
  value?: RepresentationValue | null;
  onChange: (value: RepresentationValue) => void;
  disabled: boolean;
  isRequired: boolean;
  requireRole: boolean;
  representationTypes: RepresentationType[];
  getSearchAffiliationURL: (params: {q: string; affiliationListId: number}) => string;
};

function RepresentationInputComponent({
  id,
  value,
  onChange,
  disabled,
  isRequired,
  requireRole,
  representationTypes,
  getSearchAffiliationURL,
}: RepresentationInputComponentProps) {
  const normalizedValue = value ?? EMPTY_VALUE;
  const representationId = normalizedValue.representationId;
  const selectedRepresentation =
    representationTypes.find(item => item.id === representationId) ?? null;
  const representationOptions = representationTypes.map(item => ({
    value: item.id,
    text: item.name,
  }));
  const preloadedAffiliationOptions = (selectedRepresentation?.affiliations || []).map(
    affiliation => ({
      key: affiliation.id,
      value: affiliation.id,
      text: affiliation.name,
    })
  );
  if (
    normalizedValue.affiliation.id !== null &&
    normalizedValue.affiliation.text &&
    !preloadedAffiliationOptions.some(option => option.value === normalizedValue.affiliation.id)
  ) {
    preloadedAffiliationOptions.unshift({
      key: normalizedValue.affiliation.id,
      value: normalizedValue.affiliation.id,
      text: normalizedValue.affiliation.text,
    });
  }
  const usePreloadedAffiliations = preloadedAffiliationOptions.length > 0;
  const roleOptions = selectedRepresentation?.roles || [];
  const roleValue = normalizedValue.role ?? EMPTY_ROLE;
  const isRoleRequired = requireRole && roleOptions.length > 0;
  const radioRoleOptions = roleOptions.map(role => ({
    value: role.id!,
    label: role.name,
  }));

  const handleRepresentationChange = (_: unknown, {value: selectedValue}: {value?: unknown}) => {
    const nextRepresentationId = typeof selectedValue === 'number' ? selectedValue : null;
    const selectedRepresentation = representationTypes.find(
      item => item.id === nextRepresentationId
    );
    onChange({
      representationId: nextRepresentationId,
      representationName: selectedRepresentation?.name ?? '',
      affiliation: EMPTY_AFFILIATION,
      role: EMPTY_ROLE,
    });
  };

  const handleAffiliationChange = (nextAffiliation: AffiliationValue) => {
    onChange({
      ...normalizedValue,
      affiliation: nextAffiliation ?? EMPTY_AFFILIATION,
    });
  };

  const handleRoleChange = (nextRoleId: string | number | null) => {
    const nextRole =
      typeof nextRoleId === 'number'
        ? (roleOptions.find(role => role.id === nextRoleId) ?? EMPTY_ROLE)
        : EMPTY_ROLE;
    onChange({
      ...normalizedValue,
      role: nextRole,
    });
  };

  return (
    <>
      <Form.Field required={isRequired}>
        <Dropdown
          id={`${id}-representation-type`}
          styleName="representation-field"
          options={representationOptions}
          search
          selection
          fluid
          required={isRequired}
          disabled={disabled}
          clearable={!isRequired}
          placeholder={Translate.string('Select a representation type')}
          value={representationId}
          onChange={handleRepresentationChange}
        />
      </Form.Field>
      {!!selectedRepresentation && (
        <Form.Field required={isRequired}>
          <label htmlFor={`${id}-affiliation`}>{selectedRepresentation.name}</label>
          <AffiliationField
            id={`${id}-affiliation`}
            styleName="representation-field"
            value={normalizedValue.affiliation}
            onChange={handleAffiliationChange}
            allowCustomAffiliations={false}
            currentAffiliation={null}
            includeMeta={false}
            searchAffiliationURL={({q}) =>
              getSearchAffiliationURL({q, affiliationListId: selectedRepresentation.id})
            }
            // These props intentionally pass through AffiliationField to ComboDropdown.
            {...(usePreloadedAffiliations
              ? {
                  options: preloadedAffiliationOptions,
                  search: true,
                  onSearchChange: () => {},
                }
              : {})}
            disabled={disabled}
          />
        </Form.Field>
      )}
      {!!selectedRepresentation && roleOptions.length > 0 && (
        <RadioGroup
          id={`${id}-role`}
          value={roleValue.id}
          onChange={handleRoleChange}
          disabled={disabled}
          required={isRoleRequired}
          label={Translate.string('Role')}
          noneLabel={Translate.string('None', 'Choice')}
          options={radioRoleOptions}
        />
      )}
    </>
  );
}

type RepresentationInputProps = {
  fieldId: number;
  htmlId: string;
  htmlName: string;
  disabled?: boolean;
  isRequired: boolean;
  requireRole?: boolean;
  representationTypes?: RepresentationType[];
  searchContext?: Record<string, unknown>;
};

export function RepresentationSettings() {
  const {eventId} = useSelector(getStaticData) as StaticData;
  const catalogsURL = manageAffiliationsURL({event_id: eventId});

  return (
    <>
      <Message info>
        <Translate>
          Representation types are configured in the{' '}
          <Param name="url" wrapper={<a href={catalogsURL} />}>
            affiliation catalogs settings
          </Param>
          .
        </Translate>
      </Message>
      <FinalCheckbox
        name="requireRole"
        label={Translate.string('Require a role (if available)')}
        value={undefined}
      />
    </>
  );
}

export default function RepresentationInput({
  fieldId,
  htmlId,
  htmlName,
  disabled = false,
  isRequired,
  requireRole = false,
  representationTypes = [],
  searchContext = {},
}: RepresentationInputProps) {
  const {eventId, regformId, management} = useSelector(getStaticData) as StaticData;
  const searchURL = management ? searchAffiliationsManagementURL : searchAffiliationsURL;

  return (
    <FinalField
      id={htmlId}
      name={htmlName}
      component={RepresentationInputComponent}
      undefinedValue={EMPTY_VALUE}
      disabled={disabled}
      isRequired={isRequired}
      requireRole={requireRole}
      representationTypes={representationTypes}
      getSearchAffiliationURL={({q, affiliationListId}: {q: string; affiliationListId: number}) =>
        searchURL({
          event_id: eventId,
          reg_form_id: regformId,
          field_id: fieldId,
          affiliation_list_id: affiliationListId,
          q,
          ...searchContext,
        })
      }
    />
  );
}
