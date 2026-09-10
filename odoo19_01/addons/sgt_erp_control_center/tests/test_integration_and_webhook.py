# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase
import json

class TestSgtErpIntegrationAndWebhook(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Config = cls.env['sgt.erp.config']
        cls.Integration = cls.env['sgt.erp.integration']
        cls.company = cls.env.company

    def test_01_google_connection_mock_and_disabled(self):
        """Kiểm tra xử lý Google Calendar disabled, missing và mock credentials"""
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Google Test Config',
                'company_id': self.company.id,
                'product_name': 'Google Test ERP',
            })

        # 1. Disabled state
        config.write({'enable_google_calendar': False})
        config.action_test_google_connection()
        self.assertEqual(config.google_connection_status, 'disabled')

        # 2. Missing credentials
        config.write({
            'enable_google_calendar': True,
            'google_client_id': False,
            'google_client_secret': False,
        })
        config.action_test_google_connection()
        self.assertEqual(config.google_connection_status, 'error')
        self.assertIn('Missing Client ID', config.google_error_message)

        # 3. Mock credentials for CI
        config.write({
            'google_client_id': 'mock_client_id.apps.googleusercontent.com',
            'google_client_secret': 'mock_secret_key',
        })
        res = config.action_test_google_connection()
        self.assertEqual(config.google_connection_status, 'connected')
        self.assertEqual(res.get('params', {}).get('type'), 'success')

    def test_02_integration_manager_test_connection(self):
        """Kiểm tra action_test_connection trên sgt.erp.integration"""
        # Test Google Calendar integration with mock
        integration_google = self.Integration.create({
            'name': 'Google Calendar Sync',
            'integration_type': 'google_calendar',
            'client_id': 'test_google_client_id',
            'client_secret': 'test_secret',
            'company_id': self.company.id,
        })
        integration_google.action_test_connection()
        self.assertEqual(integration_google.status, 'connected')

        # Test Webhook integration
        integration_webhook = self.Integration.create({
            'name': 'Zalo Inbound Webhook',
            'integration_type': 'webhook',
            'client_id': 'sgt_secret_token_123',
            'company_id': self.company.id,
        })
        integration_webhook.action_test_connection()
        self.assertEqual(integration_webhook.status, 'connected')

    def test_03_webhook_controller_endpoints(self):
        """Kiểm tra các endpoint Webhook Controller (/sgt_erp/webhook/ping và /sgt_erp/webhook/<token>)"""
        # 1. Test ping route
        ping_res = self.url_open('/sgt_erp/webhook/ping')
        self.assertEqual(ping_res.status_code, 200)
        ping_data = json.loads(ping_res.text)
        self.assertEqual(ping_data.get('status'), 'active')

        # 2. Create test webhook integration
        webhook_token = 'unique_webhook_token_xyz_999'
        integration = self.Integration.create({
            'name': 'Test CRM Webhook',
            'integration_type': 'webhook',
            'client_id': webhook_token,
            'status': 'not_connected',
            'company_id': self.company.id,
        })

        # 3. Test valid webhook invocation
        res = self.url_open(f'/sgt_erp/webhook/{webhook_token}')
        self.assertEqual(res.status_code, 200)
        res_data = json.loads(res.text)
        self.assertEqual(res_data.get('status'), 'success')
        self.assertEqual(res_data.get('integration'), 'Test CRM Webhook')

        # Verify integration record was marked connected
        integration.invalidate_recordset()
        self.assertEqual(integration.status, 'connected')
        self.assertTrue(integration.last_check)

        # 4. Test invalid token returns 404
        res_invalid = self.url_open('/sgt_erp/webhook/non_existent_token_000')
        self.assertEqual(res_invalid.status_code, 404)
        invalid_data = json.loads(res_invalid.text)
        self.assertEqual(invalid_data.get('error'), 'invalid_token')
