# Registration Form Passcode

This plugin adds a passcode prompt to Indico registration forms. Event managers can
configure a passcode and rich-text instructions explaining where participants can
find it.

Passcode protection is configured separately for each registration form through
the **Passcode protection** section on its management page. The form must have
**Only logged-in users** enabled in General Settings before protection can be
configured. Registration managers and participants who already have a registration
can access the form without entering a passcode.

After entering a passcode, participants receive temporary access in their current
session. The access duration is configured in the plugin settings and defaults to
24 hours. Changes to the duration apply only to new access grants. When changing a
passcode, managers can choose whether to revoke existing grants and require
participants to enter the new code.

## Changelog

### 3.3

- Initial release.
