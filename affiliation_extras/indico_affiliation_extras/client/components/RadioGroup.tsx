// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import React from 'react';
import {Form} from 'semantic-ui-react';

import {RadioButton} from 'indico/react/components';

import './RadioGroup.module.scss';

type RadioGroupValue = string | number;

export interface RadioGroupOption {
  value: RadioGroupValue;
  label: React.ReactNode;
  disabled?: boolean;
}

export default function RadioGroup({
  id,
  value,
  onChange,
  options,
  disabled = false,
  required = false,
  label,
  noneLabel,
}: {
  id: string;
  value: RadioGroupValue | null;
  onChange: (value: RadioGroupValue | null) => void;
  options: RadioGroupOption[];
  disabled?: boolean;
  required?: boolean;
  label?: React.ReactNode;
  noneLabel?: React.ReactNode;
}) {
  if (options.length === 0) {
    return null;
  }

  return (
    <Form.Field required={required}>
      {label && <label>{label}</label>}
      <table className="affiliation-extras-radio-group" role="presentation">
        <tbody>
          {!required && noneLabel && (
            <tr className="affiliation-extras-radio-group-row">
              <td>
                <RadioButton
                  id={`${id}-none`}
                  name={id}
                  label={noneLabel}
                  value=""
                  disabled={disabled}
                  checked={value === null}
                  onChange={() => onChange(null)}
                />
              </td>
            </tr>
          )}
          {options.map((option, index) => (
            <tr className="affiliation-extras-radio-group-row" key={option.value}>
              <td>
                <RadioButton
                  id={`${id}-${index}`}
                  name={id}
                  label={option.label}
                  value={option.value}
                  disabled={disabled || option.disabled}
                  checked={value === option.value}
                  onChange={() => onChange(option.value)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Form.Field>
  );
}
