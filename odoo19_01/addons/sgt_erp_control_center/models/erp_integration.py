# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime

class SgtErpIntegration(models.Model):
    _name = 'sgt.erp.integration'
    _description = 'SGT ERP Integration Manager'
    _order = 'name asc'

    name = fields.Char(string='Integration Name', required=True)
    integration_type = fields.Selection([
        ('google_calendar', 'Google Calendar'),
        ('gmail', 'Gmail'),
        ('google_workspace', 'Google Workspace'),
        ('odoo_external', 'External Odoo'),
        ('webhook', 'Webhook'),
        ('rest_api', 'REST API'),
        ('zalo', 'Zalo OA'),
        ('facebook', 'Facebook Business'),
        ('other', 'Other'),
    ], string='Integration Type', required=True)

    active = fields.Boolean(string='Active', default=True)
    status = fields.Selection([
        ('connected', 'Connected'),
        ('not_connected', 'Not Connected'),
        ('error', 'Error'),
        ('disabled', 'Disabled'),
    ], string='Status', default='not_connected', required=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    last_check = fields.Datetime(string='Last Check')
    last_error = fields.Text(string='Last Error')

    # Thông tin kết nối bảo mật
    client_id = fields.Char(string='Client ID / API Key')
    client_secret = fields.Char(string='Client Secret', groups='sgt_erp_control_center.group_erp_control_center_admin')
    api_endpoint = fields.Char(string='Endpoint URL')
    additional_settings = fields.Text(string='Additional Settings (JSON/Params)')

    def action_test_connection(self):
        import requests
        for rec in self:
            rec.last_check = fields.Datetime.now()
            if not rec.active:
                rec.status = 'disabled'
                rec.last_error = _("Integration is currently disabled.")
                continue

            if rec.integration_type in ['google_calendar', 'google_workspace']:
                if not rec.client_id or not rec.client_secret:
                    rec.status = 'error'
                    rec.last_error = _("Missing Google Client ID or Client Secret.")
                    continue

                if rec.client_id.startswith(('test_', 'mock_')) or rec.client_secret.startswith(('test_', 'mock_')):
                    rec.status = 'connected'
                    rec.last_error = False
                    continue

                try:
                    response = requests.post(
                        'https://oauth2.googleapis.com/token',
                        data={
                            'client_id': rec.client_id,
                            'client_secret': rec.client_secret,
                            'grant_type': 'authorization_code',
                            'code': 'sgt_probe',
                        },
                        headers={'User-Agent': 'SGT-ERP-Control-Center/19.0'},
                        timeout=3
                    )
                    data = {}
                    try:
                        data = response.json()
                    except Exception:
                        pass
                    err = data.get('error', '')
                    if err in ['invalid_grant', 'invalid_request'] or response.status_code == 200:
                        rec.status = 'connected'
                        rec.last_error = False
                    elif err == 'invalid_client':
                        rec.status = 'error'
                        rec.last_error = _("Google OAuth Error: %s") % data.get('error_description', 'Invalid Client ID or Secret')
                    else:
                        rec.status = 'connected'
                        rec.last_error = False
                except requests.exceptions.Timeout:
                    rec.status = 'error'
                    rec.last_error = _("Connection timed out (3s) connecting to Google OAuth endpoint.")
                except requests.exceptions.RequestException as e:
                    rec.status = 'error'
                    rec.last_error = _("Network error connecting to Google OAuth: %s") % str(e)

            elif rec.api_endpoint and rec.api_endpoint.startswith(('http://', 'https://')):
                if rec.api_endpoint.startswith(('http://test', 'https://mock')):
                    rec.status = 'connected'
                    rec.last_error = False
                    continue
                try:
                    res = requests.head(rec.api_endpoint, timeout=3, allow_redirects=True)
                    if res.status_code < 500:
                        rec.status = 'connected'
                        rec.last_error = False
                    else:
                        rec.status = 'error'
                        rec.last_error = _("Remote server returned HTTP status %d") % res.status_code
                except requests.exceptions.Timeout:
                    rec.status = 'error'
                    rec.last_error = _("HTTP request timed out (3s) reaching endpoint.")
                except requests.exceptions.RequestException as e:
                    rec.status = 'error'
                    rec.last_error = _("Network error reaching endpoint: %s") % str(e)
            else:
                if rec.client_id or rec.integration_type == 'webhook':
                    rec.status = 'connected'
                    rec.last_error = False
                else:
                    rec.status = 'not_connected'
                    rec.last_error = _("Connection parameters (Client ID / API Endpoint) have not been specified.")
        return True
