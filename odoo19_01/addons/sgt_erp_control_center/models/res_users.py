# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    erp_theme_id = fields.Many2one('sgt.erp.theme', string='Personal ERP Theme', ondelete='set null')
    use_custom_theme = fields.Boolean(string='Use Custom Theme', default=False,
                                      help='If enabled, this user will use personal theme instead of company theme.')
    role_preset_id = fields.Many2one('sgt.erp.role.preset', string='Assigned Role Preset',
                                    help='ERP Role Preset which defines mapped groups and permissions.')

    def get_effective_theme(self):
        """Trả về theme có hiệu lực theo thứ tự ưu tiên: User Theme -> Company Theme -> Default Theme"""
        self.ensure_one()
        if self.use_custom_theme and self.erp_theme_id:
            return self.erp_theme_id
        if self.company_id and self.company_id.erp_theme_id:
            return self.company_id.erp_theme_id
        
        # Fallback theme đầu tiên đang active
        default_theme = self.env['sgt.erp.theme'].search([('active', '=', True)], limit=1)
        return default_theme

    @api.onchange('role_preset_id')
    def _onchange_role_preset_id(self):
        """Tự động bổ sung các nhóm quyền từ Role Preset khi người dùng chọn trên giao diện"""
        if self.role_preset_id:
            groups_to_add = self.role_preset_id.group_ids
            if self.role_preset_id.security_group_id:
                groups_to_add |= self.role_preset_id.security_group_id
            self.group_ids = self.group_ids | groups_to_add

    def action_apply_role_preset(self):
        """Áp dụng các nhóm quyền từ Role Preset vào tài khoản này"""
        for user in self:
            if user.role_preset_id:
                user.role_preset_id._sync_record_rules()
                groups_to_add = user.role_preset_id.group_ids
                if user.role_preset_id.security_group_id:
                    groups_to_add |= user.role_preset_id.security_group_id
                user.write({'group_ids': [(4, g.id) for g in groups_to_add]})
                if user not in user.role_preset_id.user_ids:
                    user.role_preset_id.write({'user_ids': [(4, user.id)]})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Role Preset Applied"),
                'message': _("Permissions & Data Scope from Role Preset applied successfully to user!"),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.role_preset_id:
                user.role_preset_id._sync_record_rules()
                groups_to_add = user.role_preset_id.group_ids
                if user.role_preset_id.security_group_id:
                    groups_to_add |= user.role_preset_id.security_group_id
                if groups_to_add:
                    user.write({'group_ids': [(4, g.id) for g in groups_to_add]})
        return users

    def write(self, vals):
        old_scope_groups = {}
        if 'role_preset_id' in vals:
            for user in self:
                if user.role_preset_id and user.role_preset_id.security_group_id:
                    old_scope_groups[user.id] = user.role_preset_id.security_group_id.id

        res = super().write(vals)

        if 'role_preset_id' in vals:
            for user in self:
                old_grp_id = old_scope_groups.get(user.id)
                if old_grp_id and (not user.role_preset_id or user.role_preset_id.security_group_id.id != old_grp_id):
                    user.write({'group_ids': [(3, old_grp_id)]})

                if user.role_preset_id:
                    user.role_preset_id._sync_record_rules()
                    groups_to_add = user.role_preset_id.group_ids
                    if user.role_preset_id.security_group_id:
                        groups_to_add |= user.role_preset_id.security_group_id
                    if groups_to_add:
                        user.write({'group_ids': [(4, g.id) for g in groups_to_add]})
        return res
