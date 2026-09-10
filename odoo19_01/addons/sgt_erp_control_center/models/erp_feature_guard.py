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
        # Không chặn trong chế độ cài đặt module ban đầu hoặc superuser hệ thống (trừ khi test_action_guard)
        if not self.env.context.get('test_action_guard'):
            if self.env.su or self.env.context.get('install_mode'):
                return res

        if self.res_model and self.res_model in FEATURE_MODEL_MAPPING:
            feat_code = FEATURE_MODEL_MAPPING[self.res_model]
            Feature = self.env['sgt.erp.feature']
            is_on = Feature.sudo().is_enabled(feat_code)
            if not is_on:
                raise AccessError(
                    _("Tính năng '%s' (Phân hệ %s) hiện đang bị vô hiệu hóa trong hệ thống SGT ERP theo cấu hình gói dịch vụ.")
                    % (self.name or self.res_model, feat_code.upper())
                )
        return res

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    def run(self):
        if not self.env.su and not self.env.context.get('install_mode'):
            if self.model_name in ('crm.lead', 'crm.team') and not self.env['sgt.erp.feature'].sudo().is_enabled('crm'):
                raise AccessError(
                    _("Phân hệ CRM hiện đang bị vô hiệu hóa theo cấu hình gói dịch vụ của hệ thống.")
                )
            if self.model_name == 'purchase.order' and not self.env['sgt.erp.feature'].sudo().is_enabled('purchase'):
                raise AccessError(
                    _("Phân hệ Mua hàng hiện đang bị vô hiệu hóa theo cấu hình gói dịch vụ của hệ thống.")
                )
            if self.model_name == 'account.move' and not self.env['sgt.erp.feature'].sudo().is_enabled('account'):
                raise AccessError(
                    _("Phân hệ Kế toán & Hóa đơn hiện đang bị vô hiệu hóa theo cấu hình gói dịch vụ của hệ thống.")
                )
        return super().run()
