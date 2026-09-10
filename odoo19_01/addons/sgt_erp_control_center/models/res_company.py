# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    erp_config_id = fields.Many2one('sgt.erp.config', string='ERP Configuration', ondelete='set null')
    erp_theme_id = fields.Many2one('sgt.erp.theme', string='Active ERP Theme', ondelete='set null')
    erp_package_id = fields.Many2one('sgt.erp.package', string='ERP Package', ondelete='set null')
    erp_customer_code = fields.Char(string='ERP Customer Code')
