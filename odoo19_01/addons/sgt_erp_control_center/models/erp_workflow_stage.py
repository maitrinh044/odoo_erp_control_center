# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpWorkflowStage(models.Model):
    _name = 'sgt.erp.workflow.stage'
    _description = 'SGT ERP Workflow Stage'
    _order = 'workflow_id, sequence asc, id asc'

    name = fields.Char(string='Stage Name', required=True)
    workflow_id = fields.Many2one('sgt.erp.workflow', string='Workflow', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban', default=False)
    is_won = fields.Boolean(string='Is Final / Won Stage', default=False)
    
    # Approval Builder settings per stage
    require_approval = fields.Boolean(string='Require Approval to Enter', default=False)
    min_approvals = fields.Integer(string='Min Approvals Required', default=1)
    approver_group_id = fields.Many2one('res.groups', string='Approver Group')
    approver_user_ids = fields.Many2many(
        'res.users',
        'sgt_erp_workflow_stage_user_rel',
        'stage_id',
        'user_id',
        string='Designated Approvers'
    )
    amount_threshold = fields.Float(string='Amount Threshold for Approval', default=0.0,
                                    help='If record amount exceeds this, approval is strictly required.')
    notification_template = fields.Text(string='Notification Template / Message',
                                        help='Message sent to approvers upon stage change request.')
    auto_next_stage_id = fields.Many2one('sgt.erp.workflow.stage', string='Auto Move to Stage Upon Approval')
