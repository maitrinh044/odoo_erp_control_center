# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SgtErpPackage(models.Model):
    _name = 'sgt.erp.package'
    _description = 'SGT ERP Package Manager'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Package Name', required=True)
    code = fields.Char(string='Package Code', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    
    feature_ids = fields.Many2many(
        'sgt.erp.feature',
        'sgt_erp_package_feature_rel',
        'package_id',
        'feature_id',
        string='Included Features',
        context={'active_test': False},
    )

    @api.constrains('code')
    def _check_code_uniq(self):
        for rec in self:
            duplicate = self.search([('code', '=', rec.code), ('id', '!=', rec.id)], limit=1)
            if duplicate:
                raise ValidationError(_("Package code must be unique!"))

    def apply_to_company(self, company_id=None):
        """Kích hoạt các feature thuộc package này cho công ty, không xóa dữ liệu"""
        self.ensure_one()
        if not company_id:
            company_id = self.env.company.id

        Feature = self.env['sgt.erp.feature'].with_context(active_test=False)
        package = self.with_context(active_test=False)
        package_feature_codes = set(package.feature_ids.mapped('code'))

        all_features = Feature.search([
            '|', ('company_id', '=', company_id), ('company_id', '=', False)
        ])

        for feat in all_features:
            if feat.code in package_feature_codes or package.code == 'enterprise':
                feat.active = True
            elif package.code != 'custom':
                feat.active = False

        # Đồng bộ menu tương ứng của tất cả các feature
        all_features.sync_menu_visibility()

    def action_apply_to_current_company(self):
        """Áp dụng gói này trực tiếp cho công ty hiện tại từ màn hình Form"""
        self.ensure_one()
        company = self.env.company
        company.write({'erp_package_id': self.id})
        self.apply_to_company(company.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Cấu hình Gói thành công"),
                'message': _("Đã áp dụng thành công gói '%s' cho công ty %s và đồng bộ các phân hệ liên quan.") % (self.name, company.name),
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
