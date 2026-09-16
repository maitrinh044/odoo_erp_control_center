# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpWorkflowLevel(models.Model):
    _name = 'sgt.erp.workflow.level'
    _description = 'SGT ERP Workflow Approval Level'
    _order = 'workflow_id, sequence asc, id asc'

    name = fields.Char(string='Level Name', required=True)
    workflow_id = fields.Many2one('sgt.erp.workflow', string='Workflow', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    approver_type = fields.Selection([
        ('user', 'Specific Users'),
        ('group', 'Security Group'),
        ('both', 'User or Group')
    ], string='Approver Type', default='user', required=True)

    approver_user_ids = fields.Many2many(
        'res.users',
        'sgt_erp_wf_level_user_rel',
        'level_id',
        'user_id',
        string='Designated Approvers'
    )
    approver_group_id = fields.Many2one('res.groups', string='Approver Group')

    # Amount triggers for this level
    amount_min = fields.Float(string='Minimum Amount', default=0.0,
                              help='This level is only required if document amount >= minimum amount. Set 0 for always required.')
    amount_max = fields.Float(string='Maximum Amount', default=0.0,
                              help='Set 0 for no maximum limit.')

    auto_notification = fields.Boolean(string='Notify When Pending', default=True)
    description = fields.Char(string='Description / Notes')

    def check_user_can_approve(self, user=None):
        """Check whether user has approval rights for this level."""
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
