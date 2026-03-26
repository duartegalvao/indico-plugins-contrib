// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import groupsURL from 'indico-url:plugin_affiliation_extras.api_affiliation_groups';
import searchAffiliationsExtendedURL from 'indico-url:plugin_affiliation_extras.api_search_affiliations_extended';
import tagsURL from 'indico-url:plugin_affiliation_extras.api_affiliation_tags';

import React, {useEffect, useState} from 'react';
import {Button, Dropdown, Form, Grid, Icon, Input, Label, List, Loader, Modal} from 'semantic-ui-react';

import {Affiliation} from 'indico/modules/users/affiliations/types';
import {useIndicoAxios} from 'indico/react/hooks';
import {PluralTranslate, Singular, Plural, Param, Translate} from 'indico/react/i18n';
import {indicoAxios} from 'indico/utils/axios';

import {CountryDropdown} from 'indico/react/components';

import './AddItemsModal.module.scss';


interface AffiliationWithCount extends Affiliation {
  user_count?: number;
}

interface SearchFilters {
  q: string;
  groupIds: number[];
  tagIds: number[];
  countryCode: string;
}

interface ResultSectionProps {
  items: AffiliationWithCount[];
  isSelected: (item: AffiliationWithCount) => boolean;
  onToggle: (item: AffiliationWithCount) => void;
  renderItemExtra?: ((item: AffiliationWithCount) => React.ReactNode) | null;
}

interface AddItemsModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (selection: AffiliationWithCount[]) => void;
  savedSelection: AffiliationWithCount[];
  userCountURL?: string | null;
  renderItemExtra?: ((item: AffiliationWithCount) => React.ReactNode) | null;
}

/**
 * Fetches affiliations from the extended search API each time `filters` changes.
 */
