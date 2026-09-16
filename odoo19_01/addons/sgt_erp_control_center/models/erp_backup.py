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

    name = fields.Char(string='Backup Archive Name', required=True, readonly=True)
    backup_date = fields.Datetime(string='Created Date', default=fields.Datetime.now, readonly=True)
    db_name = fields.Char(string='Database Name', readonly=True)
    backup_type = fields.Selection([
        ('zip', 'Full (Database + Filestore .zip)'),
        ('dump', 'Database Only (SQL Dump .dump)'),
    ], default='zip', string='Backup Format', required=True)
    backup_mode = fields.Selection([
        ('manual', 'Manual (1-Click)'),
        ('cron', 'Automated (Cron)'),
    ], default='manual', string='Trigger Mode', readonly=True)
    file_size_mb = fields.Float(string='File Size (MB)', digits=(12, 2), readonly=True)
    file_path = fields.Char(string='Physical File Path', readonly=True)
    state = fields.Selection([
        ('running', 'In Progress'),
        ('success', 'Successful'),
        ('failed', 'Failed'),
    ], default='running', string='Status', readonly=True)
    error_log = fields.Text(string='Error Diagnostic Log', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def _get_backup_dir(self):
        """Get or create persistent backup storage directory."""
        primary_dir = '/var/lib/odoo/backups'
        if not os.path.exists(primary_dir):
            try:
                os.makedirs(primary_dir, exist_ok=True)
                return primary_dir
            except Exception as e:
                _logger.warning("Could not create primary backup dir %s: %s", primary_dir, e)
        else:
            return primary_dir

        fallback_dir = os.path.join(odoo_config.get('data_dir', '/tmp'), 'backups')
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    @api.model
    def create_backup(self, backup_type='zip', backup_mode='manual'):
        """Execute database backup process and save physical archive to disk."""
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

            # Update Backup stats in sgt.erp.config and Health Dashboard
            configs = self.env['sgt.erp.config'].search([])
            if configs:
                configs.write({
                    'backup_status': 'ok',
                    'backup_last_date': fields.Datetime.now(),
                })

            _logger.info("SGT ERP Backup successfully created: %s (Size: %.2f MB)", target_path, file_size_mb)

            # Automatically cleanup old backups according to retention policy
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

    def action_trigger_backup_now(self, *args, **kwargs):
        """Action button to trigger immediate 1-click backup."""
        backup_type = self.env.context.get('backup_type', 'zip')
        record = self.create_backup(backup_type=backup_type, backup_mode='manual')
        if record.state == 'success':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Backup Completed!"),
                    'message': _("Successfully created backup archive %(name)s (Size: %(size).2f MB).") % {
                        'name': record.name,
                        'size': record.file_size_mb,
                    },
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        else:
            raise UserError(_("Backup process failed: %s") % (record.error_log or _("Unknown error occurred.")))

    def action_download_backup(self):
        """Download backup archive directly to computer."""
        self.ensure_one()
        if self.state != 'success' or not self.file_path or not os.path.exists(self.file_path):
            raise UserError(_("Backup archive does not exist or has been removed from server."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sgt_erp/backup/download/{self.id}',
            'target': 'self',
        }

    def action_delete_backup(self):
        """Delete record and free physical storage on disk."""
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
        """Automated backup routine invoked by scheduled Cronjob."""
        config = self.env['sgt.erp.config'].search([], limit=1)
        if config and not config.backup_auto_enabled:
            _logger.info("SGT ERP Automated Backup is disabled in configuration. Skipping.")
            return

        b_type = (config and config.backup_default_type) or 'zip'
        _logger.info("SGT ERP Cron: Running scheduled automated backup (Type: %s)...", b_type)
        self.create_backup(backup_type=b_type, backup_mode='cron')

    def action_scan_existing_backups(self, *args, **kwargs):
        """Scan backup directory and synchronize existing disk archives to database."""
        backup_dir = self._get_backup_dir()
        if not os.path.exists(backup_dir):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Notice"),
                    'message': _("Backup storage directory does not exist on the server."),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        created_count = 0
        current_db = self.env.cr.dbname
        existing_paths = set(self.search([]).mapped('file_path'))

        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if not (filename.endswith('.zip') or filename.endswith('.dump')):
                continue
            file_path = os.path.join(backup_dir, filename)
            if file_path in existing_paths or not os.path.isfile(file_path):
                continue

            size_bytes = os.path.getsize(file_path)
            size_mb = round(size_bytes / (1024.0 * 1024.0), 2)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            b_type = 'zip' if filename.endswith('.zip') else 'dump'

            self.create({
                'name': filename,
                'backup_date': mtime,
                'db_name': current_db,
                'backup_type': b_type,
                'backup_mode': 'manual',
                'file_path': file_path,
                'file_size_mb': size_mb,
                'state': 'success',
                'company_id': self.env.company.id,
            })
            created_count += 1

        configs = self.env['sgt.erp.config'].search([])
        if configs:
            configs.write({
                'backup_status': 'ok',
                'backup_last_date': fields.Datetime.now(),
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Backup Archives Synchronized"),
                'message': _("Found and synchronized %d existing backup archive(s) from disk.") % created_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_cleanup_old_backups(self, *args, **kwargs):
        """Action button to cleanup expired backup archives."""
        deleted_count = self._cleanup_old_backups()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Cleanup Completed!"),
                'message': _("Cleaned up %(count)d expired backup archive(s).") % {'count': deleted_count} if deleted_count else _("No expired backup archives found."),
                'type': 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_open_backup_schedule(self, *args, **kwargs):
        """Directly open automated backup Cronjob configuration."""
        cron = self.env.ref('sgt_erp_control_center.cron_sgt_erp_automated_backup', raise_if_not_found=False)
        if not cron:
            cron = self.env['ir.cron'].search([('code', 'ilike', 'cron_run_automated_backup')], limit=1)
        if not cron:
            raise UserError(_("Automated backup cron job not found."))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Configure Automated Backup Schedule"),
            'res_model': 'ir.cron',
            'res_id': cron.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cleanup_old_backups(self, retention_days=None):
        """Purge backups older than configured retention days to preserve storage."""
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
