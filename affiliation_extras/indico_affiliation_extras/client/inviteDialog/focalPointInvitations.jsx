// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import focalPointInviteMetadataURL from 'indico-url:plugin_affiliation_extras.api_focal_point_invite_metadata';
import inviteFocalPointsURL from 'indico-url:plugin_affiliation_extras.api_invite_focal_points';

import React, {useEffect} from 'react';
import {useForm} from 'react-final-form';
import {Icon, Loader, Message} from 'semantic-ui-react';

import {FinalCheckbox} from 'indico/react/forms';
import {useIndicoAxios} from 'indico/react/hooks';
import {Param, Plural, PluralTranslate, Singular, Translate} from 'indico/react/i18n';

import ContactListRecipientFields from '../components/ContactListRecipientFields';

const mockContactListOptions = [
  'Primary contacts',
  'Administrative contacts',
  'Technical contacts',
];

const AffiliationCatalogField = ({eventId, regformId}) => {
  const form = useForm();
  const {data, loading} = useIndicoAxios(
    focalPointInviteMetadataURL({event_id: eventId, reg_form_id: regformId}),
    {camelize: true}
  );

  useEffect(() => {
    if (data) {
      form.change('focal_points', data);
    }
  }, [data, form]);

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
      {mockContactListOptions.length > 0 ? (
        <ContactListRecipientFields
          contactListOptions={data.affiliationCount ? mockContactListOptions : []}
          allowNoContactLists
        />
      ) : (
        <FinalCheckbox
          name="include_unnamed_lists"
          label={Translate.string('Invite contacts')}
          description={Translate.string('Invite contacts from unnamed contact lists.')}
          disabled={!data.affiliationCount}
        />
      )}
    </>
  );
};

const focalPointInvitations = {
  key: 'focal_points',
  buttonLabel: Translate.string('Affiliation Catalog'),
  Component: AffiliationCatalogField,
  extraFields: ['focal_points'],
  initialValues: {
    focal_points: {focalPointCount: 0, affiliationCount: 0},
    include_focal_points: true,
    contact_lists: [],
    include_unnamed_lists: true,
  },
  getCount: ({focal_points: focalPoints, include_focal_points: includeFocalPoints}) =>
    includeFocalPoints ? (focalPoints?.focalPointCount ?? 0) : 0,
  getSubmitURL: ({eventId, regformId}) =>
    inviteFocalPointsURL({event_id: eventId, reg_form_id: regformId}),
};

export default focalPointInvitations;
