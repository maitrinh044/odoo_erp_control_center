# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SgtErpApprovalWizard(models.TransientModel):
    _name = 'sgt.erp.approval.wizard'
    _description = 'Wizard Xác Nhận Phê Duyệt / Từ Chối'

    line_id = fields.Many2one('sgt.erp.approval.line', string='Cấp duyệt cần xử lý', required=True)
    document_reference = fields.Char(related='line_id.document_reference', string='Chứng từ', readonly=True)
    level_name = fields.Char(related='line_id.name', string='Tên cấp duyệt', readonly=True)
    action_type = fields.Selection([
        ('approve', 'Phê duyệt'),
        ('reject', 'Từ chối')
    ], string='Hành động', required=True, default='approve')

    note = fields.Text(string='Ý kiến / Lý do', required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.note or not self.note.strip():
            raise UserError(_("Vui lòng nhập ý kiến hoặc lý do thực hiện."))

        if self.action_type == 'approve':
            self.line_id.action_approve(user=self.env.user, note=self.note.strip())
            title = _("Phê duyệt thành công")
            message = _("Đã phê duyệt [%(level)s] cho chứng từ %(doc)s.") % {
                'level': self.line_id.name,
                'doc': self.line_id.document_reference or '',
            }
            msg_type = 'success'
        else:
            self.line_id.action_reject(user=self.env.user, note=self.note.strip())
            title = _("Đã từ chối phê duyệt")
            message = _("Đã từ chối [%(level)s] của chứng từ %(doc)s.") % {
                'level': self.line_id.name,
                'doc': self.line_id.document_reference or '',
            }
            msg_type = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': msg_type,
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
