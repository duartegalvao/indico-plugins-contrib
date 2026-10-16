// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import {FORM_ERROR} from 'final-form';
import React from 'react';
import ReactDOM from 'react-dom';
import type {FormProps} from 'react-final-form';

import {handleSubmitError} from 'indico/react/forms';
import {indicoAxios} from 'indico/utils/axios';

import {
  PasscodeSettingsButton,
  type PasscodeFormValues,
  type PasscodeSettingsData,
} from './PasscodeSettings';

customElements.define(
  'ind-plugin-regform-passcode-settings',
  class extends HTMLElement {
    connectedCallback() {
      const handleSubmit: FormProps<PasscodeFormValues>['onSubmit'] = async data => {
        try {
          await indicoAxios.post(this.getAttribute('save-url') ?? '', data);
        } catch (error) {
          return handleSubmitError(error, {_schema: FORM_ERROR});
        }
        location.reload();
      };
      ReactDOM.render(
        <PasscodeSettingsButton
          settings={JSON.parse(this.getAttribute('settings') ?? '') as PasscodeSettingsData}
          requireLogin={JSON.parse(this.getAttribute('require-login') ?? '')}
          generalSettingsURL={this.getAttribute('general-settings-url') ?? ''}
          onSubmit={handleSubmit}
        />,
        this
      );
    }

    disconnectedCallback() {
      ReactDOM.unmountComponentAtNode(this);
    }
  }
);
