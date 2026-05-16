// This file is part of the third-party Indico plugins.
// Copyright (C) 2026 CERN
//
// The third-party Indico plugins are free software; you can
// redistribute them and/or modify them under the terms of the;
// MIT License see the LICENSE file for more details.

import React from 'react';
import ReactDOM from 'react-dom';

import RoleCatalogManagement from './RoleCatalogManagement';

export default function setupRoleCatalogs(elem, roleCatalogs) {
  ReactDOM.render(<RoleCatalogManagement initialCatalogs={roleCatalogs} />, elem);
}
