# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sgt_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('to_approve', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='not_required', copy=False, tracking=True)

    sgt_approver_id = fields.Many2one('res.users', string='Approver', copy=False, readonly=True)
    sgt_approval_date = fields.Datetime(string='Approval Date', copy=False, readonly=True)
    sgt_approval_workflow_id = fields.Many2one('sgt.erp.workflow', string='Approval Workflow', copy=False)

    # Multi-level Approval Tracking
    sgt_approval_line_ids = fields.One2many(
        'sgt.erp.approval.line', 'sale_order_id',
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

    def _generate_approval_lines(self, rule):
        """Generate approval levels automatically according to multi-level workflow config."""
        self.ensure_one()
        # Remove unapproved previous lines if any
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
            # Fallback for single-level workflow
            lines_vals.append({
                'name': _("Threshold Approval [%s]") % rule.name,
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
        """Open approval modal dialog."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        if not line:
            return self.action_approve_order()
        return {
            'name': _("Confirm Approval"),
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
        """Open rejection modal dialog."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        if not line:
            return self.action_reject_order()
        return {
            'name': _("Confirm Rejection"),
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
            approver_names = ', '.join(rule.approver_user_ids.mapped('name')) if rule and rule.approver_user_ids else _("Management")
            order.message_post(
                body=_(
                    "Approval request sent to %(approvers)s because the order total exceeds the threshold limit (%(amount)s %(currency)s)."
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
            line = order.sgt_current_approval_line_id
            if line:
                line.action_approve(user=self.env.user)
                continue

            rule = order.sgt_approval_workflow_id or self.env['sgt.erp.workflow'].sudo().get_approval_rule('sale.order', order.company_id, order.amount_total)
            if rule and not rule.check_user_can_approve(self.env.user):
                raise AccessError(_("You do not have authorization to approve this sales order according to workflow [%s].") % rule.name)
            
            order.sudo().write({
                'sgt_approval_state': 'approved',
                'sgt_approver_id': self.env.user.id,
                'sgt_approval_date': fields.Datetime.now(),
                'sgt_approval_workflow_id': rule.id if rule else False,
            })
            order.message_post(
                body=_("Sales order was successfully approved by <b>%s</b>.") % self.env.user.name
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
                raise AccessError(_("You do not have authorization to reject this sales order according to workflow [%s].") % rule.name)

            order.sudo().write({
                'sgt_approval_state': 'rejected',
                'sgt_approver_id': self.env.user.id,
                'sgt_approval_date': fields.Datetime.now(),
            })
            order.message_post(
                body=_("Sales order approval was rejected by <b>%s</b>.") % self.env.user.name
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
                            return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Current Level Approved'),
                                    'message': _('Order has advanced to the next approval stage.'),
                                    'type': 'info',
                                    'sticky': False,
                                }
                            }
                    else:
                        raise UserError(
                            _(
                                "Sales order %(name)s is in 'Pending Approval' status (%(level)s). "
                                "Please contact an authorized approver before confirming."
                            ) % {'name': order.name, 'level': line.name}
                        )

                # Fallback if no lines
                if rule and rule.check_user_can_approve(self.env.user):
                    order.sudo().write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                        'sgt_approval_workflow_id': rule.id if rule else False,
                    })
                    order.message_post(
                        body=_("Sales order automatically approved by authorized approver: <b>%s</b>.") % self.env.user.name
                    )
                    continue
                else:
                    raise UserError(
                        _(
                            "Sales order %(name)s is in 'Pending Approval' status. "
                            "Please contact an authorized approver before confirming."
                        ) % {'name': order.name}
                    )

            # Check threshold for new confirmation or manual workflow selection
            should_require_approval = False
            if order.sgt_approval_workflow_id and order.sgt_approval_workflow_id.require_approval:
                should_require_approval = True
            elif rule and rule.amount_threshold > 0 and order.amount_total >= rule.amount_threshold:
                should_require_approval = True

            if should_require_approval and rule:
                # Create approval lines
                lines = order._generate_approval_lines(rule)
                pending_line = lines.filtered(lambda l: l.state == 'pending')[:1]
                
                if pending_line and pending_line.check_user_can_approve(self.env.user):
                    # Automatically approve level 1
                    pending_line.action_approve(user=self.env.user)
                    if order.sgt_approval_state == 'approved':
                        continue
                    else:
                        order.sudo().write({
                            'sgt_approval_state': 'to_approve',
                            'sgt_approval_workflow_id': rule.id,
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Stage 1 Approved'),
                                'message': _('Order stage 1 was automatically approved and is waiting for subsequent stages.'),
                                'type': 'info',
                                'sticky': False,
                            }
                        }

                # User cannot approve first level
                order.sudo().write({
                    'sgt_approval_state': 'to_approve',
                    'sgt_approval_workflow_id': rule.id,
                })
                order.message_post(
                    body=_(
                        "Order total %(amount)s %(currency)s exceeds approval threshold (%(threshold)s %(currency)s). "
                        "Moved to <b>Pending Approval</b> under workflow [%(rule)s]."
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
                        'title': _('Approval Required'),
                        'message': _(
                            "Order %(name)s exceeds threshold (%(threshold)s %(currency)s). "
                            "Moved to 'Pending Approval'."
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
