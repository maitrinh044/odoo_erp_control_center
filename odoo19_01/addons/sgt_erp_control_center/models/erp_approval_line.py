# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class SgtErpApprovalLine(models.Model):
    _name = 'sgt.erp.approval.line'
    _description = 'SGT ERP Approval Progress Line'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Stage Name', required=True)
    res_model = fields.Char(string='Target Model', required=True, index=True)
    res_id = fields.Integer(string='Document ID', required=True, index=True)

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', index=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade', index=True)
    account_move_id = fields.Many2one('account.move', string='Invoice / Entry', ondelete='cascade', index=True)

    sale_order_line_ids = fields.One2many(
        related='sale_order_id.order_line',
        string='Sales Lines',
        readonly=True
    )
    purchase_order_line_ids = fields.One2many(
        related='purchase_order_id.order_line',
        string='Purchase Lines',
        readonly=True
    )
    invoice_line_ids = fields.One2many(
        related='account_move_id.invoice_line_ids',
        string='Invoice Lines',
        readonly=True
    )

    workflow_id = fields.Many2one('sgt.erp.workflow', string='Approval Workflow', ondelete='set null')
    level_id = fields.Many2one('sgt.erp.workflow.level', string='Approval Stage Config', ondelete='set null')
    sequence = fields.Integer(string='Sequence', default=10)

    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ], string='Status', default='waiting', required=True, index=True)

    approver_user_ids = fields.Many2many(
        'res.users',
        'sgt_erp_approval_line_user_rel',
        'line_id',
        'user_id',
        string='Designated Approvers'
    )
    approver_group_id = fields.Many2one('res.groups', string='Approver Group')

    approved_by_id = fields.Many2one('res.users', string='Action By', readonly=True)
    approved_date = fields.Datetime(string='Action Date', readonly=True)
    note = fields.Text(string='Comment / Reason')

    # Reference to original document record for approval queue display
    document_reference = fields.Char(string='Document Reference', compute='_compute_document_info', store=True)
    partner_id = fields.Many2one('res.partner', string='Customer / Partner', compute='_compute_document_info', store=True)
    amount_total = fields.Float(string='Total Amount', compute='_compute_document_info', store=True)
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_document_info', store=True)

    @api.depends('res_model', 'res_id', 'sale_order_id', 'purchase_order_id', 'account_move_id')
    def _compute_document_info(self):
        for line in self:
            if line.sale_order_id:
                line.document_reference = line.sale_order_id.name
                line.partner_id = line.sale_order_id.partner_id
                line.amount_total = line.sale_order_id.amount_total
                line.company_id = line.sale_order_id.company_id
            elif line.purchase_order_id:
                line.document_reference = line.purchase_order_id.name
                line.partner_id = line.purchase_order_id.partner_id
                line.amount_total = line.purchase_order_id.amount_total
                line.company_id = line.purchase_order_id.company_id
            elif line.account_move_id:
                line.document_reference = line.account_move_id.name or line.account_move_id.ref or f"Move #{line.account_move_id.id}"
                line.partner_id = line.account_move_id.partner_id
                line.amount_total = line.account_move_id.amount_total
                line.company_id = line.account_move_id.company_id
            elif line.res_model and line.res_id:
                try:
                    record = self.env[line.res_model].browse(line.res_id)
                    if record.exists():
                        line.document_reference = getattr(record, 'display_name', False) or getattr(record, 'name', '')
                        line.partner_id = getattr(record, 'partner_id', False)
                        line.amount_total = getattr(record, 'amount_total', 0.0) or getattr(record, 'expected_revenue', 0.0)
                        line.company_id = getattr(record, 'company_id', self.env.company)
                    else:
                        line.document_reference = f"{line.res_model} #{line.res_id}"
                except Exception:
                    line.document_reference = f"{line.res_model} #{line.res_id}"

    def check_user_can_approve(self, user=None):
        """Check whether user has permission to approve this line."""
        self.ensure_one()
        user = user or self.env.user
        if user.has_group('base.group_system'):
            return True
        line_sudo = self.sudo()
        if user.id in line_sudo.approver_user_ids.ids:
            return True
        if line_sudo.approver_group_id:
            user_groups = user.sudo().all_group_ids if hasattr(user, 'all_group_ids') else user.sudo().group_ids
            if line_sudo.approver_group_id in user_groups:
                return True
        return False

    def action_approve(self, user=None, note=None):
        """Approve current level and advance to next level."""
        self.ensure_one()
        user = user or self.env.user
        if not self.check_user_can_approve(user):
            raise AccessError(_("You do not have permission to approve stage [%s].") % self.name)
        if self.state != 'pending':
            raise UserError(_("This approval stage is not currently pending."))

        self.sudo().write({
            'state': 'approved',
            'approved_by_id': user.id,
            'approved_date': fields.Datetime.now(),
            'note': note or '',
        })

        # Post log to document Chatter
        doc = self._get_document_record()
        note_display = f"<br/><i>Note: {note}</i>" if note else ""
        if doc and hasattr(doc, 'message_post'):
            doc.sudo().message_post(
                body=_(
                    "<b>%(level)s</b> was approved by <b>%(user)s</b>.%(note)s"
                ) % {
                    'level': self.name,
                    'user': user.name,
                    'note': note_display,
                }
            )

        # Look for next pending line for this document
        all_lines = self.search([
            ('res_model', '=', self.res_model),
            ('res_id', '=', self.res_id)
        ], order='sequence asc, id asc')

        next_line = all_lines.filtered(lambda l: l.state == 'waiting')[:1]
        if next_line:
            # Advance next level to pending
            next_line.sudo().write({'state': 'pending'})
            if doc and hasattr(doc, 'message_post'):
                approvers_str = ', '.join(next_line.approver_user_ids.mapped('name')) if next_line.approver_user_ids else (next_line.approver_group_id.name if next_line.approver_group_id else _("Management"))
                doc.sudo().message_post(
                    body=_(
                        "Advance approval stage to <b>%(next_level)s</b> (Assigned to: %(approvers)s)."
                    ) % {
                        'next_level': next_line.name,
                        'approvers': approvers_str,
                    }
                )
            if hasattr(doc, 'sgt_approval_state'):
                doc.sudo().write({'sgt_approval_state': 'to_approve'})
        else:
            # All approval stages completed!
            if doc and hasattr(doc, 'sgt_approval_state'):
                doc.sudo().write({
                    'sgt_approval_state': 'approved',
                    'sgt_approver_id': user.id,
                    'sgt_approval_date': fields.Datetime.now(),
                })
            if doc and hasattr(doc, 'message_post'):
                doc.sudo().message_post(
                    body=_(
                        "<b>All approval stages have been successfully completed!</b> Document is ready for processing."
                    )
                )
            # Automatically confirm document
            if self.res_model == 'sale.order' and doc and doc.state in ('draft', 'sent'):
                doc.action_confirm()
            elif self.res_model == 'purchase.order' and doc and doc.state in ('draft', 'sent', 'to approve'):
                doc.button_confirm()
            elif self.res_model == 'account.move' and doc and doc.state == 'draft':
                doc.action_post()

        return True

    def action_reject(self, user=None, note=None):
        """Reject current level and stop workflow."""
        self.ensure_one()
        user = user or self.env.user
        if not self.check_user_can_approve(user):
            raise AccessError(_("You do not have permission to reject stage [%s].") % self.name)
        if self.state not in ('pending', 'waiting'):
            raise UserError(_("Cannot reject stage in its current status."))

        self.sudo().write({
            'state': 'rejected',
            'approved_by_id': user.id,
            'approved_date': fields.Datetime.now(),
            'note': note or '',
        })

        # Skip all subsequent pending/waiting levels
        all_lines = self.search([
            ('res_model', '=', self.res_model),
            ('res_id', '=', self.res_id),
            ('id', '!=', self.id),
            ('state', 'in', ('waiting', 'pending'))
        ])
        if all_lines:
            all_lines.sudo().write({'state': 'skipped'})

        doc = self._get_document_record()
        reason_display = f"<br/><b>Rejection reason:</b> {note}" if note else ""
        if doc and hasattr(doc, 'message_post'):
            doc.sudo().message_post(
                body=_(
                    "<b>%(level)s</b> was <b>REJECTED</b> by <b>%(user)s</b>.%(reason)s"
                ) % {
                    'level': self.name,
                    'user': user.name,
                    'reason': reason_display,
                }
            )
        if doc and hasattr(doc, 'sgt_approval_state'):
            doc.sudo().write({
                'sgt_approval_state': 'rejected',
                'sgt_approver_id': user.id,
                'sgt_approval_date': fields.Datetime.now(),
            })

        return True

    def _get_document_record(self):
        """Helper to get source document record."""
        self.ensure_one()
        if self.sale_order_id:
            return self.sale_order_id
        if self.purchase_order_id:
            return self.purchase_order_id
        if self.account_move_id:
            return self.account_move_id
        if self.res_model and self.res_id and self.res_model in self.env:
            rec = self.env[self.res_model].browse(self.res_id)
            return rec if rec.exists() else False
        return False

    def action_open_document(self):
        """Action to open source document from pending queue."""
        self.ensure_one()
        doc = self._get_document_record()
        if not doc:
            raise UserError(_("Related document not found."))
        return {
            'type': 'ir.actions.act_window',
            'name': self.document_reference or _("Document"),
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_approve_wizard(self):
        """Open approval modal directly from approval line form."""
        self.ensure_one()
        return {
            'name': _("Approve: %s") % self.document_reference,
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_action_type': 'approve',
            }
        }

    def action_open_reject_wizard(self):
        """Open reject modal directly from approval line form."""
        self.ensure_one()
        return {
            'name': _("Reject: %s") % self.document_reference,
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_action_type': 'reject',
            }
        }
