# This file is part of the third-party Indico plugins.
# Copyright (C) 2026 CERN
#
# The third-party Indico plugins are free software; you can
# redistribute them and/or modify them under the terms of the;
# MIT License see the LICENSE file for more details.

from indico.core.db import db
from indico.util.string import format_repr


class RoleCatalog(db.Model):
    __tablename__ = 'role_catalogs'
    __table_args__ = {'schema': 'plugin_affiliation_extras'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, default='')
    allow_other_role = db.Column(db.Boolean, nullable=False, default=False)

    roles = db.relationship(
        'AffiliationRole',
        lazy=True,
        order_by=lambda: AffiliationRole.position,
        cascade='all, delete-orphan',
        backref=db.backref('catalog', lazy=True),
    )
    # relationship backrefs:
    # - affiliation_lists (AffiliationList.role_catalog)

    def __repr__(self):
        return format_repr(self, 'id', _text=self.name)


class AffiliationRole(db.Model):
    __tablename__ = 'affiliation_roles'
    __table_args__ = (
        db.Index(
            'ix_uq_affiliation_roles_catalog_id_code_lower',
            'catalog_id',
            db.text('lower(code)'),
            unique=True,
        ),
        {'schema': 'plugin_affiliation_extras'},
    )

    id = db.Column(db.Integer, primary_key=True)
    catalog_id = db.Column(
        db.Integer,
        db.ForeignKey('plugin_affiliation_extras.role_catalogs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    position = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return format_repr(self, 'id', 'catalog_id', 'code', _text=self.name)
