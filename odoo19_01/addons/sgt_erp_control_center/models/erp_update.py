# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpUpdate(models.Model):
    _name = 'sgt.erp.update'
    _description = 'SGT ERP Update & Version Manager'
    _order = 'release_date desc, id desc'

    name = fields.Char(string='Update Title', required=True)
    version = fields.Char(string='Version Code', required=True)
    release_date = fields.Date(string='Release Date', default=fields.Date.context_today)
    is_current = fields.Boolean(string='Current Installed Version', default=False)
    state = fields.Selection([
        ('installed', 'Installed'),
        ('available', 'Update Available'),
        ('upcoming', 'Upcoming Release'),
    ], string='Status', default='installed', required=True)
    
    changelog = fields.Html(string='What\'s New & Changes')
    upgrade_notes = fields.Text(string='Migration & Technical Notes')

    @api.model
    def action_check_updates(self):
        """Kiểm tra phiên bản hiện tại từ manifest"""
        mod = self.env['ir.module.module'].search([('name', '=', 'sgt_erp_control_center')], limit=1)
        current_ver = mod.installed_version if mod else '19.0.2.0.0'
        records = self.search([])
        for r in records:
            r.is_current = (r.version == current_ver or current_ver.endswith(r.version))
            if r.is_current:
                r.state = 'installed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Update Check Completed"),
                'message': _("Current installed version is %s. System is up to date.") % current_ver,
                'type': 'success',
                'sticky': False,
            }
        }
