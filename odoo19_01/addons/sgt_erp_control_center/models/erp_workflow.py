# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpWorkflow(models.Model):
    _name = 'sgt.erp.workflow'
    _description = 'SGT ERP Workflow Configuration'
    _order = 'name asc'

    name = fields.Char(string='Workflow Name', required=True)
    workflow_type = fields.Selection([
        ('crm', 'CRM'),
        ('sales', 'Sales'),
        ('purchase', 'Purchase Order'),
        ('account', 'Invoicing & Bills'),
        ('hr', 'HR'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], string='Workflow Type', default='crm', required=True)
    
    model_id = fields.Many2one('ir.model', string='Target Model')
    model_name = fields.Char(related='model_id.model', string='Model Technical Name', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    stage_ids = fields.One2many('sgt.erp.workflow.stage', 'workflow_id', string='Workflow Stages')
    stage_count = fields.Integer(string='Stages Count', compute='_compute_stage_count')
    
    stage_configuration = fields.Text(string='Stage Configuration', help='Config stages order, rules, etc.')
    trigger = fields.Selection([
        ('stage_change', 'Stage Transition'),
        ('on_create', 'On Record Creation'),
        ('on_write', 'On Record Update'),
        ('amount_threshold', 'Amount Threshold Exceeded'),
    ], string='Trigger Event', default='stage_change')
    require_approval = fields.Boolean(string='Require Approval', default=False)
    approver_group_id = fields.Many2one('res.groups', string='Approver Group')
    approver_user_ids = fields.Many2many(
        'res.users',
        'sgt_erp_workflow_user_rel',
        'workflow_id',
        'user_id',
        string='Direct Approvers'
    )
    number_of_approvals = fields.Integer(string='Number Of Approvals Required', default=1)
    amount_threshold = fields.Float(string='Amount Threshold for Approval', default=0.0)
    required_fields = fields.Char(string='Required Fields (comma-separated)')
    notification_type = fields.Selection([
        ('none', 'No Notification'),
        ('in_app', 'In-App Notification (Chatter)'),
        ('email', 'Email Notification'),
        ('both', 'Both Email and In-App')
    ], string='Notification', default='in_app', help='Notification triggered when moving stages or requesting approval')
    notification_template_id = fields.Many2one('mail.template', string='Email Template')
    notification_message = fields.Char(string='Notification Text / Message')
    action_after_approval = fields.Text(string='Action After Approval')

    # Multi-level Approval Configuration
    approval_mode = fields.Selection([
        ('sequential', 'Sequential (Step-by-step)'),
        ('direct', 'Direct (Highest Level Only)'),
    ], string='Multi-Level Approval Mode', default='sequential', required=True)
    level_ids = fields.One2many('sgt.erp.workflow.level', 'workflow_id', string='Approval Levels')
    level_count = fields.Integer(string='Levels Count', compute='_compute_level_count')

    @api.depends('stage_ids')
    def _compute_stage_count(self):
        for rec in self:
            rec.stage_count = len(rec.stage_ids)

    @api.depends('level_ids')
    def _compute_level_count(self):
        for rec in self:
            rec.level_count = len(rec.level_ids)

    def get_applicable_levels(self, amount=None):
        """Return list of applicable approval levels (sgt.erp.workflow.level) based on amount."""
        self.ensure_one()
        if not self.level_ids:
            return self.env['sgt.erp.workflow.level']

        ordered_levels = self.level_ids.sorted(key=lambda l: (l.sequence, l.id))
        if amount is None or amount <= 0:
            return ordered_levels

        matching_levels = ordered_levels.filtered(
            lambda l: (l.amount_min <= 0 or amount >= l.amount_min) and (l.amount_max <= 0 or amount <= l.amount_max)
        )
        if not matching_levels:
            # Fallback: if amount exceeds all level amount_mins, match the highest levels
            matching_levels = ordered_levels.filtered(lambda l: l.amount_min <= 0 or amount >= l.amount_min)
        if not matching_levels and ordered_levels:
            # Fallback: if amount is below minimum level, default to first level
            matching_levels = ordered_levels[:1]

        if self.approval_mode == 'direct' and matching_levels:
            # Only take the highest level (last by sequence)
            return matching_levels[-1:]

        return matching_levels

    @api.model
    def get_approval_rule(self, model_name, company=None, amount=None):
        """Find active workflow rule requiring approval for given model and company."""
        company = company or self.env.company
        wf_type = 'sales' if model_name == 'sale.order' else ('crm' if model_name == 'crm.lead' else 'custom')
        domain = [
            ('active', '=', True),
            ('require_approval', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
            '|', ('model_id.model', '=', model_name), ('workflow_type', '=', wf_type),
        ]
        rules = self.search(domain)
        if amount is not None:
            # Filter rule where threshold > 0 and amount >= amount_threshold
            matching_rules = rules.filtered(lambda r: r.amount_threshold > 0 and amount >= r.amount_threshold)
            if matching_rules:
                # Return highest threshold rule first
                return matching_rules.sorted(key=lambda r: r.amount_threshold, reverse=True)[0]
            return self.browse()
        return rules[:1]

    def check_user_can_approve(self, user=None):
        """Check if user has permission to approve this workflow."""
        self.ensure_one()
        user = user or self.env.user
        # System Administrator can always approve
        if user.has_group('base.group_system'):
            return True
        if user in self.approver_user_ids:
            return True
        if self.approver_group_id:
            user_groups = user.all_group_ids if hasattr(user, 'all_group_ids') else user.group_ids
            if self.approver_group_id in user_groups:
                return True
        return False

    def validate_required_fields(self, record):
        """Ensure all required_fields are populated on record."""
        self.ensure_one()
        if not self.required_fields:
            return True
        missing = []
        field_names = [f.strip() for f in self.required_fields.split(',') if f.strip()]
        for fname in field_names:
            if fname in record._fields:
                val = record[fname]
                if not val:
                    field_string = record._fields[fname].string or fname
                    missing.append(f"{field_string} ({fname})")
        if missing:
            from odoo.exceptions import ValidationError
            raise ValidationError(
                _("Cannot proceed due to missing required fields in workflow [%(workflow)s]:\n- %(fields)s") % {
                    'workflow': self.name,
                    'fields': '\n- '.join(missing),
                }
            )
        return True

