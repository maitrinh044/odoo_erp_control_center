# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class SgtErpMassApprovalWizard(models.TransientModel):
    _name = 'sgt.erp.mass.approval.wizard'
    _description = 'SGT ERP Mass Approval Wizard'

    action_type = fields.Selection([
        ('approve', 'Mass Approve'),
        ('reject', 'Mass Reject'),
    ], string='Action', default='approve', required=True)

    line_ids = fields.Many2many(
        'sgt.erp.approval.line',
        string='Selected Approval Stages'
    )

    total_count = fields.Integer(string='Total Documents', compute='_compute_counts')
    sale_order_count = fields.Integer(string='Sales Orders', compute='_compute_counts')
    purchase_order_count = fields.Integer(string='Purchase Orders', compute='_compute_counts')
    account_move_count = fields.Integer(string='Invoices', compute='_compute_counts')
    other_count = fields.Integer(string='Other Documents', compute='_compute_counts')

    note = fields.Text(
        string='Comment / Reason',
        help='Approval comment or rejection reason applied to all selected documents.'
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
        """Execute mass approval or rejection."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please select at least one document to process."))

        if self.action_type == 'reject' and not (self.note and self.note.strip()):
            raise UserError(_("Please provide a rejection reason when performing mass rejection."))

        success_count = 0
        skipped_count = 0
        skipped_details = []

        for line in self.line_ids:
            if line.state != 'pending':
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: Not in pending state")
                continue

            if not line.check_user_can_approve(self.env.user):
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: You do not have permission to approve this stage")
                continue

            try:
                if self.action_type == 'approve':
                    line.action_approve(user=self.env.user, note=self.note or _("Mass approved"))
                else:
                    line.action_reject(user=self.env.user, note=self.note)
                success_count += 1
            except Exception as e:
                skipped_count += 1
                skipped_details.append(f"{line.document_reference or line.name}: {str(e)}")

        action_label = _("approved") if self.action_type == 'approve' else _("rejected")

        message = _(
            "Successfully %(action)s %(success)s/%(total)s document(s)."
        ) % {
            'action': action_label,
            'success': success_count,
            'total': len(self.line_ids),
        }
        if skipped_count > 0:
            message += _(" Skipped %(skipped)s document(s) due to insufficient permissions or invalid state.") % {'skipped': skipped_count}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Mass Processing Result"),
                'message': message,
                'type': 'success' if success_count > 0 else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
