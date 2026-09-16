# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSgtErpThemeAndBranding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Theme = cls.env['sgt.erp.theme']
        cls.company = cls.env.company
        cls.user = cls.env.user

    def test_01_theme_presets_exist(self):
        """Verify existence of 8 standard theme presets."""
        expected_presets = [
            'Corporate Blue',
            'Modern Green',
            'China Red',
            'Medical Clean',
            'Industrial Orange',
            'Dark Tech',
            'Luxury Gold',
            'Odoo Default'
        ]
        themes = self.Theme.search([])
        theme_names = themes.mapped('name')
        for expected in expected_presets:
            self.assertIn(expected, theme_names, f"Preset '{expected}' must exist!")

    def test_02_create_from_preset(self):
        """Verify duplicating a theme from preset."""
        preset = self.Theme.search([('name', '=', 'Corporate Blue')], limit=1)
        self.assertTrue(preset, "Corporate Blue preset must exist")
        
        action = preset.action_create_from_preset()
        new_theme_id = action.get('res_id')
        new_theme = self.Theme.browse(new_theme_id)
        self.assertTrue(new_theme.exists())
        self.assertIn("(Custom Copy)", new_theme.name)
        self.assertEqual(new_theme.primary_color, preset.primary_color)

    def test_03_theme_effective_priority(self):
        """Verify priority order: User Theme -> Company Theme -> Default Theme."""
        theme_corp = self.Theme.search([('name', '=', 'Corporate Blue')], limit=1)
        theme_dark = self.Theme.search([('name', '=', 'Dark Tech')], limit=1)
        
        # 1. Company Theme
        self.company.erp_theme_id = theme_corp.id
        self.user.use_custom_theme = False
        self.assertEqual(self.user.get_effective_theme(), theme_corp)

        # 2. User Theme override
        self.user.use_custom_theme = True
        self.user.erp_theme_id = theme_dark.id
        self.assertEqual(self.user.get_effective_theme(), theme_dark)

    def test_04_kanban_and_list_striping(self):
        """Verify Kanban background and List row striping CSS variables configuration."""
        theme = self.Theme.create({
            'name': 'Test Kanban & Striping Theme',
            'kanban_bg_color': '#FAFAFA',
            'list_alternate_row': True,
        })
        css_vars = theme.get_css_variables()
        self.assertEqual(css_vars.get('--sgt-kanban-bg'), '#FAFAFA')
        self.assertEqual(css_vars.get('--sgt-list-striped'), '1')
        self.assertIn('rgba', css_vars.get('--sgt-list-stripe-bg'))

        theme.list_alternate_row = False
        css_vars_disabled = theme.get_css_variables()
        self.assertEqual(css_vars_disabled.get('--sgt-list-striped'), '0')
        self.assertEqual(css_vars_disabled.get('--sgt-list-stripe-bg'), 'transparent')

    def test_05_gradient_generator(self):
        """Verify Visual Gradient Generator and CSS variable generation for gradients."""
        theme = self.Theme.create({
            'name': 'Test Gradient Theme',
            'navbar_gradient_enabled': True,
            'navbar_gradient_color1': '#09244B',
            'navbar_gradient_color2': '#165DFF',
            'navbar_gradient_angle': '135deg',
            'btn_gradient_enabled': True,
            'btn_gradient_color1': '#165DFF',
            'btn_gradient_color2': '#722ED1',
            'btn_gradient_angle': '90deg',
            'sidebar_gradient_enabled': True,
            'sidebar_gradient_color1': '#071A34',
            'sidebar_gradient_color2': '#0F3460',
            'sidebar_gradient_angle': '180deg',
        })
        css_vars = theme.get_css_variables()
        self.assertIn('linear-gradient(135deg, #09244B 0%, #165DFF 100%)', css_vars.get('--sgt-navbar-bg'))
        self.assertIn('linear-gradient(90deg, #165DFF 0%, #722ED1 100%)', css_vars.get('--sgt-btn-primary'))
        self.assertIn('linear-gradient(180deg, #071A34 0%, #0F3460 100%)', css_vars.get('--sgt-sidebar-bg'))

        # Test Radial gradient
        theme.navbar_gradient_angle = 'radial'
        css_vars_radial = theme.get_css_variables()
        self.assertIn('radial-gradient(circle, #09244B 0%, #165DFF 100%)', css_vars_radial.get('--sgt-navbar-bg'))

    def test_06_login_page_branding(self):
        """Verify Login page branding configuration (login_logo, login_background, QWeb layout)."""
        config = self.env['sgt.erp.config'].sudo().search([('company_id', '=', self.company.id)], limit=1)
        if not config:
            config = self.env['sgt.erp.config'].sudo().create({
                'company_id': self.company.id,
                'product_name': 'SGT Enterprise ERP',
                'footer_text': 'Copyright 2026 SGT Corporation',
            })
        else:
            config.write({
                'product_name': 'SGT Enterprise ERP',
                'footer_text': 'Copyright 2026 SGT Corporation',
            })

        # Test login template inheritance
        login_view = self.env.ref('sgt_erp_control_center.sgt_login_layout', raise_if_not_found=False)
        self.assertTrue(login_view, "Template sgt_login_layout must be registered")
        self.assertEqual(login_view.inherit_id.key, 'web.login_layout')
        self.assertIn('/sgt_erp/login_logo', login_view.arch)
        self.assertIn('/sgt_erp/login_background', login_view.arch)
        self.assertIn('sgt_login_body', login_view.arch)

        # Test apply configuration deactivates website.login_layout
        config.action_apply_configuration()
        wl = self.env['ir.ui.view'].sudo().search([('key', '=', 'website.login_layout')], limit=1)
        if wl:
            self.assertFalse(wl.active, "website.login_layout must be deactivated for dedicated ERP login")
