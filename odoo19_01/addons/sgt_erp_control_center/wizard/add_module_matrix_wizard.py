# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

CONFIG_MODEL_SUFFIXES = (
    '.stage', '.tag', '.type', '.category', '.reason', '.lost.reason',
    '.status', '.template', '.state', '.priority', '.industry', '.title',
    '.medium', '.source',
)

class SgtErpAddModuleMatrixWizard(models.TransientModel):
    _name = 'sgt.erp.add.module.matrix.wizard'
    _description = 'Wizard Thêm nhanh Quyền theo Module vào Ma trận'

    role_preset_id = fields.Many2one('sgt.erp.role.preset', string='Vai trò (Role Preset)', required=True, ondelete='cascade')
    module_ids = fields.Many2many('ir.module.module', string='Chọn các Modules', required=True, domain=[('state', '=', 'installed')])
    filter_mode = fields.Selection([
        ('primary', 'Chỉ đối tượng nghiệp vụ chính (Khuyến nghị)'),
        ('all', 'Tất cả đối tượng của module'),
    ], string='Chế độ lọc', default='primary', required=True)

    perm_read = fields.Boolean(string='Xem (Read)', default=True)
    perm_write = fields.Boolean(string='Sửa (Write)', default=True)
    perm_create = fields.Boolean(string='Tạo (Create)', default=True)
    perm_unlink = fields.Boolean(string='Xóa (Delete)', default=False)
    data_scope = fields.Selection([
        ('all', 'Toàn hệ thống (All)'),
        ('team', 'Cả nhóm / Chi nhánh (Team)'),
        ('own', 'Chỉ của mình (Own)'),
    ], string='Phạm vi dữ liệu', required=True, default='own')

    line_ids = fields.One2many('sgt.erp.add.module.matrix.wizard.line', 'wizard_id', string='Danh sách đối tượng xem trước')

    @api.onchange('module_ids', 'filter_mode', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'data_scope')
    def _onchange_module_and_settings(self):
        if not self.module_ids:
            self.line_ids = [(5, 0, 0)]
            return

        existing_models = set(self.role_preset_id.permission_matrix_ids.mapped('model_id.model'))
        seen_models = set(existing_models)
        lines = []

        for module in self.module_ids:
            model_datas = self.env['ir.model.data'].search([
                ('module', '=', module.name),
                ('model', '=', 'ir.model')
            ])
            model_ids = model_datas.mapped('res_id')
            matching_models = self.env['ir.model'].browse(model_ids)

            for model in matching_models:
                m_name = model.model
                if m_name in seen_models or m_name.startswith(('ir.', 'wizard.', 'report.')) or m_name.endswith(('.wizard', '.report')):
                    continue

                is_config = any(m_name.endswith(suffix) for suffix in CONFIG_MODEL_SUFFIXES)

                if self.filter_mode == 'primary' and is_config:
                    continue

                seen_models.add(m_name)
                lines.append((0, 0, {
                    'selected': True,
                    'model_id': model.id,
                    'module_name': module.shortdesc or module.name,
                    'model_type': 'config' if is_config else 'primary',
                    'perm_read': self.perm_read if not is_config else True,
                    'perm_write': self.perm_write if not is_config else False,
                    'perm_create': self.perm_create if not is_config else False,
                    'perm_unlink': self.perm_unlink if not is_config else False,
                    'data_scope': self.data_scope if not is_config else 'all',
                }))

        self.line_ids = [(5, 0, 0)] + lines

    def action_add_to_matrix(self):
        self.ensure_one()
        role = self.role_preset_id
        existing_models = set(role.permission_matrix_ids.mapped('model_id.model'))
        seen_models = set(existing_models)
        lines_to_create = []

        if self.line_ids:
            for l in self.line_ids.filtered('selected'):
                if l.model_id.model in seen_models:
                    continue
                seen_models.add(l.model_id.model)
                lines_to_create.append({
                    'role_preset_id': role.id,
                    'model_id': l.model_id.id,
                    'model_type': l.model_type,
                    'perm_read': l.perm_read,
                    'perm_write': l.perm_write,
                    'perm_create': l.perm_create,
                    'perm_unlink': l.perm_unlink,
                    'data_scope': l.data_scope,
                })
        else:
            for module in self.module_ids:
                model_datas = self.env['ir.model.data'].search([
                    ('module', '=', module.name),
                    ('model', '=', 'ir.model')
                ])
                model_ids = model_datas.mapped('res_id')
                matching_models = self.env['ir.model'].browse(model_ids)

                for model in matching_models:
                    m_name = model.model
                    if m_name in seen_models or m_name.startswith(('ir.', 'wizard.', 'report.')) or m_name.endswith(('.wizard', '.report')):
                        continue

                    is_config = any(m_name.endswith(suffix) for suffix in CONFIG_MODEL_SUFFIXES)
                    if self.filter_mode == 'primary' and is_config:
                        continue

                    seen_models.add(m_name)
                    lines_to_create.append({
                        'role_preset_id': role.id,
                        'model_id': model.id,
                        'model_type': 'config' if is_config else 'primary',
                        'perm_read': True if is_config else self.perm_read,
                        'perm_write': False if is_config else self.perm_write,
                        'perm_create': False if is_config else self.perm_create,
                        'perm_unlink': False if is_config else self.perm_unlink,
                        'data_scope': 'all' if is_config else self.data_scope,
                    })

        if lines_to_create:
            created_records = self.env['sgt.erp.permission.matrix'].create(lines_to_create)
            created_records.action_sync_to_odoo_acls()
            role._sync_record_rules()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Thêm thành công"),
                'message': _("Đã thêm %d đối tượng từ các module vào Ma trận Phân quyền của vai trò '%s'.") % (len(lines_to_create), role.name),
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class SgtErpAddModuleMatrixWizardLine(models.TransientModel):
    _name = 'sgt.erp.add.module.matrix.wizard.line'
    _description = 'Dòng xem trước đối tượng thêm vào Ma trận Phân quyền'

    wizard_id = fields.Many2one('sgt.erp.add.module.matrix.wizard', string='Wizard', ondelete='cascade')
    selected = fields.Boolean(string='Chọn', default=True)
    model_id = fields.Many2one('ir.model', string='Đối tượng (Model)', required=True)
    model_name = fields.Char(related='model_id.model', string='Mã kỹ thuật', readonly=True)
    module_name = fields.Char(string='Phân hệ / Module')
    model_type = fields.Selection([
        ('primary', 'Nghiệp vụ chính'),
        ('config', 'Cấu hình/Danh mục'),
    ], string='Phân loại', default='primary')

    perm_read = fields.Boolean(string='Xem', default=True)
    perm_write = fields.Boolean(string='Sửa', default=True)
    perm_create = fields.Boolean(string='Tạo', default=True)
    perm_unlink = fields.Boolean(string='Xóa', default=False)
    data_scope = fields.Selection([
        ('all', 'Toàn hệ thống'),
        ('team', 'Cả nhóm'),
        ('own', 'Chỉ của mình'),
    ], string='Phạm vi', default='own')
