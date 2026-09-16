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
        """Test license verification in local mode (Offline)"""
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
        """Test license verification in online mode (Online License Server)"""
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
        """Test automatic expiration warning calculation"""
        today = fields.Date.context_today(self.env.user)
        
        # 1. Expired license
        expired_lic = self.License.create({
            'name': 'Expired License',
            'customer_name': 'Expired Corp',
            'status': 'expired',
            'expiration_date': today - timedelta(days=1),
        })
        self.assertTrue(expired_lic.license_warning)
        self.assertIn("WARNING: License has expired", expired_lic.license_warning)

        # 2. Expiring license (under 15 days)
        expiring_lic = self.License.create({
            'name': 'Expiring License',
            'customer_name': 'Expiring Corp',
            'status': 'active',
            'expiration_date': today + timedelta(days=5),
        })
        self.assertTrue(expiring_lic.license_warning)
        self.assertIn("ATTENTION: License will expire in 5 days", expiring_lic.license_warning)

    def test_04_automatic_status_update_on_expiration_date(self):
        """Test automatic status update to 'expired' or 'expiring' on expiration date changes"""
        today = fields.Date.context_today(self.env.user)

        # Create license with future expiration date
        lic = self.License.create({
            'name': 'Dynamic Status License',
            'customer_name': 'Dynamic Corp',
            'expiration_date': today + timedelta(days=60),
        })
        self.assertEqual(lic.status, 'active')

        # Change date to the past -> status must automatically update to 'expired'
        lic.expiration_date = today - timedelta(days=3)
        self.assertEqual(lic.status, 'expired', "Status must automatically update to 'expired' when expiration date is in the past")

        # Change date to near future (< 15 days) -> status must automatically update to 'expiring'
        lic.expiration_date = today + timedelta(days=7)
        self.assertEqual(lic.status, 'expiring', "Status must automatically update to 'expiring' when under 15 days remain")

        # Change date to long-term (> 15 days) -> status must automatically revert to 'active'
        lic.expiration_date = today + timedelta(days=90)
        self.assertEqual(lic.status, 'active', "Status must automatically revert to 'active' when renewed long-term")
