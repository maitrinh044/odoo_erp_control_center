# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSgtErpFeatureAndPackage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Feature = cls.env['sgt.erp.feature']
        cls.Package = cls.env['sgt.erp.package']

    def test_01_feature_is_enabled_helper(self):
        """Kiểm tra API helper is_enabled"""
        crm_feat = self.Feature.search([('code', '=', 'crm')], limit=1)
        if not crm_feat:
            crm_feat = self.Feature.create({
                'name': 'Customer Relationship Management',
                'code': 'crm',
                'category': 'crm',
                'active': True
            })
        
        # Đang bật
        crm_feat.active = True
        self.assertTrue(self.Feature.is_enabled('crm'))

        # Tắt
        crm_feat.active = False
        self.assertFalse(self.Feature.is_enabled('crm'))

        # Mã không tồn tại
        self.assertFalse(self.Feature.is_enabled('invalid_non_existent_feature_code'))

    def test_02_packages_exist(self):
        """Kiểm tra sự tồn tại của 4 gói phần mềm chuẩn"""
        packages = self.Package.search([])
        package_codes = packages.mapped('code')
        for code in ['starter', 'business', 'professional', 'enterprise']:
            self.assertIn(code, package_codes, f"Package '{code}' must exist!")

    def test_03_enterprise_package_contains_features(self):
        """Kiểm tra gói Enterprise bao gồm đầy đủ các tính năng"""
        enterprise = self.Package.search([('code', '=', 'enterprise')], limit=1)
        self.assertTrue(enterprise, "Enterprise package must exist")
        self.assertTrue(len(enterprise.feature_ids) > 0, "Enterprise package should contain features")

    def test_04_menu_auto_sync_on_feature_toggle(self):
        """Kiểm tra việc tự động đồng bộ ẩn/hiện menu Odoo tương ứng khi bật/tắt Feature"""
        crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
        if not crm_menu:
            # Module CRM chưa cài đặt thì bỏ qua
            return

        crm_feat = self.Feature.search([('code', '=', 'crm')], limit=1)
        self.assertTrue(crm_feat, "Feature CRM phải tồn tại trong hệ thống")
        crm_feat.menu_xml_id = 'crm.crm_menu_root'
        crm_feat.auto_sync_menu = True

        # Tắt CRM Feature -> Menu CRM phải chuyển sang active = False
        crm_feat.active = False
        self.assertFalse(crm_menu.active, "Menu CRM phải bị ẩn (active=False) khi Feature CRM bị tắt")

        # Bật lại CRM Feature -> Menu CRM phải chuyển sang active = True
        crm_feat.active = True
        self.assertTrue(crm_menu.active, "Menu CRM phải hiển thị (active=True) khi Feature CRM được bật lại")

    def test_05_direct_action_access_guard(self):
        """Kiểm tra việc chặn truy cập Action trực tiếp khi Feature bị tắt"""
        from odoo.exceptions import AccessError
        
        target_model = 'crm.lead' if 'crm.lead' in self.env else 'res.partner'
        target_feat_code = 'crm' if target_model == 'crm.lead' else 'contacts'

        feat = self.Feature.search([('code', '=', target_feat_code)], limit=1)
        if not feat:
            feat = self.Feature.create({
                'name': f'Test {target_feat_code.upper()} Feature',
                'code': target_feat_code,
                'category': 'system',
                'active': True,
            })

        act = self.env['ir.actions.act_window'].create({
            'name': f'Test {target_feat_code.upper()} Action',
            'res_model': target_model,
            'view_mode': 'tree,form',
        })

        # Khi Feature bị tắt -> _get_action_dict() phải bắn AccessError
        feat.active = False
        non_su_env = self.env(su=False)
        guarded_act = act.with_env(non_su_env).with_context(install_mode=False, test_action_guard=True)
        with self.assertRaises(AccessError):
            guarded_act._get_action_dict()

        # Khi Feature được bật lại -> _get_action_dict() hoạt động bình thường
        feat.active = True
        action_dict = guarded_act._get_action_dict()
        self.assertIsInstance(action_dict, dict)
        self.assertEqual(action_dict.get('res_model'), target_model)

    def test_06_package_switch_and_feature_activation(self):
        """Kiểm tra việc chuyển đổi gói từ Starter sang Enterprise và kích hoạt các tính năng bị tắt"""
        starter = self.Package.search([('code', '=', 'starter')], limit=1)
        enterprise = self.Package.search([('code', '=', 'enterprise')], limit=1)
        self.assertTrue(starter and enterprise, "Starter and Enterprise packages must exist")

        # 1. Áp dụng gói Starter -> CRM bật, Sales và HR tắt
        starter.apply_to_company()
        self.assertTrue(self.Feature.is_enabled('crm'))
        self.assertFalse(self.Feature.is_enabled('sales'))
        self.assertFalse(self.Feature.is_enabled('hr'))

        # 2. Áp dụng gói Enterprise -> Sales và HR phải được kích hoạt lại thành công
        enterprise.apply_to_company()
        self.assertTrue(self.Feature.is_enabled('crm'))
        self.assertTrue(self.Feature.is_enabled('sales'), "Sales must be enabled in Enterprise package")
        self.assertTrue(self.Feature.is_enabled('hr'), "HR must be enabled in Enterprise package")

        # 3. Kiểm tra nút action_apply_to_current_company
        res = enterprise.action_apply_to_current_company()
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(self.env.company.erp_package_id.id, enterprise.id)

    def test_07_one_click_toggle_and_menu_sync(self):
        """Kiểm tra thao tác Bật/Tắt 1-chạm action_toggle_feature"""
        crm_feat = self.Feature.search([('code', '=', 'crm')], limit=1)
        self.assertTrue(crm_feat)
        crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)

        original_active = crm_feat.active
        # Bấm toggle
        res = crm_feat.action_toggle_feature()
        self.assertEqual(crm_feat.active, not original_active)
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(res.get('tag'), 'display_notification')
        if crm_menu:
            self.assertEqual(crm_menu.active, crm_feat.active)

        # Bấm toggle lần nữa để trả về trạng thái cũ
        crm_feat.action_toggle_feature()
        self.assertEqual(crm_feat.active, original_active)
        if crm_menu:
            self.assertEqual(crm_menu.active, original_active)

    def test_08_action_enable_all_and_force_sync(self):
        """Kiểm tra hành động Bật tất cả và Đồng bộ lại toàn bộ Menu"""
        # Tắt thử 1 feature
        crm_feat = self.Feature.search([('code', '=', 'crm')], limit=1)
        if crm_feat:
            crm_feat.active = False

        res_enable = self.Feature.action_enable_all_features()
        self.assertEqual(res_enable.get('type'), 'ir.actions.client')
        if crm_feat:
            self.assertTrue(crm_feat.active, "Tất cả feature phải được bật")

        res_sync = self.Feature.action_force_sync_all_menus()
        self.assertEqual(res_sync.get('type'), 'ir.actions.client')

