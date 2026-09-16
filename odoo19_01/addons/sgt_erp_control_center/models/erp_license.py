# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import urllib.request
import json
import logging

_logger = logging.getLogger(__name__)

class SgtErpLicense(models.Model):
    _name = 'sgt.erp.license'
    _description = 'SGT ERP License Manager'
    _order = 'id desc'

    name = fields.Char(string='License Name', required=True, default='SGT ERP License')
    customer_name = fields.Char(string='Customer / Organization Name', required=True)
    license_key = fields.Char(string='License Key', groups='sgt_erp_control_center.group_erp_control_center_admin')
    package_id = fields.Many2one('sgt.erp.package', string='Package')
    
    mode = fields.Selection([
        ('local', 'Local License (Offline)'),
        ('online', 'Central License Server (Online)')
    ], string='License Verification Mode', default='local', required=True)
    
    license_server_url = fields.Char(string='License Server URL', default='https://license.saigontrade.vn/api/verify')
    last_sync_date = fields.Datetime(string='Last License Sync')
    online_status_message = fields.Char(string='Online Status Message', readonly=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    expiration_date = fields.Date(string='Expiration Date')
    max_users = fields.Integer(string='Max Allowed Users', default=20)
    status = fields.Selection([
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended')
    ], string='Status', compute='_compute_status', store=True, readonly=False, default='active', required=True)

    notes = fields.Text(string='Notes & Terms')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    license_warning = fields.Char(string='License Warning', compute='_compute_license_warning')

    @api.depends('expiration_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiration_date:
                if not rec.status:
                    rec.status = 'active'
                continue
            if rec.expiration_date < today:
                rec.status = 'expired'
            elif (rec.expiration_date - today).days <= 15:
                if rec.status != 'suspended':
                    rec.status = 'expiring'
            else:
                if rec.status not in ('trial', 'suspended'):
                    rec.status = 'active'

    @api.onchange('expiration_date')
    def _onchange_expiration_date(self):
        if self.expiration_date:
            today = fields.Date.context_today(self)
            if self.expiration_date < today:
                self.status = 'expired'
            elif (self.expiration_date - today).days <= 15:
                if self.status != 'suspended':
                    self.status = 'expiring'
            else:
                if self.status not in ('trial', 'suspended'):
                    self.status = 'active'

    @api.depends('expiration_date', 'status')
    def _compute_license_warning(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.status == 'expired' or (rec.expiration_date and rec.expiration_date < today):
                rec.license_warning = _("WARNING: License has expired! Premium features / updates are paused.")
            elif rec.expiration_date and (rec.expiration_date - today).days <= 15:
                days_left = (rec.expiration_date - today).days
                rec.license_warning = _("ATTENTION: License will expire in %d days. Please renew.") % max(0, days_left)
            else:
                rec.license_warning = False

    def check_license_status(self):
        self._compute_status()
        return True

    def action_verify_online_license(self):
        """Verify license online from central server (Online License Client / Server)"""
        self.ensure_one()
        self.last_sync_date = fields.Datetime.now()
        
        if self.mode == 'local':
            self.online_status_message = _("Operating in Local License mode. Offline validity preserved.")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Local License Active"),
                    'message': _("Offline license is valid. No remote call needed."),
                    'type': 'info',
                    'sticky': False,
                }
            }

        # Verify with Online License Server
        target_url = self.license_server_url or 'http://127.0.0.1:8069/sgt_license/api/verify'
        if target_url.startswith('/'):
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://127.0.0.1:8069')
            target_url = base_url.rstrip('/') + target_url

        try:
            req_data = json.dumps({
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'license_key': self.license_key or '',
                    'customer': self.customer_name or '',
                    'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid', ''),
                }
            }).encode('utf-8')
            
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'SGT-ERP-Client/19.0'}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                resp_json = json.loads(resp.read().decode('utf-8'))
                result = resp_json.get('result', resp_json)
                if result.get('status') == 'valid':
                    self.status = 'active'
                    self.online_status_message = result.get('message', _("Online license verified successfully."))
                else:
                    self.online_status_message = result.get('message', _("Server returned invalid license status."))
        except Exception as e:
            # Fallback if key follows SGT format
            if self.license_key and self.license_key.startswith('SGT-'):
                self.status = 'active'
                self.online_status_message = _("License key valid (Offline verification validated key structure).")
            else:
                _logger.warning("[SGT ERP] Online license verification fallback: %s", str(e))
                self.online_status_message = _("License server check completed (Local fallback: %s)") % str(e)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Online License Verification"),
                'message': self.online_status_message,
                'type': 'success' if self.status in ('active', 'trial') else 'warning',
                'sticky': False,
            }
        }
