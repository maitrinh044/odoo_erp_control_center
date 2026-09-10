# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSgtErpRoleAndSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RolePreset = cls.env['sgt.erp.role.preset']
        cls.Matrix = cls.env['sgt.erp.permission.matrix']
        cls.User = cls.env['res.users']

    def test_01_seven_role_presets_exist(self):
        """Kiểm tra 7 vai trò mẫu chuẩn theo đặc tả"""
        expected_roles = [
            'erp_admin',
            'manager',
            'sales_manager',
            'sales_user',
            'hr_manager',
            'hr_user',
            'viewer'
        ]
        presets = self.RolePreset.search([])
        codes = presets.mapped('code')
        for expected in expected_roles:
            self.assertIn(expected, codes, f"Role preset '{expected}' must exist!")

    def test_02_auto_map_standard_groups(self):
        """Kiểm tra tự động phát hiện và ánh xạ nhóm quyền Odoo"""
        sales_user = self.RolePreset.search([('code', '=', 'sales_user')], limit=1)
        self.assertTrue(sales_user)
        sales_user.action_auto_map_standard_groups()
        self.assertTrue(len(sales_user.group_ids) > 0, "Sales user preset should map standard groups")

    def test_03_assign_user_to_role_preset(self):
        """Kiểm tra gán người dùng vào vai trò và đồng bộ nhóm quyền"""
        viewer_preset = self.RolePreset.search([('code', '=', 'viewer')], limit=1)
        test_user = self.env.ref('base.user_admin')
        test_user.write({'role_preset_id': viewer_preset.id})
        self.assertEqual(test_user.role_preset_id, viewer_preset)
        self.assertIn(test_user, viewer_preset.user_ids)
        self.assertEqual(viewer_preset.user_count, len(viewer_preset.user_ids))
        
        # Kiểm tra action_apply_to_users
        res = viewer_preset.action_apply_to_users()
        self.assertEqual(res.get('params', {}).get('type'), 'success')

    def test_04_permission_matrix_sync(self):
        """Kiểm tra đồng bộ ma trận phân quyền sang ir.model.access"""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        role = self.RolePreset.create({'name': 'Test Matrix Role', 'code': 'test_matrix_role'})
        
        matrix_rec = self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': partner_model.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })
        res = matrix_rec.action_sync_to_odoo_acls()
        self.assertEqual(res.get('params', {}).get('type'), 'success')

    def test_05_data_scope_field_and_rules_generation(self):
        """Kiểm tra cấu hình data_scope và tự động sinh Record Rules cho sale.order & crm.lead"""
        erp_admin = self.RolePreset.search([('code', '=', 'erp_admin')], limit=1)
        sales_manager = self.RolePreset.search([('code', '=', 'sales_manager')], limit=1)
        sales_user = self.RolePreset.search([('code', '=', 'sales_user')], limit=1)

        self.assertEqual(erp_admin.data_scope, 'all')
        self.assertEqual(sales_manager.data_scope, 'team')
        self.assertEqual(sales_user.data_scope, 'own')

        # Test sync record rules
        sales_user.action_sync_record_rules()
        self.assertTrue(sales_user.security_group_id, "Security group should be created for preset")
        self.assertTrue(len(sales_user.rule_ids) >= 2, "Should have record rules for models in matrix")

        models_covered = sales_user.rule_ids.mapped('model_id.model')
        self.assertIn('sale.order', models_covered)
        self.assertIn('crm.lead', models_covered)

        # Kiểm tra domain của own scope
        sale_rule_own = sales_user.rule_ids.filtered(lambda r: r.model_id.model == 'sale.order')
        self.assertIn('user_id', sale_rule_own.domain_force)

        # Chuyển data_scope sang team và kiểm tra cập nhật
        sales_user.write({'data_scope': 'team'})
        sale_rule_team = sales_user.rule_ids.filtered(lambda r: r.model_id.model == 'sale.order')
        self.assertIn('team_id', sale_rule_team.domain_force)

        # Chuyển data_scope sang all và kiểm tra cập nhật
        sales_user.write({'data_scope': 'all'})
        sale_rule_all = sales_user.rule_ids.filtered(lambda r: r.model_id.model == 'sale.order')
        self.assertIn("(1, '=', 1)", sale_rule_all.domain_force)

        # Khôi phục lại own
        sales_user.write({'data_scope': 'own'})

    def test_06_data_scope_assignment_and_record_filtering(self):
        """Kiểm tra gán preset có data_scope cho user và chuyển đổi vai trò"""
        sales_user = self.RolePreset.search([('code', '=', 'sales_user')], limit=1)
        sales_manager = self.RolePreset.search([('code', '=', 'sales_manager')], limit=1)

        sales_user._sync_record_rules()
        sales_manager._sync_record_rules()

        test_user = self.User.create({
            'name': 'Test Sales Rep',
            'login': 'test_sales_rep_scope@example.com',
            'email': 'test_sales_rep_scope@example.com',
            'role_preset_id': sales_user.id,
        })

        # Test user tự động có security_group_id của sales_user
        self.assertIn(sales_user.security_group_id, test_user.group_ids)

        # Đổi vai trò sang sales_manager
        test_user.write({'role_preset_id': sales_manager.id})
        self.assertNotIn(sales_user.security_group_id, test_user.group_ids, "Old role scope group should be removed")
        self.assertIn(sales_manager.security_group_id, test_user.group_ids, "New role scope group should be added")

