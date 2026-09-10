# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.sgt_erp_control_center.controllers.health_controller import SgtSystemHealthController

class TestHealthLiveStats(TransactionCase):

    def setUp(self):
        super().setUp()
        self.controller = SgtSystemHealthController()

    def test_live_stats_structure(self):
        """Kiểm tra JSON-RPC endpoint trả về đầy đủ các trường dữ liệu đo phần cứng thời gian thực"""
        stats = self.controller.get_live_stats(env=self.env)
        
        # Kiểm tra các khối chỉ số chính
        self.assertIn('cpu', stats)
        self.assertIn('ram', stats)
        self.assertIn('storage', stats)
        self.assertIn('system', stats)

        # Kiểm tra chi tiết CPU
        cpu = stats['cpu']
        self.assertIn('percentage', cpu)
        self.assertIn('cores', cpu)
        self.assertIn('load_1m', cpu)
        self.assertIn('load_5m', cpu)
        self.assertIn('load_15m', cpu)
        self.assertIn('model', cpu)
        self.assertGreaterEqual(cpu['cores'], 1)
        self.assertGreaterEqual(cpu['percentage'], 0.0)
        self.assertLessEqual(cpu['percentage'], 100.0)

        # Kiểm tra chi tiết RAM
        ram = stats['ram']
        self.assertIn('percentage', ram)
        self.assertIn('used_gb', ram)
        self.assertIn('free_gb', ram)
        self.assertIn('total_gb', ram)
        self.assertGreaterEqual(ram['percentage'], 0.0)
        self.assertLessEqual(ram['percentage'], 100.0)

        # Kiểm tra chi tiết Storage
        storage = stats['storage']
        self.assertIn('os_disk_percentage', storage)
        self.assertIn('data_disk_percentage', storage)
        self.assertIn('database_size_mb', storage)

        # Kiểm tra chi tiết System
        system = stats['system']
        self.assertIn('active_connections', system)
        self.assertIn('uptime', system)
        self.assertIn('server_time', system)
        self.assertGreaterEqual(system['active_connections'], 1)
