# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SgtErpPermissionMatrix(models.Model):
    _name = 'sgt.erp.permission.matrix'
    _description = 'SGT ERP Visual Permission Matrix'
    _order = 'role_preset_id, module_shortdesc asc, model_id asc'

    role_preset_id = fields.Many2one('sgt.erp.role.preset', string='Role Preset', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', string='Target Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    model_display_name = fields.Char(related='model_id.name', string='Object Description', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    module_id = fields.Many2one('ir.module.module', string='Module', compute='_compute_module_info', store=True)
    module_shortdesc = fields.Char(string='Module', compute='_compute_module_info', store=True)

    data_scope = fields.Selection([
        ('all', 'All Records (All)'),
        ('team', 'Team Records (Team)'),
        ('own', 'Own Records Only (Own)'),
    ], string='Data Scope', default='own', required=True,
       help='Data access scope for this business object (All Records / Team Records / Own Records).')

    model_type = fields.Selection([
        ('primary', 'Primary Business'),
        ('config', 'Configuration / Master Data'),
    ], string='Object Classification', default='primary', required=True)

    perm_read = fields.Boolean(string='Read', default=True)
    perm_write = fields.Boolean(string='Write', default=False)
    perm_create = fields.Boolean(string='Create', default=False)
    perm_unlink = fields.Boolean(string='Delete', default=False)

    note = fields.Char(string='Policy Note')

    @api.constrains('role_preset_id', 'model_id')
    def _check_unique_role_model(self):
        for rec in self:
            count = self.search_count([
                ('role_preset_id', '=', rec.role_preset_id.id),
                ('model_id', '=', rec.model_id.id),
            ])
            if count > 1:
                raise ValidationError(_("Object '%s' already exists in Permission Matrix for Role '%s'!") % (
                    rec.model_id.name, rec.role_preset_id.name
                ))

    @api.depends('model_id')
    def _compute_module_info(self):
        for rec in self:
            if not rec.model_id:
                rec.module_id = False
                rec.module_shortdesc = False
                continue
            data = self.env['ir.model.data'].sudo().search([
                ('model', '=', 'ir.model'),
                ('res_id', '=', rec.model_id.id)
            ], limit=1)
            if data and data.module:
                mod = self.env['ir.module.module'].sudo().search([('name', '=', data.module)], limit=1)
                rec.module_id = mod.id if mod else False
                rec.module_shortdesc = (mod.shortdesc or mod.name) if mod else data.module
            else:
                rec.module_id = False
                first_part = rec.model_id.model.split('.')[0] if '.' in rec.model_id.model else rec.model_id.model
                rec.module_shortdesc = first_part.capitalize()

    @api.onchange('role_preset_id')
    def _onchange_role_preset_id(self):
        if self.role_preset_id and self.role_preset_id.data_scope:
            self.data_scope = self.role_preset_id.data_scope

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['sgt.erp.permission.matrix']
        to_create = []
        for vals in vals_list:
            if 'data_scope' not in vals and vals.get('role_preset_id'):
                preset = self.env['sgt.erp.role.preset'].browse(vals['role_preset_id'])
                if preset.data_scope:
                    vals['data_scope'] = preset.data_scope

            role_id = vals.get('role_preset_id')
            model_id = vals.get('model_id')
            if role_id and model_id:
                existing = self.search([
                    ('role_preset_id', '=', role_id),
                    ('model_id', '=', model_id),
                ], limit=1)
                if existing:
                    existing.write(vals)
                    records |= existing
                    continue
            to_create.append(vals)

        if to_create:
            created = super().create(to_create)
            records |= created

        if records:
            records.action_sync_to_odoo_acls()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ['perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'data_scope', 'model_id']):
            self.action_sync_to_odoo_acls()
        return res

    def unlink(self):
        roles = self.mapped('role_preset_id')
        res = super().unlink()
        roles._sync_record_rules()
        return res

    def action_sync_to_odoo_acls(self):
        """Synchronize permission matrix to ir.model.access and ir.rule for role groups."""
        access_obj = self.env['ir.model.access'].sudo()
        synced_count = 0
        roles_to_sync = self.env['sgt.erp.role.preset']

        for rec in self:
            if not rec.role_preset_id or not rec.model_id:
                continue

            roles_to_sync |= rec.role_preset_id
            target_groups = rec.role_preset_id.group_ids
            if rec.role_preset_id.security_group_id:
                target_groups |= rec.role_preset_id.security_group_id

            for group in target_groups:
                existing = access_obj.search([
                    ('model_id', '=', rec.model_id.id),
                    ('group_id', '=', group.id)
                ], limit=1)
                vals = {
                    'name': f"SGT Matrix: {rec.role_preset_id.name} - {rec.model_id.name}",
                    'model_id': rec.model_id.id,
                    'group_id': group.id,
                    'perm_read': rec.perm_read,
                    'perm_write': rec.perm_write,
                    'perm_create': rec.perm_create,
                    'perm_unlink': rec.perm_unlink,
                }
                if existing:
                    existing.write(vals)
                else:
                    access_obj.create(vals)
                synced_count += 1

        # Synchronize dynamic Record Rules for roles
        for role in roles_to_sync:
            role._sync_record_rules()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Permission Matrix Synchronized"),
                'message': _("Successfully synchronized %d access control rules (ACLs & Record Rules) for %d role(s).") % (synced_count, len(roles_to_sync)),
                'type': 'success',
                'sticky': False,
            }
        }
