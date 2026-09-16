# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import AccessError

FEATURE_MODEL_MAPPING = {
    'crm.lead': 'crm',
    'sale.order': 'sales',
    'purchase.order': 'purchase',
    'account.move': 'account',
    'stock.picking': 'stock',
    'hr.employee': 'hr',
    'project.project': 'project',
    'project.task': 'project',
    'calendar.event': 'calendar',
    'res.partner': 'contacts',
    'lms.course': 'lms',
}

class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        res = super()._get_action_dict()
        # Do not block in install mode or superuser mode (unless test_action_guard context is set)
        if not self.env.context.get('test_action_guard'):
            if self.env.su or self.env.context.get('install_mode'):
                return res

        if self.res_model and self.res_model in FEATURE_MODEL_MAPPING:
            feat_code = FEATURE_MODEL_MAPPING[self.res_model]
            Feature = self.env['sgt.erp.feature']
            is_on = Feature.sudo().is_enabled(feat_code)
            if not is_on:
                raise AccessError(
                    _("Feature '%s' (%s module) is currently disabled in SGT ERP according to the active package configuration.")
                    % (self.name or self.res_model, feat_code.upper())
                )
        return res

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    def run(self):
        if not self.env.su and not self.env.context.get('install_mode'):
            if self.model_name in ('crm.lead', 'crm.team') and not self.env['sgt.erp.feature'].sudo().is_enabled('crm'):
                raise AccessError(
                    _("The CRM module is currently disabled according to system package configuration.")
                )
            if self.model_name == 'purchase.order' and not self.env['sgt.erp.feature'].sudo().is_enabled('purchase'):
                raise AccessError(
                    _("The Purchase module is currently disabled according to system package configuration.")
                )
            if self.model_name == 'account.move' and not self.env['sgt.erp.feature'].sudo().is_enabled('account'):
                raise AccessError(
                    _("The Invoicing & Accounting module is currently disabled according to system package configuration.")
                )
        return super().run()
