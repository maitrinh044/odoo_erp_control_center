# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSgtErpFeatureAndPackage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Feature = cls.env['sgt.erp.feature'].with_context(active_test=False)
        cls.Package = cls.env['sgt.erp.package']

    def test_01_feature_is_enabled_helper(self):
        """Verify is_enabled API helper."""
        crm_feats = self.Feature.search([('code', '=', 'crm')])
        if not crm_feats:
            crm_feats = self.Feature.create({
                'name': 'Customer Relationship Management',
                'code': 'crm',
                'category': 'crm',
                'active': True
            })
        
        # Currently active
        crm_feats.write({'active': True})
        self.assertTrue(self.Feature.is_enabled('crm'))

        # Inactive
        crm_feats.write({'active': False})
        self.assertFalse(self.Feature.is_enabled('crm'))

        # Non-existent code
        self.assertFalse(self.Feature.is_enabled('invalid_non_existent_feature_code'))

    def test_02_packages_exist(self):
        """Verify existence of 4 standard packages."""
        packages = self.Package.search([])
        package_codes = packages.mapped('code')
        for code in ['starter', 'business', 'professional', 'enterprise']:
            self.assertIn(code, package_codes, f"Package '{code}' must exist!")

    def test_03_enterprise_package_contains_features(self):
        """Verify Enterprise package contains all features."""
        enterprise = self.Package.search([('code', '=', 'enterprise')], limit=1)
        self.assertTrue(enterprise, "Enterprise package must exist")
        self.assertTrue(len(enterprise.feature_ids) > 0, "Enterprise package should contain features")

    def test_04_menu_auto_sync_on_feature_toggle(self):
        """Verify automatic sync of hiding/showing corresponding Odoo menus when toggling Features."""
        crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
        if not crm_menu:
            # CRM module not installed, skip
            return

        crm_feats = self.Feature.search([('code', '=', 'crm')])
        if not crm_feats:
            crm_feats = self.Feature.create({
                'name': 'Customer Relationship Management',
                'code': 'crm',
                'category': 'crm',
                'active': True
            })
        crm_feat = crm_feats[0]
        self.assertTrue(crm_feat, "Feature CRM must exist in system")
        crm_feat.menu_xml_id = 'crm.crm_menu_root'
        crm_feat.auto_sync_menu = True

        # Disable CRM Feature -> CRM Menu must switch to active = False
        crm_feat.active = False
        self.assertFalse(crm_menu.active, "CRM Menu must be hidden (active=False) when CRM Feature is disabled")

        # Re-enable CRM Feature -> CRM Menu must switch to active = True
        crm_feat.active = True
        self.assertTrue(crm_menu.active, "CRM Menu must be visible (active=True) when CRM Feature is re-enabled")

    def test_05_direct_action_access_guard(self):
        """Verify direct action access guard when Feature is disabled."""
        from odoo.exceptions import AccessError
        
        target_model = 'crm.lead' if 'crm.lead' in self.env else 'res.partner'
        target_feat_code = 'crm' if target_model == 'crm.lead' else 'contacts'

        feats = self.Feature.search([('code', '=', target_feat_code)])
        if not feats:
            feats = self.Feature.create({
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

        # When feature is disabled -> _get_action_dict() raises AccessError
        feats.write({'active': False})
        non_su_env = self.env(su=False)
        guarded_act = act.with_env(non_su_env).with_context(install_mode=False, test_action_guard=True)
        with self.assertRaises(AccessError):
            guarded_act._get_action_dict()

        # When feature is re-enabled -> _get_action_dict() operates normally
        feats.write({'active': True})
        action_dict = guarded_act._get_action_dict()
        self.assertIsInstance(action_dict, dict)
        self.assertEqual(action_dict.get('res_model'), target_model)

    def test_06_package_switch_and_feature_activation(self):
        """Verify switching package from Starter to Enterprise and activating disabled features."""
        starter = self.Package.search([('code', '=', 'starter')], limit=1)
        enterprise = self.Package.search([('code', '=', 'enterprise')], limit=1)
        self.assertTrue(starter and enterprise, "Starter and Enterprise packages must exist")

        # 1. Apply Starter package -> CRM active, Sales and HR disabled
        starter.apply_to_company()
        self.assertTrue(self.Feature.is_enabled('crm'))
        self.assertFalse(self.Feature.is_enabled('sales'))
        self.assertFalse(self.Feature.is_enabled('hr'))

        # 2. Apply Enterprise package -> Sales and HR reactivated
        enterprise.apply_to_company()
        self.assertTrue(self.Feature.is_enabled('crm'))
        self.assertTrue(self.Feature.is_enabled('sales'), "Sales must be enabled in Enterprise package")
        self.assertTrue(self.Feature.is_enabled('hr'), "HR must be enabled in Enterprise package")

        # 3. Test action_apply_to_current_company button
        res = enterprise.action_apply_to_current_company()
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(self.env.company.erp_package_id.id, enterprise.id)

    def test_07_one_click_toggle_and_menu_sync(self):
        """Verify 1-click action_toggle_feature toggle operation."""
        crm_feats = self.Feature.search([('code', '=', 'crm')])
        if not crm_feats:
            crm_feats = self.Feature.create({
                'name': 'Customer Relationship Management',
                'code': 'crm',
                'category': 'crm',
                'active': True
            })
        crm_feat = crm_feats[0]
        crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)

        original_active = crm_feat.active
        # Click toggle
        res = crm_feat.action_toggle_feature()
        self.assertEqual(crm_feat.active, not original_active)
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(res.get('tag'), 'display_notification')
        if crm_menu:
            self.assertEqual(crm_menu.active, crm_feat.active)

        # Click toggle again to revert
        crm_feat.action_toggle_feature()
        self.assertEqual(crm_feat.active, original_active)
        if crm_menu:
            self.assertEqual(crm_menu.active, original_active)

    def test_08_action_enable_all_and_force_sync(self):
        """Verify Enable All and Force Sync All Menus actions."""
        # Disable 1 feature for testing
        crm_feats = self.Feature.search([('code', '=', 'crm')])
        if crm_feats:
            crm_feats.write({'active': False})

        res_enable = self.Feature.action_enable_all_features()
        self.assertEqual(res_enable.get('type'), 'ir.actions.client')
        crm_feats = self.Feature.search([('code', '=', 'crm')])
        if crm_feats:
            self.assertTrue(all(crm_feats.mapped('active')), "All features must be enabled")

        res_sync = self.Feature.action_force_sync_all_menus()
        self.assertEqual(res_sync.get('type'), 'ir.actions.client')

