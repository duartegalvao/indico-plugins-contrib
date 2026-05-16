// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import _ from 'lodash';
import React, {useState} from 'react';
import {Button, Confirm, Icon, Input, Popup} from 'semantic-ui-react';

import {FinalField} from 'indico/react/forms';
import {Translate} from 'indico/react/i18n';
import {SortableWrapper, useSortableItem} from 'indico/react/sortable';

import './RoleListField.module.scss';

const DEFAULT_ROLE_VALUE = {
  id: null,
  code: '',
  name: '',
  position: null,
};
const DRAG_TYPE = 'affiliations-role-catalog-role';

export interface RoleItem {
  id?: number | null;
  code: string;
  name: string;
  position?: number | null;
}

interface RoleListRowProps {
  value: RoleItem;
  index: number;
  onChange: (value: RoleItem) => void;
  onDelete: () => void;
  onMove: (sourceIndex: number, targetIndex: number) => void;
  canDelete: boolean;
}

function RoleListRow({value, index, onChange, onDelete, onMove, canDelete}: RoleListRowProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [handleRef, itemRef, style] = useSortableItem({
    type: DRAG_TYPE,
    id: value.id ?? `new-${index}`,
    index,
    active: true,
    separateHandle: true,
    moveItem: onMove,
    itemData: {},
    onDrop: () => null,
  });
  const triggerDelete = () =>
    value.code.trim() || value.name.trim() || value.id != null ? setDeleteOpen(true) : onDelete();

  return (
    <tr ref={itemRef} style={{...style}}>
      <td ref={handleRef} style={{width: '1.5em', cursor: 'grab'}}>
        <Icon name="bars" color="grey" title={Translate.string('Drag to reorder')} />
      </td>
      <td>
        <Input
          size="small"
          placeholder={Translate.string('Role code')}
          value={value.code}
          onChange={(_, {value: code}) => onChange({...value, code})}
        />
      </td>
      <td>
        <Input
          size="small"
          placeholder={Translate.string('Role name')}
          value={value.name}
          onChange={(_, {value: name}) => onChange({...value, name})}
        />
      </td>
      <td style={{whiteSpace: 'nowrap', width: '1px'}}>
        <Popup
          content={Translate.string('Remove role')}
          on="hover"
          trigger={
            <Icon
              name="trash"
              color="grey"
              onClick={canDelete ? triggerDelete : undefined}
              disabled={!canDelete}
              link={canDelete}
            />
          }
        />
        <Confirm
          header={
            value.name
              ? Translate.string('Removing role "{name}"', {name: value.name})
              : Translate.string('Removing role')
          }
          content={Translate.string('Are you sure you want to remove this role?')}
          confirmButton={<Button content={Translate.string('Remove')} negative />}
          cancelButton={Translate.string('Cancel')}
          open={deleteOpen}
          onCancel={() => setDeleteOpen(false)}
          onConfirm={() => {
            onDelete();
            setDeleteOpen(false);
          }}
        />
      </td>
    </tr>
  );
}

function RoleListField({
  value: _value,
  onChange,
  onFocus,
  onBlur,
}: {
  value?: RoleItem[];
  onChange: (value: RoleItem[]) => void;
  onFocus: () => void;
  onBlur: () => void;
}) {
  const values = _value?.length ? _value : [DEFAULT_ROLE_VALUE];
  const normalizePositions = (items: RoleItem[]) =>
    items.map((item, idx) => ({
      ...item,
      position: idx + 1,
    }));
  const normalizedValues = normalizePositions(values);

  const handleChange = (newValue: RoleItem[], touch: boolean = true) => {
    onChange(normalizePositions(newValue));
    if (touch) {
      onFocus();
      onBlur();
    }
  };

  const handleMove = (sourceIndex: number, targetIndex: number) => {
    const newValue = [...normalizedValues];
    const [sourceItem] = newValue.splice(sourceIndex, 1);
    newValue.splice(targetIndex, 0, sourceItem);
    handleChange(newValue);
  };

  return (
    <>
      <SortableWrapper accept={DRAG_TYPE}>
        <table className="i-table-widget">
          <colgroup>
            <col styleName="col-drag" />
            <col styleName="col-code" />
            <col styleName="col-name" />
            <col styleName="col-actions" />
          </colgroup>
          <thead>
            <tr>
              <th />
              <th>
                <Translate>Code</Translate>
              </th>
              <th>
                <Translate>Name</Translate>
              </th>
              <th />
            </tr>
          </thead>
          <tbody>
            {normalizedValues.map((value, idx) => (
              <RoleListRow
                key={value.id ?? `new-${idx}`}
                index={idx}
                value={value}
                canDelete={normalizedValues.length > 1}
                onChange={newValue =>
                  handleChange(normalizedValues.map((v, i) => (i === idx ? newValue : v)))
                }
                onDelete={() => handleChange(normalizedValues.filter((_, i) => i !== idx))}
                onMove={handleMove}
              />
            ))}
          </tbody>
        </table>
      </SortableWrapper>
      <Button
        type="button"
        icon="add"
        content={Translate.string('Add role')}
        onClick={() => handleChange([...normalizedValues, DEFAULT_ROLE_VALUE], false)}
        disabled={normalizedValues.some(v => !v.code.trim() || !v.name.trim())}
        style={{marginTop: '0.5em'}}
        compact
        basic
      />
    </>
  );
}

const validateRoles = (value: RoleItem[]) => {
  if (!value?.length) {
    return Translate.string('Role catalogs must contain at least one role.');
  }
  if (value.some(({code, name}) => !code.trim() || !name.trim())) {
    return Translate.string('Role codes and names must not be empty.');
  }
  const codes = value.map(({code}) => code.trim().toLowerCase());
  if (_.uniq(codes).length !== codes.length) {
    return Translate.string('Role codes must be unique within a catalog.');
  }
};

export default function FinalRoleList({name, ...rest}) {
  return (
    <FinalField
      name={name}
      component={RoleListField}
      format={(v: RoleItem[]) => v}
      parse={(v: RoleItem[]) => v}
      undefinedValue={[]}
      isEqual={_.isEqual}
      validate={validateRoles}
      {...rest}
    />
  );
}
