# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpAuditLog(models.Model):
    _name = 'sgt.erp.audit.log'
    _description = 'SGT ERP Configuration Audit Log'
    _order = 'date desc, id desc'

    name = fields.Char(string='Summary', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    date = fields.Datetime(string='Date & Time', default=fields.Datetime.now, readonly=True)
    
    category = fields.Selection([
        ('branding', 'Branding'),
        ('theme', 'Theme'),
        ('package', 'Package'),
        ('feature', 'Feature'),
        ('workflow', 'Workflow & Approval'),
        ('integration', 'Integration'),
        ('license', 'License / Giấy phép'),
        ('general', 'General Configuration'),
    ], string='Category', required=True, readonly=True)

    field_name = fields.Char(string='Field Changed', required=True, readonly=True)
    old_value = fields.Text(string='Old Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)

    @api.depends('category', 'field_name', 'user_id', 'date')
    def _compute_name(self):
        for rec in self:
            user_name = rec.user_id.name if rec.user_id else 'System'
            cat_label = dict(self._fields['category'].selection).get(rec.category, rec.category or 'CONFIG')
            rec.name = f"[{cat_label}] {rec.field_name or 'Update'} by {user_name}"

    @api.model
    def log_change(self, category, field_name, old_value, new_value, company_id=None):
        """Helper để ghi nhận thay đổi cấu hình tường minh"""
        old_str = str(old_value) if old_value is not None and old_value is not False else ''
        new_str = str(new_value) if new_value is not None and new_value is not False else ''
        if old_str == new_str:
            return False
        return self.create({
            'user_id': self.env.user.id,
            'date': fields.Datetime.now(),
            'category': category,
            'field_name': field_name,
            'old_value': old_str,
            'new_value': new_str,
            'company_id': company_id.id if company_id else self.env.company.id,
        })