function useAffiliationSearch(filters: SearchFilters | null) {
  const [results, setResults] = useState<AffiliationWithCount[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!filters) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    setIsLoading(true);
    indicoAxios
      .get<AffiliationWithCount[]>(searchAffiliationsExtendedURL({}), {
        params: {
          q: filters.q,
          group_ids: filters.groupIds,
          tag_ids: filters.tagIds,
          country_code: filters.countryCode,
        },
      })
      .then(({data}) => {
        setResults(data);
      })
      .catch(() => {
        setResults([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
    return () => controller.abort();
  }, [JSON.stringify(filters)]); // eslint-disable-line react-hooks/exhaustive-deps

  return {results, isLoading};
}

/**
 * Fetches per-affiliation user counts from the given URL whenever the IDs
 * change. Returns a map of `{ [id]: count }`, or `{}` when no URL is given.
 */
function useUserCounts(ids: number[], userCountURL: string | null | undefined) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const key = ids.join(',');

  useEffect(() => {
    if (!userCountURL || !ids.length) {
      setCounts({});
      return;
    }
    indicoAxios
      .post<Record<string, number>>(userCountURL, {affiliation_ids: ids})
      .then(({data}) => {
        setCounts(data);
      })
      .catch(() => {});
  }, [key, userCountURL]); // eslint-disable-line react-hooks/exhaustive-deps

  return counts;
}

/**
 * Manages the current item selection, keeping it in sync with `savedSelection`
 * each time the modal opens.
 */
function useSelectionState(savedSelection: AffiliationWithCount[], open: boolean) {
  const [selection, setSelection] = useState<AffiliationWithCount[]>(savedSelection);

  useEffect(() => {
    if (open) {
      setSelection(savedSelection);
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  return [selection, setSelection] as const;
}

function ResultSection({items, isSelected, onToggle, renderItemExtra = null}: ResultSectionProps) {
  return items.length > 0 ? (
    <List divided relaxed styleName="list">
      {items.map(item => (
        <List.Item key={item.id} styleName="result-item" onClick={() => onToggle(item)}>
          <div styleName="item">
            <div styleName="content">
              {item.name}
              {renderItemExtra && (
                <span styleName="item-count">{renderItemExtra(item)}</span>
              )}
            </div>
            <div styleName="item-actions">
              {isSelected(item) ? (
                <Icon name="checkmark" size="large" color="green" />
              ) : (
                <Icon styleName="button" name="add" size="large" />
              )}
            </div>
          </div>
        </List.Item>
      ))}
    </List>
  ) : (
    <p styleName="no-results">
      <Translate>No results.</Translate>
    </p>
  );
}

export default function AddItemsModal({
  open,
  onClose,
  onConfirm,
  savedSelection,
  userCountURL = null,
  renderItemExtra = null,
}: AddItemsModalProps) {
  const [searchInput, setSearchInput] = useState('');
  const [groupIds, setGroupIds] = useState<number[]>([]);
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [countryCode, setCountryCode] = useState('');
  const [activeFilters, setActiveFilters] = useState<SearchFilters | null>(null);

  const {results, isLoading} = useAffiliationSearch(activeFilters);
  const {data: groups} = useIndicoAxios(groupsURL({}), {manual: !open});
  const {data: tags} = useIndicoAxios(tagsURL({}), {manual: !open});

  const ids = results.map(a => a.id);
  const counts = useUserCounts(ids, userCountURL);
  const affiliations: AffiliationWithCount[] = userCountURL
    ? results.map(a => ({...a, user_count: counts[String(a.id)] ?? 0}))
    : results;
  const [selection, setSelection] = useSelectionState(savedSelection, open);

  const hasSearched = activeFilters !== null;
  const hasAnyInput = Boolean(searchInput || groupIds.length || tagIds.length || countryCode);
  const filtersUnchanged =
    activeFilters !== null &&
    activeFilters.q === searchInput &&
    activeFilters.countryCode === countryCode &&
    activeFilters.groupIds.length === groupIds.length &&
    activeFilters.groupIds.every((id, i) => id === groupIds[i]) &&
    activeFilters.tagIds.length === tagIds.length &&
    activeFilters.tagIds.every((id, i) => id === tagIds[i]);

  // Reset filter state when the modal closes.
  useEffect(() => {
    if (!open) {
      setActiveFilters(null);
      setSearchInput('');
      setGroupIds([]);
      setTagIds([]);
      setCountryCode('');
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (item: AffiliationWithCount) => {
    setSelection(prev =>
      prev.some(i => i.id === item.id) ? prev.filter(i => i.id !== item.id) : [...prev, item]
    );
  };

  const isSelected = (item: AffiliationWithCount) => selection.some(i => i.id === item.id);
  const savedIds = new Set(savedSelection.map(i => i.id));
  const newItems = selection.filter(i => !savedIds.has(i.id));
  const newAdditionsCount = newItems.length;
  const registrationsCount = newItems.reduce((acc, item) => acc + (item.user_count || 0), 0);
  const hasChanges =
    selection.some(i => !savedIds.has(i.id)) ||
    savedSelection.some(i => !selection.some(s => s.id === i.id));

  const applySearch = () => {
    setActiveFilters({q: searchInput, groupIds, tagIds, countryCode});
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (hasAnyInput && !filtersUnchanged) {
        applySearch();
      }
    }
  };

  const handleConfirm = () => {
    onConfirm(selection);
    onClose();
  };

  const handleCancel = () => {
    setSelection(savedSelection);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleCancel} size="large" closeIcon>
      <Modal.Header>
        <Translate>Add Affiliations</Translate>
      </Modal.Header>
      <Modal.Content scrolling>
        <Grid>
          <Grid.Column width={4}>
            <Form>
              <Form.Field>
                <label>
                  <Translate>Affiliation name</Translate>
                </label>
                <Input
                  value={searchInput}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setSearchInput(e.target.value)
                  }
                  onKeyDown={handleKeyDown}
                  placeholder={Translate.string('Affiliation name')}
                  autoFocus
                />
              </Form.Field>
              <Form.Field>
                <label>
                  <Translate>Groups</Translate>
                </label>
                <Dropdown
                  fluid
                  multiple
                  search
                  selection
                  value={groupIds}
                  options={(groups ?? []).map(group => ({
                    key: group.id,
                    value: group.id,
                    text: `${group.code}: ${group.name}`,
                  }))}
                  onChange={(_, {value}) => setGroupIds(value as number[])}
                  placeholder={Translate.string('Select groups...')}
                  loading={!groups}
                  disabled={!groups}
                />
              </Form.Field>
              <Form.Field>
                <label>
                  <Translate>Tags</Translate>
                </label>
                <Dropdown
                  fluid
                  multiple
                  search
                  selection
                  value={tagIds}
                  options={(tags ?? []).map(tag => ({
                    key: tag.id,
                    value: tag.id,
                    text: tag.name,
                    color: tag.color,
                    content: (
                      <>
                        <Label size="mini" color={tag.color} empty />
                        {' '}
                        {tag.name}
                      </>
                    ),
                  }))}
                  renderLabel={({color, text}) => ({color, content: text})}
                  onChange={(_, {value}) => setTagIds(value as number[])}
                  placeholder={Translate.string('Select tags...')}
                  loading={!tags}
                  disabled={!tags}
                />
              </Form.Field>
              <Form.Field>
                <label>
                  <Translate>Country</Translate>
                </label>
                <CountryDropdown value={countryCode} onChange={setCountryCode} fluid />
              </Form.Field>
              <Button
                type="button"
                icon="search"
                primary
                content={Translate.string('Search')}
                onClick={applySearch}
                loading={hasSearched && isLoading}
                disabled={!hasAnyInput || filtersUnchanged}
              />
            </Form>
          </Grid.Column>

          {!hasSearched ? (
            <Grid.Column width={12}>
              <Translate>Fill in the fields and click Search.</Translate>
            </Grid.Column>
          ) : isLoading ? (
            <Grid.Column width={12}>
              <Loader active inline="centered" />
            </Grid.Column>
          ) : (
            <Grid.Column width={12}>
              <ResultSection
                items={affiliations}
                isSelected={isSelected}
                onToggle={toggle}
                renderItemExtra={renderItemExtra}
              />
            </Grid.Column>
          )}
        </Grid>
      </Modal.Content>

      <Modal.Actions>
        <div styleName="actions">
          <span styleName="selected-count">
            {newAdditionsCount > 0 && (
              <>
                <PluralTranslate count={newAdditionsCount}>
                  <Singular>
                    <Param name="count" value={newAdditionsCount} /> affiliation selected
                  </Singular>
                  <Plural>
                    <Param name="count" value={newAdditionsCount} /> affiliations selected
                  </Plural>
                </PluralTranslate>
                {userCountURL && registrationsCount > 0 && (
                  <>
                    {', '}
                    <PluralTranslate count={registrationsCount}>
                      <Singular>
                        <Param name="count" value={registrationsCount} /> user belongs to them
                      </Singular>
                      <Plural>
                        <Param name="count" value={registrationsCount} /> users belong to them
                      </Plural>
                    </PluralTranslate>
                  </>
                )}
              </>
            )}
          </span>
          <Button type="button" primary onClick={handleConfirm} disabled={!hasChanges}>
            <Translate>Add</Translate>
          </Button>
          <Button type="button" onClick={handleCancel}>
            <Translate>Cancel</Translate>
          </Button>
        </div>
      </Modal.Actions>
    </Modal>
  );
}
