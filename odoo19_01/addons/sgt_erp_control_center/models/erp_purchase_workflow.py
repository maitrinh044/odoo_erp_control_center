# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sgt_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('to_approve', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='not_required', copy=False, tracking=True)

    sgt_approver_id = fields.Many2one('res.users', string='Approver', copy=False, readonly=True)
    sgt_approval_date = fields.Datetime(string='Approval Date', copy=False, readonly=True)
    sgt_approval_workflow_id = fields.Many2one('sgt.erp.workflow', string='Approval Workflow', copy=False)
    sgt_rejection_reason = fields.Text(string='Rejection Reason', copy=False, readonly=True)

    # Multi-level Approval Tracking
    sgt_approval_line_ids = fields.One2many(
        'sgt.erp.approval.line', 'purchase_order_id',
        string='Multi-Level Approval Progress',
        copy=False
    )
    sgt_current_approval_line_id = fields.Many2one(
        'sgt.erp.approval.line',
        string='Current Approval Stage',
        compute='_compute_current_approval_line',
        store=True
    )
    sgt_can_current_user_approve = fields.Boolean(
        string='Can I Approve Current Stage',
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

    def _get_applicable_purchase_workflow(self):
        """Find applicable workflow rule for this purchase order."""
        self.ensure_one()
        if self.sgt_approval_workflow_id:
            return self.sgt_approval_workflow_id.sudo()
        Workflow = self.env['sgt.erp.workflow'].sudo()
        domain = [
            ('active', '=', True),
            ('require_approval', '=', True),
            ('workflow_type', '=', 'purchase'),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id or self.env.company.id)
        ]
        workflows = Workflow.search(domain, order='amount_threshold desc, id desc')
        for wf in workflows:
            if wf.amount_threshold > 0 and self.amount_total < wf.amount_threshold:
                continue
            return wf
        return False

    def _generate_purchase_approval_lines(self, rule):
        """Generate approval stages automatically according to purchase workflow config."""
        self.ensure_one()
        existing_lines = self.sgt_approval_line_ids.filtered(lambda l: l.state in ('waiting', 'pending'))
        if existing_lines:
            existing_lines.unlink()

        levels = rule.get_applicable_levels(self.amount_total)
        lines_vals = []
        if levels:
            for idx, lvl in enumerate(levels):
                if rule.approval_mode == 'direct':
                    state = 'pending'
                else:
                    state = 'pending' if idx == 0 else 'waiting'
                lines_vals.append({
                    'name': lvl.name,
                    'res_model': 'purchase.order',
                    'res_id': self.id,
                    'purchase_order_id': self.id,
                    'workflow_id': rule.id,
                    'level_id': lvl.id,
                    'sequence': lvl.sequence,
                    'state': state,
                    'approver_user_ids': [(6, 0, lvl.approver_user_ids.ids)],
                    'approver_group_id': lvl.approver_group_id.id if lvl.approver_group_id else False,
                })
        else:
            lines_vals.append({
                'name': _("Purchase Threshold Approval [%s]") % rule.name,
                'res_model': 'purchase.order',
                'res_id': self.id,
                'purchase_order_id': self.id,
                'workflow_id': rule.id,
                'sequence': 10,
                'state': 'pending',
                'approver_user_ids': [(6, 0, rule.approver_user_ids.ids)],
                'approver_group_id': rule.approver_group_id.id if rule.approver_group_id else False,
            })

        for val in lines_vals:
            self.env['sgt.erp.approval.line'].sudo().create(val)

    def button_confirm(self):
        """Intercept purchase order confirmation to enforce multi-level approval."""
        for order in self:
            if order.sgt_approval_state == 'approved':
                continue

            rule = order._get_applicable_purchase_workflow()
            if not rule:
                continue

            if order.sgt_approval_state == 'to_approve':
                current_line = order.sgt_current_approval_line_id
                if current_line and current_line.check_user_can_approve(self.env.user):
                    current_line.action_approve(user=self.env.user)
                    if order.sgt_approval_state != 'approved':
                        raise UserError(_(
                            "You approved stage [%(level)s]. Purchase order is awaiting subsequent approval stages."
                        ) % {'level': current_line.name})
                elif rule.check_user_can_approve(self.env.user):
                    order.write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                    })
                    order.message_post(body=_(
                        "<b>Purchase order directly approved by %(user)s</b>"
                    ) % {'user': self.env.user.name})
                else:
                    raise UserError(_(
                        "Purchase order #%(name)s (%(amount)s %(currency)s) is pending approval. You do not have approval authority."
                    ) % {
                        'name': order.name,
                        'amount': '{:,.0f}'.format(order.amount_total),
                        'currency': order.currency_id.symbol or '',
                    })
            else:
                # Initiate approval flow
                levels = rule.get_applicable_levels(order.amount_total)
                if not levels and rule.check_user_can_approve(self.env.user):
                    order.write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                    })
                    order.message_post(body=_(
                        "Purchase order automatically approved because %(user)s has approval rights."
                    ) % {'user': self.env.user.name})
                else:
                    order._generate_purchase_approval_lines(rule)
                    order.write({
                        'sgt_approval_state': 'to_approve',
                        'sgt_approval_workflow_id': rule.id,
                    })
                    first_line = order.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')[:1]
                    if first_line and first_line.check_user_can_approve(self.env.user):
                        first_line.action_approve(user=self.env.user)
                        if order.sgt_approval_state == 'approved':
                            continue
                        raise UserError(_(
                            "You approved stage [%(level)s]. Purchase order is awaiting subsequent approval stages."
                        ) % {'level': first_line.name})
                    else:
                        approvers_str = rule.approver_group_id.name if rule.approver_group_id else ", ".join(rule.approver_user_ids.mapped('name'))
                        order.message_post(body=_(
                            "<b>Purchase order approval required!</b><br/>Total: %(amount)s %(currency)s exceeds threshold limit. Authorized approval (%(approvers)s) is required."
                        ) % {
                            'amount': '{:,.0f}'.format(order.amount_total),
                            'currency': order.currency_id.symbol or '',
                            'approvers': approvers_str or _("Administrator"),
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Purchase Approval Required'),
                                'message': _(
                                    "Purchase order %(name)s exceeds threshold (%(threshold)s %(currency)s). "
                                    "Moved to 'Pending Approval'."
                                ) % {
                                    'name': order.name,
                                    'threshold': '{:,.0f}'.format(rule.amount_threshold),
                                    'currency': order.currency_id.symbol or '',
                                },
                                'type': 'warning',
                                'sticky': False,
                            }
                        }

        unconfirmed = self.filtered(lambda o: o.state in ('draft', 'sent', 'to approve'))
        if unconfirmed:
            return super(PurchaseOrder, unconfirmed).button_confirm()
        return True

    def action_request_approval(self):
        """Manually submit purchase order for approval."""
        self.ensure_one()
        rule = self._get_applicable_purchase_workflow()
        if not rule:
            raise UserError(_("No applicable purchase approval rule found for this order."))
        self._generate_purchase_approval_lines(rule)
        self.write({
            'sgt_approval_state': 'to_approve',
            'sgt_approval_workflow_id': rule.id,
        })
        self.message_post(body=_("Purchase order approval request submitted."))
        return True

    def action_open_approve_wizard(self):
        """Open approval modal wizard for purchase order."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        return {
            'name': _("Approve Purchase Order"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_line_id': line.id if line else False,
                'default_res_model': 'purchase.order',
                'default_res_id': self.id,
                'default_action_type': 'approve',
            }
        }

    def action_open_reject_wizard(self):
        """Open rejection modal wizard for purchase order."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        return {
            'name': _("Reject Purchase Order"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_line_id': line.id if line else False,
                'default_res_model': 'purchase.order',
                'default_res_id': self.id,
                'default_action_type': 'reject',
            }
        }
