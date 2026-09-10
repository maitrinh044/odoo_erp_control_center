# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestSgtErpControlCenter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Config = cls.env['sgt.erp.config']
        cls.company = cls.env.company

    def test_01_config_creation_and_unique_company(self):
        """Kiểm tra tạo ERP config và ràng buộc duy nhất theo công ty"""
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Test Corp ERP Config',
                'company_id': self.company.id,
                'customer_name': 'Test Corp',
                'product_name': 'Test ERP',
            })
        self.assertTrue(config.id)
        self.assertEqual(config.company_id, self.company)

        # Ràng buộc trùng lặp phải quăng ValidationError
        with self.assertRaises(ValidationError):
            self.Config.create({
                'name': 'Duplicate Corp Config',
                'company_id': self.company.id,
                'customer_name': 'Duplicate Corp',
                'product_name': 'Duplicate ERP',
            })

    def test_02_action_apply_configuration(self):
        """Kiểm tra áp dụng cấu hình 10 bước chuẩn chỉ"""
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Test Corp ERP Config',
                'company_id': self.company.id,
                'customer_name': 'Test Corp',
                'product_name': 'Test ERP',
            })
        
        action = config.action_apply_configuration()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('params', {}).get('type'), 'success')

        # Kiểm tra chatter log
        messages = self.env['mail.message'].search([
            ('model', '=', 'sgt.erp.config'),
            ('res_id', '=', config.id)
        ], order='id desc', limit=1)
        self.assertTrue(messages)
        self.assertIn('Apply Configuration Executed', messages.body)

    def test_03_backup_status_check(self):
        """Kiểm tra hàm kiểm tra trạng thái sao lưu (Backup Status)"""
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Test Corp ERP Config',
                'company_id': self.company.id,
                'customer_name': 'Test Corp',
                'product_name': 'Test ERP',
            })
        
        res = config.action_check_backup_status()
        self.assertEqual(res.get('params', {}).get('type'), 'success')
        self.assertEqual(config.backup_status, 'ok')
        self.assertTrue(config.backup_last_date)

    def test_04_setup_wizard(self):
        """Kiểm tra luồng Wizard thiết lập nhanh 5 bước"""
        package = self.env['sgt.erp.package'].search([], limit=1)
        theme = self.env['sgt.erp.theme'].search([], limit=1)
        wizard = self.env['sgt.erp.setup.wizard'].create({
            'customer_name': 'Wizard Business',
            'product_name': 'Wizard ERP',
            'package_id': package.id,
            'theme_id': theme.id,
            'company_id': self.company.id,
        })
        self.assertEqual(wizard.state, 'step1')
        wizard.action_goto_step2()
        self.assertEqual(wizard.state, 'step2')
        wizard.action_goto_step3()
        self.assertEqual(wizard.state, 'step3')
        wizard.action_goto_step4()
        self.assertEqual(wizard.state, 'step4')
        wizard.action_goto_step5()
        self.assertEqual(wizard.state, 'step5')

    def test_05_audit_log_tracking(self):
        """Kiểm tra ghi nhận Audit Log khi thay đổi cấu hình quan trọng (Mục 24)"""
        AuditLog = self.env['sgt.erp.audit.log']
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Test Corp ERP Config',
                'company_id': self.company.id,
                'customer_name': 'Original Name',
                'product_name': 'Original Product',
            })
        
        # Sửa cấu hình
        config.write({
            'product_name': 'New White-label Name',
            'customer_name': 'Updated Client Ltd',
        })

        logs = AuditLog.search([
            ('company_id', '=', self.company.id),
            ('field_name', 'in', ['ERP Product Name', 'Customer / Business Name'])
        ])
        self.assertTrue(logs, "Audit logs must be created on config write")
        product_log = logs.filtered(lambda l: l.field_name == 'ERP Product Name')
        self.assertTrue(product_log)
        self.assertEqual(product_log.new_value, 'New White-label Name')
        self.assertEqual(product_log.category, 'branding')

    def test_06_system_health_telemetry(self):
        """Kiểm tra đo lường Health Telemetry: RAM, Disk, Crons, Mail, Database Metrics"""
        config = self.Config.search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.Config.create({
                'name': 'Telemetry Test Config',
                'company_id': self.company.id,
                'customer_name': 'Telemetry Corp',
                'product_name': 'Telemetry ERP',
            })
        
        # Test Refresh Health action
        action_res = config.action_refresh_health()
        self.assertEqual(action_res.get('params', {}).get('type'), 'success')

        # Check telemetry fields
        self.assertIn(config.overall_system_status, ['operational', 'degraded', 'critical'])
        self.assertGreaterEqual(config.database_size_mb, 0)
        self.assertGreaterEqual(config.database_active_connections, 1)
        self.assertTrue(config.database_version)
        self.assertGreaterEqual(config.disk_percentage, 0.0)
        self.assertGreaterEqual(config.ram_percentage, 0.0)
        self.assertGreaterEqual(config.cron_total_count, 0)
        self.assertTrue(config.server_uptime)

        # Check CPU & Processor telemetry (Phase 2)
        self.assertGreaterEqual(config.cpu_cores, 1)
        self.assertGreaterEqual(config.cpu_percentage, 0.0)
        self.assertGreaterEqual(config.cpu_load_1m, 0.0)
        self.assertGreaterEqual(config.cpu_load_5m, 0.0)
        self.assertGreaterEqual(config.cpu_load_15m, 0.0)
        self.assertTrue(config.cpu_model)

        # Check OS Partition Disk metrics (Phase 2)
        self.assertGreaterEqual(config.os_disk_total_gb, 0.0)
        self.assertGreaterEqual(config.os_disk_used_gb, 0.0)
        self.assertGreaterEqual(config.os_disk_free_gb, 0.0)
        self.assertGreaterEqual(config.os_disk_percentage, 0.0)

        # Test view action helpers
        crons_action = config.action_view_failed_crons()
        self.assertEqual(crons_action['res_model'], 'ir.cron')
        mail_action = config.action_view_mail_queue()
        self.assertEqual(mail_action['res_model'], 'mail.mail')
        users_action = config.action_view_active_users()
        self.assertEqual(users_action['res_model'], 'res.users')
