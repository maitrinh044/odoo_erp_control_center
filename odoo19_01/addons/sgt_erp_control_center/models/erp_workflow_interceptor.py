# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sgt_approval_state = fields.Selection([
        ('not_required', 'Không yêu cầu duyệt'),
        ('to_approve', 'Chờ phê duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái phê duyệt', default='not_required', copy=False, tracking=True)

    sgt_approver_id = fields.Many2one('res.users', string='Người duyệt', copy=False, readonly=True)
    sgt_approval_date = fields.Datetime(string='Ngày duyệt', copy=False, readonly=True)
    sgt_approval_workflow_id = fields.Many2one('sgt.erp.workflow', string='Quy trình phê duyệt', copy=False)

    # Multi-level Approval Tracking
    sgt_approval_line_ids = fields.One2many(
        'sgt.erp.approval.line', 'sale_order_id',
        string='Tiến trình duyệt đa cấp',
        copy=False
    )
    sgt_current_approval_line_id = fields.Many2one(
        'sgt.erp.approval.line',
        string='Cấp duyệt hiện tại',
        compute='_compute_current_approval_line',
        store=True
    )
    sgt_can_current_user_approve = fields.Boolean(
        string='Tôi có quyền duyệt cấp này',
        compute='_compute_can_current_user_approve'
    )

    @api.depends('sgt_approval_line_ids.state')
    def _compute_current_approval_line(self):
        for order in self:
            pending = order.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
            order.sgt_current_approval_line_id = pending[:1] if pending else False

    def _compute_can_current_user_approve(self):
        for order in self:
            line = order.sgt_current_approval_line_id
            if line:
                order.sgt_can_current_user_approve = line.check_user_can_approve(self.env.user)
            elif order.sgt_approval_workflow_id and order.sgt_approval_state == 'to_approve':
                order.sgt_can_current_user_approve = order.sgt_approval_workflow_id.check_user_can_approve(self.env.user)
            else:
                order.sgt_can_current_user_approve = False

    def _generate_approval_lines(self, rule):
        """Sinh các cấp duyệt tự động theo cấu hình workflow đa cấp."""
        self.ensure_one()
        # Xóa các dòng cũ chưa duyệt nếu có
        existing_lines = self.sgt_approval_line_ids.filtered(lambda l: l.state in ('waiting', 'pending'))
        if existing_lines:
            existing_lines.unlink()

        levels = rule.get_applicable_levels(self.amount_total)
        lines_vals = []
        if levels:
            for idx, lvl in enumerate(levels):
                state = 'pending' if idx == 0 else 'waiting'
                lines_vals.append({
                    'name': lvl.name,
                    'res_model': 'sale.order',
                    'res_id': self.id,
                    'sale_order_id': self.id,
                    'workflow_id': rule.id,
                    'level_id': lvl.id,
                    'sequence': lvl.sequence,
                    'state': state,
                    'approver_user_ids': [(6, 0, lvl.approver_user_ids.ids)],
                    'approver_group_id': lvl.approver_group_id.id if lvl.approver_group_id else False,
                })
        else:
            # Fallback nếu workflow đơn cấp
            lines_vals.append({
                'name': _("Phê duyệt theo hạn mức [%s]") % rule.name,
                'res_model': 'sale.order',
                'res_id': self.id,
                'sale_order_id': self.id,
                'workflow_id': rule.id,
                'sequence': 10,
                'state': 'pending',
                'approver_user_ids': [(6, 0, rule.approver_user_ids.ids)],
                'approver_group_id': rule.approver_group_id.id if rule.approver_group_id else False,
            })

        return self.env['sgt.erp.approval.line'].create(lines_vals)

    def action_open_approve_wizard(self):
        """Mở dialog nhập ý kiến phê duyệt."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        if not line:
            # Fallback nếu đơn cấp
            return self.action_approve_order()
        return {
            'name': _("Xác nhận Phê duyệt"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': line.id,
                'default_action_type': 'approve',
            }
        }

    def action_open_reject_wizard(self):
        """Mở dialog nhập lý do từ chối."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        if not line:
            return self.action_reject_order()
        return {
            'name': _("Xác nhận Từ chối"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': line.id,
                'default_action_type': 'reject',
            }
        }

    def action_request_approval(self):
        """Send approval request to authorized approvers."""
        for order in self:
            rule = order.sgt_approval_workflow_id.sudo() if order.sgt_approval_workflow_id else self.env['sgt.erp.workflow'].sudo().get_approval_rule('sale.order', order.company_id, order.amount_total)
            order.sudo().write({
                'sgt_approval_state': 'to_approve',
                'sgt_approval_workflow_id': rule.id if rule else False,
            })
            if rule:
                order._generate_approval_lines(rule)
            approver_names = ', '.join(rule.approver_user_ids.mapped('name')) if rule and rule.approver_user_ids else _("Ban Quản lý")
            order.message_post(
                body=_(
                    "Đơn hàng đã được gửi yêu cầu phê duyệt đến %(approvers)s do giá trị đơn hàng vượt hạn mức (%(amount)s %(currency)s)."
                ) % {
                    'approvers': approver_names,
                    'amount': f"{order.amount_total:,.2f}",
                    'currency': order.currency_id.symbol or '',
                }
            )
        return True

    def action_approve_order(self):
        """Approve the order by an authorized approver and proceed to confirm."""
        for order in self:
            # Nếu có approval lines, thực thi cấp hiện tại
            line = order.sgt_current_approval_line_id
            if line:
                line.action_approve(user=self.env.user)
                continue

            rule = order.sgt_approval_workflow_id or self.env['sgt.erp.workflow'].sudo().get_approval_rule('sale.order', order.company_id, order.amount_total)
            if rule and not rule.check_user_can_approve(self.env.user):
                raise AccessError(_("Bạn không có thẩm quyền phê duyệt đơn hàng này theo quy định quy trình [%s].") % rule.name)
            
            order.sudo().write({
                'sgt_approval_state': 'approved',
                'sgt_approver_id': self.env.user.id,
                'sgt_approval_date': fields.Datetime.now(),
                'sgt_approval_workflow_id': rule.id if rule else False,
            })
            order.message_post(
                body=_("Đơn hàng đã được phê duyệt thành công bởi <b>%s</b>.") % self.env.user.name
            )
            # Proceed to standard confirmation
            order.action_confirm()
        return True

    def action_reject_order(self):
        """Reject the order approval."""
        for order in self:
            line = order.sgt_current_approval_line_id
            if line:
                line.action_reject(user=self.env.user)
                continue

            rule = order.sgt_approval_workflow_id or self.env['sgt.erp.workflow'].sudo().get_approval_rule('sale.order', order.company_id, order.amount_total)
            if rule and not rule.check_user_can_approve(self.env.user):
                raise AccessError(_("Bạn không có thẩm quyền từ chối đơn hàng này theo quy tắc [%s].") % rule.name)

            order.sudo().write({
                'sgt_approval_state': 'rejected',
                'sgt_approver_id': self.env.user.id,
                'sgt_approval_date': fields.Datetime.now(),
            })
            order.message_post(
                body=_("Đơn hàng đã bị từ chối phê duyệt bởi <b>%s</b>.") % self.env.user.name
            )
        return True

    def action_confirm(self):
        """Intercept confirmation to enforce workflow approval thresholds."""
        for order in self:
            if order.sgt_approval_state == 'approved':
                continue

            rule = order.sgt_approval_workflow_id.sudo() if order.sgt_approval_workflow_id else self.env['sgt.erp.workflow'].sudo().get_approval_rule('sale.order', order.company_id, order.amount_total)
            
            # If the order is already in to_approve state
            if order.sgt_approval_state == 'to_approve':
                line = order.sgt_current_approval_line_id
                if line:
                    if line.check_user_can_approve(self.env.user):
                        line.action_approve(user=self.env.user)
                        if order.sgt_approval_state == 'approved':
                            continue
                        else:
                            # Vẫn còn cấp tiếp theo chờ duyệt
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Đã duyệt cấp hiện tại'),
                                    'message': _('Đơn hàng đã chuyển tới cấp duyệt tiếp theo.'),
                                    'type': 'info',
                                    'sticky': False,
                                }
                            }
                    else:
                        raise UserError(
                            _(
                                "Đơn hàng %(name)s đang ở trạng thái 'Chờ phê duyệt' (%(level)s). "
                                "Vui lòng liên hệ người có thẩm quyền để duyệt trước khi xác nhận đơn."
                            ) % {'name': order.name, 'level': line.name}
                        )

                # Fallback nếu không có lines
                if rule and rule.check_user_can_approve(self.env.user):
                    order.sudo().write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                        'sgt_approval_workflow_id': rule.id if rule else False,
                    })
                    order.message_post(
                        body=_("Đơn hàng được phê duyệt tự động bởi người có thẩm quyền: <b>%s</b>.") % self.env.user.name
                    )
                    continue
                else:
                    raise UserError(
                        _(
                            "Đơn hàng %(name)s đang ở trạng thái 'Chờ phê duyệt'. "
                            "Vui lòng liên hệ người có thẩm quyền để duyệt trước khi xác nhận đơn."
                        ) % {'name': order.name}
                    )

            # Check threshold for new confirmation or manual workflow selection
            should_require_approval = False
            if order.sgt_approval_workflow_id and order.sgt_approval_workflow_id.require_approval:
                should_require_approval = True
            elif rule and rule.amount_threshold > 0 and order.amount_total >= rule.amount_threshold:
                should_require_approval = True

            if should_require_approval and rule:
                # Tạo approval lines
                lines = order._generate_approval_lines(rule)
                pending_line = lines.filtered(lambda l: l.state == 'pending')[:1]
                
                if pending_line and pending_line.check_user_can_approve(self.env.user):
                    # Tự động duyệt cấp 1
                    pending_line.action_approve(user=self.env.user)
                    if order.sgt_approval_state == 'approved':
                        # Tất cả các cấp đã hoàn thành
                        continue
                    else:
                        # Còn cấp tiếp theo, dừng xác nhận
                        order.sudo().write({
                            'sgt_approval_state': 'to_approve',
                            'sgt_approval_workflow_id': rule.id,
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Đã duyệt cấp 1'),
                                'message': _('Đơn hàng đã được tự động duyệt cấp 1 và đang chờ các cấp tiếp theo.'),
                                'type': 'info',
                                'sticky': False,
                            }
                        }

                # User không có quyền duyệt cấp đầu tiên
                order.sudo().write({
                    'sgt_approval_state': 'to_approve',
                    'sgt_approval_workflow_id': rule.id,
                })
                order.message_post(
                    body=_(
                        "Đơn hàng có tổng tiền %(amount)s %(currency)s vượt hạn mức phê duyệt (%(threshold)s %(currency)s). "
                        "Đã chuyển sang trạng thái <b>Chờ phê duyệt</b> theo quy trình [%(rule)s]."
                    ) % {
                        'amount': f"{order.amount_total:,.2f}",
                        'threshold': f"{rule.amount_threshold:,.2f}",
                        'currency': order.currency_id.symbol or '',
                        'rule': rule.name,
                    }
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Chờ Phê Duyệt Hạn Mức'),
                        'message': _(
                            "Đơn hàng %(name)s vượt hạn mức (%(threshold)s %(currency)s). "
                            "Đã chuyển sang trạng thái 'Chờ phê duyệt'."
                        ) % {
                            'name': order.name,
                            'threshold': f"{rule.amount_threshold:,.2f}",
                            'currency': order.currency_id.symbol or '',
                        },
                        'type': 'warning',
                        'sticky': False,
                    }
                }

        orders_to_confirm = self.filtered(lambda o: o.state in ('draft', 'sent'))
        if orders_to_confirm:
            return super(SaleOrder, orders_to_confirm).action_confirm()
        return True


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        """Intercept stage changes on CRM Leads to validate required fields."""
        if 'stage_id' in vals:
            company = self.env.company
            rule = self.env['sgt.erp.workflow'].sudo().get_approval_rule('crm.lead', company)
            if rule and rule.required_fields:
                for lead in self:
                    rule.validate_required_fields(lead)
        return super(CrmLead, self).write(vals)
