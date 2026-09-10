# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import timedelta

class TestSgtErpLicenseServer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.License = cls.env['sgt.erp.license']

    def test_01_license_local_verification(self):
        """Kiểm tra xác thực giấy phép ở chế độ cục bộ (Offline)"""
        lic = self.License.create({
            'name': 'Local Enterprise License',
            'customer_name': 'Saigon Trade Test Corp',
            'license_key': 'SGT-LOC-12345',
            'mode': 'local',
            'status': 'active',
        })
        res = lic.action_verify_online_license()
        self.assertEqual(res.get('params', {}).get('type'), 'info')
        self.assertEqual(lic.status, 'active')

    def test_02_license_online_verification(self):
        """Kiểm tra xác thực giấy phép ở chế độ trực tuyến (Online License Server)"""
        lic = self.License.create({
            'name': 'Online Enterprise License',
            'customer_name': 'Saigon Trade Test Corp',
            'license_key': 'SGT-ENT-99999-ONLINE',
            'mode': 'online',
            'status': 'trial',
        })
        res = lic.action_verify_online_license()
        self.assertEqual(lic.status, 'active')
        self.assertTrue(lic.last_sync_date)

    def test_03_license_expiration_warning(self):
        """Kiểm tra tự động tính toán cảnh báo thời hạn giấy phép"""
        today = fields.Date.context_today(self.env.user)
        
        # 1. Bản quyền hết hạn
        expired_lic = self.License.create({
            'name': 'Expired License',
            'customer_name': 'Expired Corp',
            'status': 'expired',
            'expiration_date': today - timedelta(days=1),
        })
        self.assertTrue(expired_lic.license_warning)
        self.assertIn("WARNING: License has expired", expired_lic.license_warning)

        # 2. Bản quyền sắp hết hạn (dưới 15 ngày)
        expiring_lic = self.License.create({
            'name': 'Expiring License',
            'customer_name': 'Expiring Corp',
            'status': 'active',
            'expiration_date': today + timedelta(days=5),
        })
        self.assertTrue(expiring_lic.license_warning)
        self.assertIn("ATTENTION: License will expire in 5 days", expiring_lic.license_warning)

    def test_04_automatic_status_update_on_expiration_date(self):
        """Kiểm tra tự động chuyển status sang 'expired' hoặc 'expiring' khi sửa ngày hết hạn"""
        today = fields.Date.context_today(self.env.user)

        # Tạo giấy phép ban đầu còn hạn
        lic = self.License.create({
            'name': 'Dynamic Status License',
            'customer_name': 'Dynamic Corp',
            'expiration_date': today + timedelta(days=60),
        })
        self.assertEqual(lic.status, 'active')

        # Đổi ngày sang quá khứ (ví dụ 1/9/2026) -> status phải tự động đổi sang 'expired'
        lic.expiration_date = today - timedelta(days=3)
        self.assertEqual(lic.status, 'expired', "Trạng thái phải tự động nhảy sang 'expired' khi ngày hết hạn ở quá khứ")

        # Đổi ngày sang sắp hết hạn (< 15 ngày) -> status phải tự động đổi sang 'expiring'
        lic.expiration_date = today + timedelta(days=7)
        self.assertEqual(lic.status, 'expiring', "Trạng thái phải tự động nhảy sang 'expiring' khi còn dưới 15 ngày")

        # Đổi ngày sang dài hạn (> 15 ngày) -> status phải tự động đổi sang 'active'
        lic.expiration_date = today + timedelta(days=90)
        self.assertEqual(lic.status, 'active', "Trạng thái phải tự động quay lại 'active' khi gia hạn dài hạn")
