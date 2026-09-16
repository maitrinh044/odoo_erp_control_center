# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SgtErpApprovalWizard(models.TransientModel):
    _name = 'sgt.erp.approval.wizard'
    _description = 'Approval Confirmation Wizard'

    line_id = fields.Many2one('sgt.erp.approval.line', string='Approval Stage', required=True)
    document_reference = fields.Char(related='line_id.document_reference', string='Document Reference', readonly=True)
    level_name = fields.Char(related='line_id.name', string='Stage Name', readonly=True)
    action_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ], string='Action', required=True, default='approve')

    note = fields.Text(string='Comment / Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.note or not self.note.strip():
            raise UserError(_("Please enter a comment or reason for this action."))

        if self.action_type == 'approve':
            self.line_id.action_approve(user=self.env.user, note=self.note.strip())
            title = _("Approved Successfully")
            message = _("Approved [%(level)s] for document %(doc)s.") % {
                'level': self.line_id.name,
                'doc': self.line_id.document_reference or '',
            }
            msg_type = 'success'
        else:
            self.line_id.action_reject(user=self.env.user, note=self.note.strip())
            title = _("Approval Rejected")
            message = _("Rejected [%(level)s] for document %(doc)s.") % {
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
