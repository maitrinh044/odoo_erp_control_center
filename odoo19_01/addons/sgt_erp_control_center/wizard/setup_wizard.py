# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SgtErpSetupWizard(models.TransientModel):
    _name = 'sgt.erp.setup.wizard'
    _description = 'Multi-step Guided ERP Setup Wizard'

    state = fields.Selection([
        ('step1', '1. Business & Brand'),
        ('step2', '2. Package Selection'),
        ('step3', '3. Theme & Appearance'),
        ('step4', '4. Integration & Security'),
        ('step5', '5. Summary & Launch'),
    ], string='Setup Step', default='step1', required=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # Step 1: Business & Brand
    customer_name = fields.Char(string='Customer / Business Name', required=True, default='Example Enterprise')
    product_name = fields.Char(string='ERP Product Name', default='SGT ERP', required=True)
    customer_code = fields.Char(string='Customer Code', default='SGT-PRO')
    industry = fields.Selection([
        ('trading', 'Trading'),
        ('manufacturing', 'Manufacturing'),
        ('distribution', 'Distribution'),
        ('service', 'Service'),
        ('exhibition', 'Exhibition'),
        ('construction', 'Construction'),
        ('medical', 'Medical'),
        ('education', 'Education'),
        ('other', 'Other'),
    ], string='Industry', default='trading', required=True)
    logo = fields.Binary(string='Company Logo')

    # Step 2: Package Selection
    package_id = fields.Many2one(
        'sgt.erp.package',
        string='ERP Package',
        default=lambda self: self.env['sgt.erp.package'].search([], limit=1)
    )
    package_features_summary = fields.Text(string='Included Features', compute='_compute_package_summary')

    # Step 3: Theme & Appearance
    theme_id = fields.Many2one(
        'sgt.erp.theme',
        string='Initial Theme',
        default=lambda self: self.env['sgt.erp.theme'].search([], limit=1)
    )

    # Step 4: Integration & Security
    enable_google_calendar = fields.Boolean(string='Enable Google Calendar Integration', default=False)
    role_preset_id = fields.Many2one('sgt.erp.role.preset', string='Default Admin Role Preset')

    @api.depends('package_id')
    def _compute_package_summary(self):
        for rec in self:
            if rec.package_id and rec.package_id.feature_ids:
                feature_names = rec.package_id.feature_ids.mapped('name')
                rec.package_features_summary = f"{len(feature_names)} features: " + ", ".join(feature_names[:8]) + ("..." if len(feature_names) > 8 else "")
            else:
                rec.package_features_summary = _("No features selected in package.")

    def action_goto_step1(self):
        self.state = 'step1'
        return self._reopen_self()

    def action_goto_step2(self):
        self.state = 'step2'
        return self._reopen_self()

    def action_goto_step3(self):
        if not self.package_id:
            raise UserError(_("Please select an ERP Package before proceeding!"))
        self.state = 'step3'
        return self._reopen_self()

    def action_goto_step4(self):
        if not self.theme_id:
            raise UserError(_("Please select a Theme before proceeding!"))
        self.state = 'step4'
        return self._reopen_self()

    def action_goto_step5(self):
        self.state = 'step5'
        return self._reopen_self()

    def _reopen_self(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply_quick_setup(self):
        """Activate and deploy system configuration from Wizard"""
        self.ensure_one()
        Config = self.env['sgt.erp.config']
        config = Config.search([('company_id', '=', self.company_id.id)], limit=1)
        vals = {
            'name': f"{self.customer_name} ERP Configuration",
            'company_id': self.company_id.id,
            'product_name': self.product_name,
            'customer_name': self.customer_name,
            'customer_code': self.customer_code,
            'industry': self.industry,
            'package_id': self.package_id.id,
            'theme_id': self.theme_id.id,
            'enable_google_calendar': self.enable_google_calendar,
        }
        if self.logo:
            vals['company_logo'] = self.logo
            vals['login_logo'] = self.logo
            self.company_id.sudo().write({'logo': self.logo})

        if config:
            config.write(vals)
        else:
            config = Config.create(vals)

        # Assign role preset if selected
        if self.role_preset_id:
            self.role_preset_id.write({'user_ids': [(4, self.env.user.id)]})
            self.role_preset_id.action_apply_to_users()

        return config.action_apply_configuration()
