# -*- coding: utf-8 -*-
import os
import shutil
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.service import db as odoo_db
from odoo.tools import config as odoo_config

_logger = logging.getLogger(__name__)

class SgtErpBackup(models.Model):
    _name = 'sgt.erp.backup'
    _description = 'SGT ERP Backup Record'
    _order = 'backup_date desc, id desc'

    name = fields.Char(string='Tên File Sao Lưu', required=True, readonly=True)
    backup_date = fields.Datetime(string='Thời Gian Tạo', default=fields.Datetime.now, readonly=True)
    db_name = fields.Char(string='Cơ Sở Dữ Liệu', readonly=True)
    backup_type = fields.Selection([
        ('zip', 'Đầy Đủ (Database + Filestore .zip)'),
        ('dump', 'Chỉ Database (SQL Dump .dump)'),
    ], default='zip', string='Định Dạng', required=True)
    backup_mode = fields.Selection([
        ('manual', 'Thủ Công (1-Chạm)'),
        ('cron', 'Tự Động (Lịch Định Kỳ)'),
    ], default='manual', string='Chế Độ', readonly=True)
    file_size_mb = fields.Float(string='Dung Lượng (MB)', digits=(12, 2), readonly=True)
    file_path = fields.Char(string='Đường Dẫn Vật Lý', readonly=True)
    state = fields.Selection([
        ('running', 'Đang thực hiện...'),
        ('success', 'Thành công'),
        ('failed', 'Thất bại'),
    ], default='running', string='Trạng Thái', readonly=True)
    error_log = fields.Text(string='Nhật Ký Lỗi', readonly=True)
    company_id = fields.Many2one('res.company', string='Công Ty', default=lambda self: self.env.company)

    @api.model
    def _get_backup_dir(self):
        """Lấy hoặc khởi tạo thư mục lưu trữ backup trên hệ thống file bền vững."""
        # Ưu tiên thư mục /var/lib/odoo/backups (được mount volume Docker)
        primary_dir = '/var/lib/odoo/backups'
        if not os.path.exists(primary_dir):
            try:
                os.makedirs(primary_dir, exist_ok=True)
                return primary_dir
            except Exception as e:
                _logger.warning("Could not create primary backup dir %s: %s", primary_dir, e)
        else:
            return primary_dir

        # Fallback về data_dir/backups
        fallback_dir = os.path.join(odoo_config.get('data_dir', '/tmp'), 'backups')
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    @api.model
    def create_backup(self, backup_type='zip', backup_mode='manual'):
        """Thực hiện quy trình sao lưu Database và lưu file vào đĩa vật lý."""
        db_name = self.env.cr.dbname
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'zip' if backup_type == 'zip' else 'dump'
        filename = f"backup_{db_name}_{timestamp}.{ext}"
        backup_dir = self._get_backup_dir()
        target_path = os.path.join(backup_dir, filename)

        record = self.create({
            'name': filename,
            'backup_date': fields.Datetime.now(),
            'db_name': db_name,
            'backup_type': backup_type,
            'backup_mode': backup_mode,
            'file_path': target_path,
            'state': 'running',
            'company_id': self.env.company.id,
        })
        if not getattr(self.env.registry, 'test_mode', False) and not odoo_config.get('test_enable', False):
            self.env.cr.commit()
        else:
            self.env.cr.flush()

        try:
            _logger.info("SGT ERP Backup starting for database %s (format: %s, target: %s)", db_name, backup_type, target_path)
            with open(target_path, 'wb') as target_file:
                odoo_db.dump_db(db_name, target_file, backup_format=backup_type, with_filestore=(backup_type == 'zip'))

            file_size_bytes = os.path.getsize(target_path)
            file_size_mb = round(file_size_bytes / (1024.0 * 1024.0), 2)

            record.write({
                'file_size_mb': file_size_mb,
                'state': 'success',
            })

            # Cập nhật thông số Backup trên sgt.erp.config và Health Dashboard
            configs = self.env['sgt.erp.config'].search([])
            if configs:
                configs.write({
                    'backup_status': 'ok',
                    'backup_last_date': fields.Datetime.now(),
                })

            _logger.info("SGT ERP Backup successfully created: %s (Size: %.2f MB)", target_path, file_size_mb)

            # Tự động dọn dẹp các bản backup cũ
            self._cleanup_old_backups()

        except Exception as e:
            _logger.error("SGT ERP Backup failed for %s: %s", db_name, e, exc_info=True)
            record.write({
                'state': 'failed',
                'error_log': str(e),
            })
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass

        return record

    def action_trigger_backup_now(self):
        """Action nút bấm 1-chạm tạo bản sao lưu ngay lập tức."""
        backup_type = self.env.context.get('backup_type', 'zip')
        record = self.create_backup(backup_type=backup_type, backup_mode='manual')
        if record.state == 'success':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Sao lưu hoàn tất!"),
                    'message': _("Đã tạo thành công bản sao lưu %(name)s (Dung lượng: %(size).2f MB).") % {
                        'name': record.name,
                        'size': record.file_size_mb,
                    },
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        else:
            raise UserError(_("Tiến trình sao lưu thất bại: %s") % (record.error_log or _("Lỗi không xác định.")))

    def action_download_backup(self):
        """Action tải file backup trực tiếp về máy tính."""
        self.ensure_one()
        if self.state != 'success' or not self.file_path or not os.path.exists(self.file_path):
            raise UserError(_("File sao lưu không tồn tại hoặc đã bị xóa khỏi máy chủ."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sgt_erp/backup/download/{self.id}',
            'target': 'self',
        }

    def action_delete_backup(self):
        """Xóa bản ghi và giải phóng file vật lý trên đĩa."""
        for rec in self:
            if rec.file_path and os.path.exists(rec.file_path):
                try:
                    os.remove(rec.file_path)
                    _logger.info("Deleted backup physical file: %s", rec.file_path)
                except Exception as e:
                    _logger.warning("Could not delete file %s: %s", rec.file_path, e)
        return self.unlink()

    @api.model
    def cron_run_automated_backup(self):
        """Phương thức định kỳ được gọi bởi Cronjob."""
        config = self.env['sgt.erp.config'].search([], limit=1)
        if config and not config.backup_auto_enabled:
            _logger.info("SGT ERP Automated Backup is disabled in configuration. Skipping.")
            return

        b_type = (config and config.backup_default_type) or 'zip'
        _logger.info("SGT ERP Cron: Running scheduled automated backup (Type: %s)...", b_type)
        self.create_backup(backup_type=b_type, backup_mode='cron')

    def action_cleanup_old_backups(self):
        """Action nút bấm dọn dẹp các bản sao lưu cũ quá hạn."""
        deleted_count = self._cleanup_old_backups()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Dọn dẹp hoàn tất!"),
                'message': _("Đã dọn dẹp %(count)d bản sao lưu cũ quá hạn lưu trữ.") % {'count': deleted_count} if deleted_count else _("Không có bản sao lưu nào quá hạn lưu trữ."),
                'type': 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    @api.model
    def _cleanup_old_backups(self, retention_days=None):
        """Xóa các bản backup cũ vượt quá số ngày lưu trữ cho phép để tiết kiệm đĩa."""
        if retention_days is None:
            config = self.env['sgt.erp.config'].search([], limit=1)
            retention_days = (config and config.backup_retention_days) or 14

        cutoff_date = fields.Datetime.now() - timedelta(days=retention_days)
        old_backups = self.search([
            ('backup_date', '<', cutoff_date),
            ('state', 'in', ['success', 'failed']),
        ])
        count = len(old_backups)
        if old_backups:
            _logger.info("Cleaning up %d old backup records older than %d days...", count, retention_days)
            for b in old_backups:
                if b.file_path and os.path.exists(b.file_path):
                    try:
                        os.remove(b.file_path)
                    except Exception as e:
                        _logger.warning("Could not remove old backup file %s: %s", b.file_path, e)
            old_backups.unlink()
        return count
