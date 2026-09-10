# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpWorkflowLevel(models.Model):
    _name = 'sgt.erp.workflow.level'
    _description = 'SGT ERP Workflow Approval Level'
    _order = 'workflow_id, sequence asc, id asc'

    name = fields.Char(string='Tên cấp duyệt', required=True)
    workflow_id = fields.Many2one('sgt.erp.workflow', string='Quy trình', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Thứ tự cấp', default=10)

    approver_type = fields.Selection([
        ('user', 'Người dùng chỉ định'),
        ('group', 'Nhóm quyền'),
        ('both', 'Người dùng hoặc Nhóm quyền')
    ], string='Loại người duyệt', default='user', required=True)

    approver_user_ids = fields.Many2many(
        'res.users',
        'sgt_erp_wf_level_user_rel',
        'level_id',
        'user_id',
        string='Người duyệt chỉ định'
    )
    approver_group_id = fields.Many2one('res.groups', string='Nhóm quyền phê duyệt')

    # Hạn mức kích hoạt cấp này
    amount_min = fields.Float(string='Hạn mức tối thiểu', default=0.0,
                              help='Cấp này chỉ được kích hoạt nếu giá trị chứng từ >= hạn mức này. Đặt 0 nếu luôn yêu cầu.')
    amount_max = fields.Float(string='Hạn mức tối đa', default=0.0,
                              help='Đặt 0 nếu không giới hạn mức trần.')

    auto_notification = fields.Boolean(string='Gửi thông báo khi đến lượt duyệt', default=True)
    description = fields.Char(string='Mô tả / Ghi chú')

    def check_user_can_approve(self, user=None):
        """Kiểm tra user có quyền duyệt ở cấp độ này không."""
        self.ensure_one()
        user = user or self.env.user
        if user.has_group('base.group_system'):
            return True
        level_sudo = self.sudo()
        if level_sudo.approver_type in ('user', 'both') and user.id in level_sudo.approver_user_ids.ids:
            return True
        if level_sudo.approver_type in ('group', 'both') and level_sudo.approver_group_id:
            user_groups = user.sudo().all_group_ids if hasattr(user, 'all_group_ids') else user.sudo().group_ids
            if level_sudo.approver_group_id in user_groups:
                return True
        return False
