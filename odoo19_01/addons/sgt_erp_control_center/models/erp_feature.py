# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError

class SgtErpFeature(models.Model):
    _name = 'sgt.erp.feature'
    _description = 'SGT ERP Feature Manager'
    _order = 'category asc, sequence asc, name asc'

    name = fields.Char(string='Feature Name', required=True)
    code = fields.Char(string='Feature Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    icon = fields.Char(string='FontAwesome Icon', default='fa-cube', help="E.g.: fa-users, fa-shopping-cart, fa-truck, fa-book")
    category = fields.Selection([
        ('crm', 'CRM'),
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
        ('account', 'Invoicing & Accounting'),
        ('stock', 'Inventory'),
        ('hr', 'Human Resources'),
        ('calendar', 'Calendar'),
        ('project', 'Project'),
        ('lms', 'LMS eLearning'),
        ('system', 'System'),
        ('other', 'Other'),
    ], string='Category', default='system', required=True)
    
    active = fields.Boolean(string='Enabled', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    required_module_names = fields.Char(string='Required Modules (comma-separated)', help='E.g.: crm,sale_management,hr')
    menu_xml_id = fields.Char(string='Related Menu XML ID', help="Root menu XML ID, e.g. 'crm.crm_menu_root'. Supports comma-separated multiple IDs.")
    auto_sync_menu = fields.Boolean(string='Auto Sync Menu Visibility', default=True, help="Automatically toggle related menu visibility when feature state changes.")
    block_direct_access = fields.Boolean(string='Block Direct Access', default=True, help="Block direct URL/Action access when this feature is disabled.")
    description = fields.Text(string='Description')

    @api.constrains('code', 'company_id')
    def _check_code_company_uniq(self):
        for rec in self:
            duplicate = self.search([
                ('code', '=', rec.code),
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id)
            ], limit=1)
            if duplicate:
                raise ValidationError(_("Feature code must be unique per company!"))

    @api.model
    def is_enabled(self, code, company_id=None):
        """
        Helper API to check if a feature is enabled.
        Example: self.env['sgt.erp.feature'].is_enabled('google_calendar')
        """
        if not company_id:
            company_id = self.env.company.id
            
        feature = self.with_context(active_test=False).search([
            ('code', '=', code),
            '|', ('company_id', '=', company_id), ('company_id', '=', False),
        ], order='company_id desc', limit=1)

        if not feature:
            return False

        return bool(feature.active)

    def sync_menu_visibility(self):
        """Synchronize active state of related menus according to feature state and clear menu cache."""
        Menu = self.env['ir.ui.menu'].sudo().with_context(active_test=False)
        changed = False
        for rec in self.with_context(active_test=False):
            if rec.auto_sync_menu and rec.menu_xml_id:
                for xml_id in rec.menu_xml_id.split(','):
                    xml_id = xml_id.strip()
                    if not xml_id:
                        continue
                    menu_rec = self.env.ref(xml_id, raise_if_not_found=False)
                    if menu_rec:
                        menu = Menu.browse(menu_rec.id)
                        if menu.exists() and menu.active != rec.active:
                            menu.write({'active': rec.active})
                            changed = True

        if changed or self.env.context.get('force_clear_cache'):
            self.env.registry.clear_all_caches()
            self.env.invalidate_all()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.sync_menu_visibility()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'active' in vals or 'menu_xml_id' in vals or 'auto_sync_menu' in vals:
            self.with_context(active_test=False).sync_menu_visibility()
        return res

    def action_toggle_feature(self):
        """Toggle feature state (1-click) and display notification."""
        self.ensure_one()
        new_state = not self.active
        self.write({'active': new_state})
        self.with_context(force_clear_cache=True).sync_menu_visibility()
        
        status_text = _("ENABLED") if new_state else _("DISABLED")
        msg_type = 'success' if new_state else 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Feature Status Updated"),
                'message': _("%(status)s feature: %(name)s. System menus have been synchronized.") % {
                    'status': status_text,
                    'name': self.name,
                },
                'type': msg_type,
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.model
    def action_enable_all_features(self):
        """Enable all features in the system."""
        features = self.with_context(active_test=False).search([('active', '=', False)])
        if features:
            features.write({'active': True})
            features.with_context(force_clear_cache=True).sync_menu_visibility()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Activate Features"),
                'message': _("All system features enabled and menus synchronized successfully."),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.model
    def action_force_sync_all_menus(self):
        """Force resynchronization of menu visibility for all features."""
        all_features = self.with_context(active_test=False).search([])
        all_features.with_context(force_clear_cache=True).sync_menu_visibility()
        self.env.registry.clear_all_caches()
        self.env.invalidate_all()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Menu Synchronization"),
                'message': _("All system menus synchronized based on current feature configuration."),
                'type': 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
