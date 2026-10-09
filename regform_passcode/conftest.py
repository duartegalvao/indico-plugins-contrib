# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

import pytest

from indico.core.plugins import IndicoPlugin


pytest_plugins = ['indico.modules.events.registration.testing.fixtures']


@pytest.fixture(autouse=True)
def _plugin_manifest(mocker):
    mocker.patch.object(IndicoPlugin, 'manifest')
