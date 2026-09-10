# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class SgtErpMassApprovalWizard(models.TransientModel):
    _name = 'sgt.erp.mass.approval.wizard'
    _description = 'SGT ERP Mass Approval Wizard'

    action_type = fields.Selection([
        ('approve', 'Phê duyệt hàng loạt'),
        ('reject', 'Từ chối hàng loạt'),
    ], string='Hành động', default='approve', required=True)

    line_ids = fields.Many2many(
        'sgt.erp.approval.line',
        string='Danh sách cấp duyệt được chọn'
    )

    total_count = fields.Integer(string='Tổng số chứng từ', compute='_compute_counts')
    sale_order_count = fields.Integer(string='Đơn bán hàng', compute='_compute_counts')
    purchase_order_count = fields.Integer(string='Đơn mua hàng', compute='_compute_counts')
    account_move_count = fields.Integer(string='Hóa đơn', compute='_compute_counts')
    other_count = fields.Integer(string='Chứng từ khác', compute='_compute_counts')

    note = fields.Text(
        string='Ý kiến / Lý do',
        help='Ghi chú phê duyệt hoặc lý do từ chối chung cho toàn bộ chứng từ đã chọn.'
    )

    @api.depends('line_ids')
    def _compute_counts(self):
        for wiz in self:
            wiz.total_count = len(wiz.line_ids)
            wiz.sale_order_count = len(wiz.line_ids.filtered(lambda l: l.res_model == 'sale.order' or l.sale_order_id))
            wiz.purchase_order_count = len(wiz.line_ids.filtered(lambda l: l.res_model == 'purchase.order' or l.purchase_order_id))
            wiz.account_move_count = len(wiz.line_ids.filtered(lambda l: l.res_model == 'account.move' or l.account_move_id))
            wiz.other_count = wiz.total_count - (wiz.sale_order_count + wiz.purchase_order_count + wiz.account_move_count)

    def action_confirm_mass_process(self):
        """Thực thi phê duyệt hoặc từ chối hàng loạt."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Vui lòng chọn ít nhất một chứng từ để xử lý."))

        if self.action_type == 'reject' and not (self.note and self.note.strip()):
            raise UserError(_("Vui lòng nhập lý do từ chối bắt buộc khi thực hiện từ chối hàng loạt."))

        success_count = 0
        skipped_count = 0
        skipped_details = []

        for line in self.line_ids:
            if line.state != 'pending':
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: Không ở trạng thái chờ duyệt")
                continue

            if not line.check_user_can_approve(self.env.user):
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: Bạn không có thẩm quyền duyệt cấp này")
                continue

            try:
                if self.action_type == 'approve':
                    line.action_approve(user=self.env.user, note=self.note or _("Phê duyệt hàng loạt"))
                else:
                    line.action_reject(user=self.env.user, note=self.note)
                success_count += 1
            except Exception as e:
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: {str(e)}")

        action_label = _("Phê duyệt") if self.action_type == 'approve' else _("Từ chối")

        message = _(
            "Đã %(action)s thành công %(success)s/%(total)s chứng từ."
        ) % {
            'action': action_label,
            'success': success_count,
            'total': len(self.line_ids),
        }
        if skipped_count > 0:
            message += _(" Bỏ qua %(skipped)s chứng từ do không đủ quyền hoặc trạng thái không hợp lệ.") % {'skipped': skipped_count}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Kết Quả Xử Lý Hàng Loạt"),
                'message': message,
                'type': 'success' if success_count > 0 else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
