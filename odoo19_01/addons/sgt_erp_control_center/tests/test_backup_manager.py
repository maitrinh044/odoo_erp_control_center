# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from odoo.tests import common
from odoo import fields

class TestSgtErpBackupManager(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Backup = cls.env['sgt.erp.backup']
        cls.Config = cls.env['sgt.erp.config']
        cls.config_rec = cls.Config.search([], limit=1)
        if not cls.config_rec:
            cls.config_rec = cls.Config.create({
                'name': 'Test Config',
                'backup_auto_enabled': True,
                'backup_retention_days': 14,
            })
        else:
            cls.config_rec.write({
                'backup_auto_enabled': True,
                'backup_retention_days': 14,
            })

    def test_01_manual_backup_creation(self):
        """Kiểm tra quy trình tạo bản sao lưu thủ công (1-Chạm)"""
        backup = self.Backup.create_backup(backup_type='zip', backup_mode='manual')
        self.assertEqual(backup.state, 'success', f"Backup failed: {backup.error_log}")
        self.assertTrue(backup.name.endswith('.zip'))
        self.assertGreater(backup.file_size_mb, 0.0)
        self.assertTrue(os.path.exists(backup.file_path))

    def test_02_backup_status_and_health_integration(self):
        """Kiểm tra tích hợp trạng thái Backup với Health Dashboard"""
        backup_dir = self.Backup._get_backup_dir()
        dummy_file = os.path.join(backup_dir, "test_health_backup.zip")
        with open(dummy_file, 'w') as f:
            f.write("test")
        self.Backup.create({
            'name': 'test_health_backup.zip',
            'backup_date': fields.Datetime.now(),
            'db_name': self.env.cr.dbname,
            'backup_type': 'zip',
            'backup_mode': 'manual',
            'file_path': dummy_file,
            'state': 'success',
            'file_size_mb': 1.5,
        })

        self.config_rec.action_check_backup_status()
        self.assertEqual(self.config_rec.backup_status, 'ok')
        self.assertTrue(self.config_rec.backup_last_date)
        self.assertGreaterEqual(self.config_rec.backup_count, 1)

    def test_03_automated_backup_cron(self):
        """Kiểm tra hàm thực thi sao lưu tự động định kỳ qua Cronjob"""
        initial_count = self.Backup.search_count([('backup_mode', '=', 'cron')])
        self.config_rec.write({'backup_default_type': 'dump'})
        self.Backup.cron_run_automated_backup()
        new_count = self.Backup.search_count([('backup_mode', '=', 'cron')])
        self.assertGreater(new_count, initial_count)

    def test_04_retention_cleanup(self):
        """Kiểm tra tự động dọn dẹp các bản sao lưu cũ vượt quá số ngày lưu trữ"""
        backup_dir = self.Backup._get_backup_dir()
        dummy_file = os.path.join(backup_dir, "test_old_backup_to_clean.zip")
        with open(dummy_file, 'w') as f:
            f.write("dummy backup content")

        old_date = fields.Datetime.now() - timedelta(days=20)
        old_record = self.Backup.create({
            'name': 'test_old_backup_to_clean.zip',
            'backup_date': old_date,
            'db_name': self.env.cr.dbname,
            'backup_type': 'zip',
            'backup_mode': 'manual',
            'file_path': dummy_file,
            'state': 'success',
            'file_size_mb': 0.01,
        })

        self.assertTrue(old_record.exists())
        self.assertTrue(os.path.exists(dummy_file))

        # Kích hoạt cleanup với retention 14 ngày
        self.Backup._cleanup_old_backups(retention_days=14)

        self.assertFalse(old_record.exists())
        self.assertFalse(os.path.exists(dummy_file))

    def test_05_download_action_and_deletion(self):
        """Kiểm tra action tải về và action xóa bản sao lưu"""
        backup_dir = self.Backup._get_backup_dir()
        test_file = os.path.join(backup_dir, "test_download_delete.zip")
        with open(test_file, 'w') as f:
            f.write("download test content")
        backup = self.Backup.create({
            'name': 'test_download_delete.zip',
            'backup_date': fields.Datetime.now(),
            'db_name': self.env.cr.dbname,
            'backup_type': 'zip',
            'backup_mode': 'manual',
            'file_path': test_file,
            'state': 'success',
            'file_size_mb': 0.05,
        })

        # Test action download
        action = backup.action_download_backup()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertIn(f"/sgt_erp/backup/download/{backup.id}", action['url'])

        # Test action delete
        file_path = backup.file_path
        backup.action_delete_backup()
        self.assertFalse(backup.exists())
        self.assertFalse(os.path.exists(file_path))
