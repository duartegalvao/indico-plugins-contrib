// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import React, {useState} from 'react';
import {type FormProps, useForm, useFormState} from 'react-final-form';
import {Button, Message, Modal} from 'semantic-ui-react';

import {FinalTinyMCETextEditor} from 'indico/react/components';
import {FinalCheckbox, FinalInput} from 'indico/react/forms';
import {FinalModalForm} from 'indico/react/forms/final-form';

import {Translate} from './i18n';

export interface PasscodeSettingsData {
  is_enabled: boolean;
  passcode: string;
  instructions: string;
}

export interface PasscodeFormValues extends PasscodeSettingsData {
  invalidate_grants: boolean;
}

interface PasscodeSettingsButtonProps {
  settings: PasscodeSettingsData;
  requireLogin: boolean;
  generalSettingsURL: string;
  onSubmit: FormProps<PasscodeFormValues>['onSubmit'];
}

interface PasscodeSettingsProps extends PasscodeSettingsButtonProps {
  onClose: () => void;
}

export function PasscodeSettingsButton(props: PasscodeSettingsButtonProps) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="i-button icon-settings" onClick={() => setOpen(true)}>
        <Translate>Configure</Translate>
      </button>
      {open && <PasscodeSettings {...props} onClose={() => setOpen(false)} />}
    </>
  );
}

function PasscodeFields({settings}: {settings: PasscodeSettingsData}) {
  const form = useForm<PasscodeFormValues>();
  const {values} = useFormState<PasscodeFormValues>({subscription: {values: true}});
  return (
    <>
      <FinalCheckbox
        name="is_enabled"
        label={Translate.string('Require a passcode')}
        onChange={(enabled: boolean) => {
          if (!enabled) {
            form.change('passcode', settings.passcode);
          }
        }}
        showAsToggle
      />
      <FinalInput
        name="passcode"
        label={Translate.string('Passcode')}
        description={Translate.string(
          'The code participants must enter to access the registration form.'
        )}
        disabled={!values.is_enabled}
        required={values.is_enabled ? 'no-validator' : false}
        noAutoComplete
      />
      {settings.passcode && (
        <FinalCheckbox
          name="invalidate_grants"
          label={Translate.string('Revoke access to old codes')}
          description={Translate.string(
            'Participants who already unlocked the form will need to enter the new code.'
          )}
          disabled={!values.is_enabled || values.passcode === settings.passcode}
          isEqual={() => true}
        />
      )}
      <FinalTinyMCETextEditor
        name="instructions"
        label={Translate.string('Instructions for participants')}
        description={Translate.string(
          'Explain where participants can find the code. These instructions are visible before unlocking.'
        )}
        height={250}
        parse={(value: string) => value}
      />
    </>
  );
}

export default function PasscodeSettings({
  settings,
  requireLogin,
  generalSettingsURL,
  onClose,
  onSubmit,
}: PasscodeSettingsProps) {
  const header = Translate.string('Passcode settings');
  if (!requireLogin) {
    return (
      <Modal open onClose={onClose} size="small" closeIcon>
        <Modal.Header>{header}</Modal.Header>
        <Modal.Content>
          <Message warning>
            <Translate>Passcode protection requires participants to log in.</Translate>{' '}
            <Translate>Enable "Only logged-in users" in General Settings.</Translate>
          </Message>
        </Modal.Content>
        <Modal.Actions>
          <Button as="a" href={generalSettingsURL} primary>
            <Translate>Open General Settings</Translate>
          </Button>
          <Button onClick={onClose}>
            <Translate>Close</Translate>
          </Button>
        </Modal.Actions>
      </Modal>
    );
  }
  return (
    <FinalModalForm<PasscodeFormValues>
      id="regform-passcode-settings"
      header={header}
      size="small"
      initialValues={{...settings, invalidate_grants: !!settings.passcode}}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={Translate.string('Save')}
      validate={values =>
        values.is_enabled && !values.passcode.trim()
          ? {passcode: Translate.string('This field is required.')}
          : {}
      }
    >
      <PasscodeFields settings={settings} />
    </FinalModalForm>
  );
}
