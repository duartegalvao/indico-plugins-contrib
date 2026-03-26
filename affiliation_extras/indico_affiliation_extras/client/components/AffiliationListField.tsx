// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import groupsURL from 'indico-url:plugin_affiliation_extras.api_affiliation_groups';
import tagsURL from 'indico-url:plugin_affiliation_extras.api_affiliation_tags';
import userCountURL from 'indico-url:plugin_affiliation_extras.api_affiliation_user_count';

import _ from 'lodash';
import React, {useEffect, useMemo, useState} from 'react';
import {Button, Dropdown, Icon, Label, List, Segment} from 'semantic-ui-react';

import {FinalField, validators} from 'indico/react/forms';
import {useIndicoAxios} from 'indico/react/hooks';
import {Translate} from 'indico/react/i18n';
import {indicoAxios} from 'indico/utils/axios';

import {Affiliation} from 'indico/modules/users/affiliations/types';

import {GroupInfo, TagInfo} from '../types';
import {getAffiliationSubheader} from '../util';
import AddItemsModal from './AddItemsModal';

export interface AffiliationListValue {
  groups: GroupInfo[];
  tags: TagInfo[];
  affiliations: Affiliation[];
  _userCount?: number | null;
}

function AffiliationListField({
  value,
  onChange,
  onFocus,
  onBlur,
  disabled = false,
  showInviteCount = false,
  userCountURL: affiliationCountURL,
  renderItemExtra,
}: {
  value: AffiliationListValue;
  onChange: (value: AffiliationListValue) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  disabled?: boolean;
  showInviteCount?: boolean;
  userCountURL?: string;
  renderItemExtra?: (item: Affiliation) => React.ReactNode;
}) {
  const {data: groups} = useIndicoAxios(groupsURL({}));
  const {data: tags} = useIndicoAxios(tagsURL({}));
  const [affiliationModalOpen, setAffiliationModalOpen] = useState(false);

  /** Notify React Final Form that this field has been interacted with. */
  const markTouched = () => {
    onFocus?.();
    onBlur?.();
  };

  const usedGroupIds = useMemo(() => new Set(value.groups.map(g => g.id)), [value.groups]);
  const usedTagIds = useMemo(() => new Set(value.tags.map(t => t.id)), [value.tags]);

  const groupOptions = useMemo(
    () =>
      (groups || [])
        .filter(g => !usedGroupIds.has(g.id))
        .map(g => ({value: g.id, text: `${g.code}: ${g.name}`})),
    [groups, usedGroupIds]
  );
  const tagOptions = useMemo(
    () =>
      (tags || [])
        .filter(t => !usedTagIds.has(t.id))
        .map(t => ({value: t.id, text: `${t.code}: ${t.name}`, color: t.color})),
    [tags, usedTagIds]
  );

  // Stable string keys derived from the current selection IDs.  Used as useEffect
  // dependencies so the count fetch only re-fires when the actual selection changes,
  // not when _userCount itself changes (which would cause an infinite loop).
  const affiliationKey = value.affiliations
    .map(a => a.id)
    .sort()
    .join(',');
  const groupKey = value.groups
    .map(g => g.id)
    .sort()
    .join(',');
  const tagKey = value.tags
    .map(t => t.id)
    .sort()
    .join(',');

  /**
   * When `showInviteCount` is true, fetch the deduplicated user count from the
   * backend whenever the selection changes, and store the result in `_userCount`
   * so that the parent's synchronous `getCount` callback can read it.
   */
  useEffect(() => {
    if (!showInviteCount) {
      return;
    }
    const hasSelection = value.affiliations.length || value.groups.length || value.tags.length;
    if (!hasSelection) {
      if (value._userCount != null) {
        onChange({...value, _userCount: null});
      }
      return;
    }
    let cancelled = false;
    indicoAxios
      .post(userCountURL({}), {
        affiliation_ids: value.affiliations.map(a => a.id),
        group_ids: value.groups.map(g => g.id),
        tag_ids: value.tags.map(t => t.id),
      })
      .then(({data}) => {
        if (!cancelled) {
          onChange({...value, _userCount: data.count});
        }
      })
      .catch(() => {
      if (!cancelled) {
        onChange({...value, _userCount: null});
      }
    });

    return () => {
      cancelled = true;
    };
  }, [affiliationKey, groupKey, tagKey, showInviteCount]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddGroup = (groupId: number) => {
    const group = (groups || []).find(g => g.id === groupId);
    if (!group) {
      return;
    }
    onChange({...value, groups: [...value.groups, group]});
    markTouched();
  };
  const handleAddTag = (tagId: number) => {
    const tag = (tags || []).find(t => t.id === tagId);
    if (!tag) {
      return;
    }
    onChange({...value, tags: [...value.tags, tag]});
    markTouched();
  };

  const handleDeleteGroup = (groupId: number) => {
    onChange({...value, groups: value.groups.filter(g => g.id !== groupId)});
    markTouched();
  };
  const handleDeleteTag = (tagId: number) => {
    onChange({...value, tags: value.tags.filter(t => t.id !== tagId)});
    markTouched();
  };
  const handleDeleteAffiliation = (affiliationId: number) => {
    onChange({...value, affiliations: value.affiliations.filter(a => a.id !== affiliationId)});
    markTouched();
  };

  const entries = [
    ...value.groups.map(group => ({
      key: `group-${group.id}`,
      title: group.code,
      description: group.name,
      onDelete: () => handleDeleteGroup(group.id),
    })),
    ...value.tags.map(tag => ({
      key: `tag-${tag.id}`,
      title: <Label size="tiny" color={tag.color} content={tag.code} />,
      description: tag.name,
      onDelete: () => handleDeleteTag(tag.id),
    })),
    ...value.affiliations.map(affiliation => ({
      key: `affiliation-${affiliation.id}`,
      title: affiliation.name,
      description: getAffiliationSubheader(affiliation),
      onDelete: () => handleDeleteAffiliation(affiliation.id),
    })),
  ];

  return (
    <>
      <Segment attached="top">
        {entries.length > 0 ? (
          <List divided relaxed>
            {entries.map(entry => (
              <List.Item key={entry.key}>
                <List.Content floated="right">
                  <Icon
                    name="close"
                    link
                    color="grey"
                    disabled={disabled}
                    onClick={() => !disabled && entry.onDelete()}
                  />
                </List.Content>
                <List.Content>
                  <List.Header>{entry.title}</List.Header>
                  {entry.description && <List.Description>{entry.description}</List.Description>}
                </List.Content>
              </List.Item>
            ))}
          </List>
        ) : (
          <Translate>This list is currently empty</Translate>
        )}
      </Segment>
      <Button.Group attached="bottom">
        <Button icon="add" as="div" disabled />
        <AddDropdown
          text={Translate.string('Group')}
          options={groupOptions}
          disabled={disabled || groupOptions.length === 0}
          onChange={handleAddGroup}
        />
        <AddDropdown
          text={Translate.string('Tag')}
          options={tagOptions}
          disabled={disabled || tagOptions.length === 0}
          onChange={handleAddTag}
        />
        <Button
          type="button"
          disabled={disabled}
          onClick={() => setAffiliationModalOpen(true)}
          content={Translate.string('Affiliation')}
        />
      </Button.Group>
      <AddItemsModal
        open={affiliationModalOpen}
        onClose={() => setAffiliationModalOpen(false)}
        onConfirm={(list: Affiliation[]) => {
          onChange({...value, affiliations: list});
          markTouched();
        }}
        savedSelection={value.affiliations}
        userCountURL={affiliationCountURL}
        renderItemExtra={renderItemExtra}
      />
    </>
  );
}

function AddDropdown({text, options, disabled, onChange}) {
  return (
    <Dropdown
      text={text}
      button
      upward
      floating
      scrolling
      disabled={disabled}
      options={options}
      openOnFocus={false}
      selectOnBlur={false}
      selectOnNavigation={false}
      value={null}
      onChange={(e, data) => onChange(data.value)}
    />
  );
}

/** Wraps `AffiliationListField` as a React Final Form field with optional required validation. */
export default function FinalAffiliationList({name, ...rest}) {
  const {required, validate, ...otherProps} = rest;
  const validateMembers = (value: AffiliationListValue) => {
    if (_.every(value, _.isEmpty)) {
      return Translate.string('This field is required.');
    }
  };
  const finalValidate =
    required && required !== 'no-validator'
      ? validate
        ? validators.chain(validateMembers, validate)
        : validateMembers
      : validate;
  return (
    <FinalField
      name={name}
      component={AffiliationListField}
      isEqual={(a, b) => _.isEqual(a, b)}
      required={required ? 'no-validator' : false}
      validate={finalValidate}
      {...otherProps}
    />
  );
}
