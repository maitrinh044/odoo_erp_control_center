# -*- coding: utf-8 -*-
import os
import logging
from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

class SgtErpBackupController(http.Controller):

    @http.route('/sgt_erp/backup/download/<int:backup_id>', type='http', auth='user')
    def download_backup_file(self, backup_id, **kwargs):
        """Cho phép quản trị viên tải file sao lưu về máy tính an toàn."""
        if not request.env.user.has_group('sgt_erp_control_center.group_erp_control_center_manager') and not request.env.is_admin():
            raise AccessError(_("Bạn không có quyền tải file sao lưu hệ thống."))

        backup = request.env['sgt.erp.backup'].browse(backup_id)
        if not backup.exists() or not backup.file_path or not os.path.exists(backup.file_path):
            return Response("File sao lưu không tồn tại trên hệ thống hoặc đã bị xóa.", status=404)

        try:
            # Sử dụng Stream chuẩn Odoo 19
            return http.Stream.from_path(backup.file_path).get_response(
                as_attachment=True,
                filename=backup.name,
            )
        except Exception as e:
            _logger.warning("http.Stream failed, falling back to direct byte read: %s", e)
            with open(backup.file_path, 'rb') as f:
                content = f.read()
            mimetype = 'application/zip' if backup.name.endswith('.zip') else 'application/octet-stream'
            headers = [
                ('Content-Type', mimetype),
                ('Content-Disposition', f'attachment; filename="{backup.name}"'),
                ('Content-Length', str(len(content))),
            ]
            return Response(content, headers=headers)
