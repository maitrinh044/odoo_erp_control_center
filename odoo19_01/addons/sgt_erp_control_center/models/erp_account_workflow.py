# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class AccountMove(models.Model):
    _inherit = 'account.move'

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
        'sgt.erp.approval.line', 'account_move_id',
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
        for move in self:
            pending = move.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
            move.sgt_current_approval_line_id = pending[:1] if pending else False

    def _compute_can_current_user_approve(self):
        for move in self:
            line = move.sgt_current_approval_line_id
            if line:
                move.sgt_can_current_user_approve = line.check_user_can_approve(self.env.user)
            elif move.sgt_approval_workflow_id and move.sgt_approval_state == 'to_approve':
                move.sgt_can_current_user_approve = move.sgt_approval_workflow_id.check_user_can_approve(self.env.user)
            else:
                move.sgt_can_current_user_approve = False

    def _get_applicable_account_workflow(self):
        """Find applicable workflow rule for invoices / vendor bills."""
        self.ensure_one()
        if self.sgt_approval_workflow_id:
            return self.sgt_approval_workflow_id.sudo()
        Workflow = self.env['sgt.erp.workflow'].sudo()
        domain = [
            ('active', '=', True),
            ('require_approval', '=', True),
            ('workflow_type', '=', 'account'),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id or self.env.company.id)
        ]
        workflows = Workflow.search(domain, order='amount_threshold desc, id desc')
        for wf in workflows:
            if wf.amount_threshold > 0 and abs(self.amount_total) < wf.amount_threshold:
                continue
            return wf
        return False

    def _generate_account_approval_lines(self, rule):
        """Generate approval stages automatically according to invoice workflow config."""
        self.ensure_one()
        existing_lines = self.sgt_approval_line_ids.filtered(lambda l: l.state in ('waiting', 'pending'))
        if existing_lines:
            existing_lines.unlink()

        levels = rule.get_applicable_levels(abs(self.amount_total))
        lines_vals = []
        if levels:
            for idx, lvl in enumerate(levels):
                if rule.approval_mode == 'direct':
                    state = 'pending'
                else:
                    state = 'pending' if idx == 0 else 'waiting'
                lines_vals.append({
                    'name': lvl.name,
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'account_move_id': self.id,
                    'workflow_id': rule.id,
                    'level_id': lvl.id,
                    'sequence': lvl.sequence,
                    'state': state,
                    'approver_user_ids': [(6, 0, lvl.approver_user_ids.ids)],
                    'approver_group_id': lvl.approver_group_id.id if lvl.approver_group_id else False,
                })
        else:
            lines_vals.append({
                'name': _("Invoice Approval [%s]") % rule.name,
                'res_model': 'account.move',
                'res_id': self.id,
                'account_move_id': self.id,
                'workflow_id': rule.id,
                'sequence': 10,
                'state': 'pending',
                'approver_user_ids': [(6, 0, rule.approver_user_ids.ids)],
                'approver_group_id': rule.approver_group_id.id if rule.approver_group_id else False,
            })

        for val in lines_vals:
            self.env['sgt.erp.approval.line'].sudo().create(val)

    def action_post(self):
        """Intercept invoice posting to enforce multi-level approval."""
        for move in self:
            if move.sgt_approval_state == 'approved':
                continue

            # Only apply to invoices (in_invoice, in_refund, out_invoice, out_refund)
            if not move.is_invoice(include_receipts=True):
                continue

            rule = move._get_applicable_account_workflow()
            if not rule:
                continue

            if move.sgt_approval_state == 'to_approve':
                current_line = move.sgt_current_approval_line_id
                if current_line and current_line.check_user_can_approve(self.env.user):
                    current_line.action_approve(user=self.env.user)
                    if move.sgt_approval_state != 'approved':
                        raise UserError(_(
                            "You approved stage [%(level)s]. Invoice is awaiting subsequent approval stages."
                        ) % {'level': current_line.name})
                elif rule.check_user_can_approve(self.env.user):
                    move.write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                    })
                    move.message_post(body=_(
                        "<b>Invoice directly approved by %(user)s</b>"
                    ) % {'user': self.env.user.name})
                else:
                    raise UserError(_(
                        "Invoice #%(name)s (%(amount)s %(currency)s) is pending approval. You do not have approval authority."
                    ) % {
                        'name': move.name or move.ref or f"#{move.id}",
                        'amount': '{:,.0f}'.format(move.amount_total),
                        'currency': move.currency_id.symbol or '',
                    })
            else:
                # Initiate approval flow
                levels = rule.get_applicable_levels(abs(move.amount_total))
                if not levels and rule.check_user_can_approve(self.env.user):
                    move.write({
                        'sgt_approval_state': 'approved',
                        'sgt_approver_id': self.env.user.id,
                        'sgt_approval_date': fields.Datetime.now(),
                    })
                    move.message_post(body=_(
                        "Invoice automatically approved because %(user)s has approval rights."
                    ) % {'user': self.env.user.name})
                else:
                    move._generate_account_approval_lines(rule)
                    move.write({
                        'sgt_approval_state': 'to_approve',
                        'sgt_approval_workflow_id': rule.id,
                    })
                    first_line = move.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')[:1]
                    if first_line and first_line.check_user_can_approve(self.env.user):
                        first_line.action_approve(user=self.env.user)
                        if move.sgt_approval_state == 'approved':
                            continue
                        raise UserError(_(
                            "You approved stage [%(level)s]. Invoice is awaiting subsequent approval stages."
                        ) % {'level': first_line.name})
                    else:
                        approvers_str = rule.approver_group_id.name if rule.approver_group_id else ", ".join(rule.approver_user_ids.mapped('name'))
                        move.message_post(body=_(
                            "<b>Invoice approval required!</b><br/>Total: %(amount)s %(currency)s exceeds threshold limit. Authorized approval (%(approvers)s) is required."
                        ) % {
                            'amount': '{:,.0f}'.format(move.amount_total),
                            'currency': move.currency_id.symbol or '',
                            'approvers': approvers_str or _("Administrator"),
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Invoice Approval Required'),
                                'message': _(
                                    "Invoice %(name)s exceeds threshold (%(threshold)s %(currency)s). "
                                    "Moved to 'Pending Approval'."
                                ) % {
                                    'name': move.name or move.ref or f"#{move.id}",
                                    'threshold': '{:,.0f}'.format(rule.amount_threshold),
                                    'currency': move.currency_id.symbol or '',
                                },
                                'type': 'warning',
                                'sticky': False,
                            }
                        }

        unposted = self.filtered(lambda m: m.state == 'draft')
        if unposted:
            return super(AccountMove, unposted).action_post()
        return True

    def action_request_approval(self):
        """Manually submit invoice for approval."""
        self.ensure_one()
        rule = self._get_applicable_account_workflow()
        if not rule:
            raise UserError(_("No applicable invoice approval rule found."))
        self._generate_account_approval_lines(rule)
        self.write({
            'sgt_approval_state': 'to_approve',
            'sgt_approval_workflow_id': rule.id,
        })
        self.message_post(body=_("Invoice approval request submitted."))
        return True

    def action_open_approve_wizard(self):
        """Open approval modal wizard for invoice."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        return {
            'name': _("Approve Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_line_id': line.id if line else False,
                'default_res_model': 'account.move',
                'default_res_id': self.id,
                'default_action_type': 'approve',
            }
        }

    def action_open_reject_wizard(self):
        """Open rejection modal wizard for invoice."""
        self.ensure_one()
        line = self.sgt_current_approval_line_id
        return {
            'name': _("Reject Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_line_id': line.id if line else False,
                'default_res_model': 'account.move',
                'default_res_id': self.id,
                'default_action_type': 'reject',
            }
        }
