// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import affiliationCatalogInviteMetadataURL from 'indico-url:plugin_affiliation_extras.api_affiliation_catalog_invite_metadata';
import affiliationCatalogInviteRecipientCountURL from 'indico-url:plugin_affiliation_extras.api_affiliation_catalog_invite_recipient_count';
import inviteAffiliationCatalogURL from 'indico-url:plugin_affiliation_extras.api_invite_affiliation_catalog';

import PropTypes from 'prop-types';
import React, {useEffect, useMemo} from 'react';
import {useForm, useFormState} from 'react-final-form';
import {Icon, Loader, Message} from 'semantic-ui-react';

import {FinalCheckbox} from 'indico/react/forms';
import {useIndicoAxios} from 'indico/react/hooks';
import {Param, Plural, PluralTranslate, Singular, Translate} from 'indico/react/i18n';

import ContactListRecipientFields from '../components/ContactListRecipientFields';

const AffiliationCatalogFields = ({eventId, regformId}) => {
  const form = useForm();
  const {
    values: {
      include_focal_points: includeFocalPoints = false,
      contact_lists: contactLists = [],
      include_unnamed_lists: includeUnnamedLists = false,
    },
  } = useFormState({subscription: {values: true}});
  const {data, loading} = useIndicoAxios(
    affiliationCatalogInviteMetadataURL({event_id: eventId, reg_form_id: regformId}),
    {camelize: true}
  );
  const recipientCountConfig = useMemo(
    () => ({
      url: affiliationCatalogInviteRecipientCountURL({
        event_id: eventId,
        reg_form_id: regformId,
      }),
      method: 'POST',
      data: {
        include_focal_points: includeFocalPoints,
        contact_lists: contactLists,
        include_unnamed_lists: includeUnnamedLists,
      },
    }),
    [contactLists, eventId, includeFocalPoints, includeUnnamedLists, regformId]
  );
  const {
    data: recipientCountData,
    error: recipientCountError,
    loading: recipientCountLoading,
  } = useIndicoAxios(recipientCountConfig, {camelize: true});
  const hasUnnamedContactLists = data?.hasUnnamedContactLists;

  useEffect(() => {
    form.change('affiliation_catalog_recipient_count', 0);
  }, [form, recipientCountConfig]);

  useEffect(() => {
    if (!recipientCountLoading && !recipientCountError && recipientCountData) {
      form.change('affiliation_catalog_recipient_count', recipientCountData.recipientCount);
    }
  }, [form, recipientCountData, recipientCountError, recipientCountLoading]);

  useEffect(() => {
    if (hasUnnamedContactLists === false && includeUnnamedLists) {
      form.change('include_unnamed_lists', false);
    }
  }, [form, hasUnnamedContactLists, includeUnnamedLists]);

  if (loading || !data) {
    return <Loader active inline="centered" />;
  }

  return (
    <>
      {data.affiliationCount ? (
        <Message info icon>
          <Icon name="building outline" />
          <Message.Content>
            <PluralTranslate as={Message.Header} count={data.affiliationCount}>
              <Singular>
                The event catalog contains <Param name="count" value={data.affiliationCount} />{' '}
                affiliation.
              </Singular>
              <Plural>
                The event catalog contains <Param name="count" value={data.affiliationCount} />{' '}
                affiliations.
              </Plural>
            </PluralTranslate>
            <Translate as="p">
              Select the affiliation contacts that should receive an invitation.
            </Translate>
            <Translate as="p">Existing invitations and registrations will be skipped.</Translate>
          </Message.Content>
        </Message>
      ) : (
        <Message error icon>
          <Icon name="warning sign" />
          <Message.Content>
            <Translate as={Message.Header}>No affiliations found</Translate>
            <Translate as="p">No affiliations were found in this event catalog.</Translate>
          </Message.Content>
        </Message>
      )}
      <FinalCheckbox
        name="include_focal_points"
        label={Translate.string('Invite focal points')}
        description={
          data.focalPointCount
            ? PluralTranslate.string(
                '{count} focal point from the catalog will be invited.',
                '{count} focal points from the catalog will be invited.',
                data.focalPointCount,
                {count: data.focalPointCount}
              )
            : Translate.string('No focal points were found in the event catalog.')
        }
        disabled={!data.focalPointCount}
      />
      {data.contactListOptions.length > 0 ? (
        <ContactListRecipientFields
          contactListOptions={data.affiliationCount ? data.contactListOptions : []}
          hasUnnamedContactLists={data.hasUnnamedContactLists}
          allowNoContactLists
        />
      ) : (
        <FinalCheckbox
          name="include_unnamed_lists"
          label={Translate.string('Invite contacts')}
          description={Translate.string('Invite contacts from unnamed contact lists.')}
          disabled={!data.affiliationCount || !data.hasUnnamedContactLists}
        />
      )}
    </>
  );
};

AffiliationCatalogFields.propTypes = {
  eventId: PropTypes.number.isRequired,
  regformId: PropTypes.number.isRequired,
};

const affiliationCatalogInvitations = {
  key: 'affiliation_catalog',
  buttonLabel: Translate.string('Affiliation Catalog'),
  Component: AffiliationCatalogFields,
  extraFields: ['include_focal_points', 'contact_lists', 'include_unnamed_lists'],
  initialValues: {
    affiliation_catalog_recipient_count: 0,
    include_focal_points: true,
    contact_lists: [],
    include_unnamed_lists: true,
  },
  getCount: ({affiliation_catalog_recipient_count: recipientCount}) => recipientCount,
  getSubmitURL: ({eventId, regformId}) =>
    inviteAffiliationCatalogURL({event_id: eventId, reg_form_id: regformId}),
};

export default affiliationCatalogInvitations;
