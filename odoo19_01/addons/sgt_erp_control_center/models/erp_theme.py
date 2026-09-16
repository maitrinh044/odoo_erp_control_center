# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SgtErpTheme(models.Model):
    _name = 'sgt.erp.theme'
    _description = 'SGT ERP Theme Manager'
    _order = 'id asc'

    name = fields.Char(string='Theme Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    style = fields.Selection([
        ('default', 'Default'),
        ('corporate', 'Corporate'),
        ('modern', 'Modern'),
        ('minimal', 'Minimal'),
        ('rounded', 'Rounded'),
        ('flat', 'Flat'),
        ('dark', 'Dark'),
        ('luxury', 'Luxury'),
        ('glass', 'Glass'),
        ('industrial', 'Industrial')
    ], string='Style', default='corporate', required=True)

    # Colors
    primary_color = fields.Char(string='Primary Color', default='#165DFF', required=True)
    secondary_color = fields.Char(string='Secondary Color', default='#09244B')
    accent_color = fields.Char(string='Accent Color', default='#FFB020')
    background_color = fields.Char(string='Background Color', default='#F5F7FA')
    card_background = fields.Char(string='Card Background', default='#FFFFFF')
    text_color = fields.Char(string='Text Color', default='#1F2937')
    secondary_text_color = fields.Char(string='Secondary Text Color', default='#6B7280')
    border_color = fields.Char(string='Border Color', default='#E5E7EB')

    # Navbar
    navbar_bg = fields.Char(string='Navbar Background', default='#09244B')
    navbar_text_color = fields.Char(string='Navbar Text Color', default='#FFFFFF')
    navbar_hover_color = fields.Char(string='Navbar Hover Color', default='#165DFF')

    # Sidebar
    sidebar_bg = fields.Char(string='Sidebar Background', default='#071A34')
    sidebar_text_color = fields.Char(string='Sidebar Text Color', default='#D1D5DB')
    sidebar_hover_color = fields.Char(string='Sidebar Hover Color', default='#165DFF')
    sidebar_active_color = fields.Char(string='Sidebar Active Color', default='#165DFF')

    # Button
    btn_primary_color = fields.Char(string='Primary Button Color', default='#165DFF')
    btn_secondary_color = fields.Char(string='Secondary Button Color', default='#6B7280')
    btn_text_color = fields.Char(string='Button Text Color', default='#FFFFFF')
    btn_radius = fields.Integer(string='Button Radius (px)', default=6)

    # Card
    card_radius = fields.Integer(string='Card Radius (px)', default=10)
    card_shadow = fields.Selection([
        ('none', 'None'),
        ('sm', 'Small'),
        ('md', 'Medium'),
        ('lg', 'Large')
    ], string='Card Shadow', default='md')

    # Kanban & List
    kanban_bg_color = fields.Char(string='Kanban Background', default='#FFFFFF')
    list_alternate_row = fields.Boolean(string='List Row Striping', default=True)

    # Gradient Generator & Presets
    gradient_preset = fields.Selection([
        ('ocean_blue', 'Corporate Ocean (#09244B → #165DFF)'),
        ('royal_purple', 'Royal Luxury (#3B0764 → #7E22CE)'),
        ('emerald_tech', 'Emerald Energy (#064E3B → #059669)'),
        ('sunset_orange', 'Sunset Glow (#7C2D12 → #EA580C)'),
        ('cyber_indigo', 'Modern Cyber Indigo (#1E1B4B → #4338CA)'),
        ('dark_graphite', 'Minimalist Graphite (#111827 → #374151)'),
        ('rose_crimson', 'Vibrant Crimson (#881337 → #E11D48)'),
        ('midnight_blue', 'Midnight Deep (#020617 → #1E293B)'),
        ('aurora_teal', 'Aurora Teal (#0F172A → #0D9488)'),
    ], string='Apply Gradient Preset')

    # Navbar Gradient
    navbar_gradient_enabled = fields.Boolean(string='Enable Navbar Gradient', default=False)
    navbar_gradient_color1 = fields.Char(string='Navbar Gradient Start', default='#09244B')
    navbar_gradient_color2 = fields.Char(string='Navbar Gradient End', default='#165DFF')
    navbar_gradient_angle = fields.Selection([
        ('90deg', 'Left to Right (90°)'),
        ('135deg', 'Diagonal Top-Left to Bottom-Right (135°)'),
        ('180deg', 'Top to Bottom (180°)'),
        ('45deg', 'Diagonal Bottom-Left to Top-Right (45°)'),
        ('radial', 'Radial (Center to Edges)'),
    ], string='Navbar Gradient Angle', default='135deg')

    # Primary Button Gradient
    btn_gradient_enabled = fields.Boolean(string='Enable Button Gradient', default=False)
    btn_gradient_color1 = fields.Char(string='Button Gradient Start', default='#165DFF')
    btn_gradient_color2 = fields.Char(string='Button Gradient End', default='#722ED1')
    btn_gradient_angle = fields.Selection([
        ('90deg', 'Left to Right (90°)'),
        ('135deg', 'Diagonal (135°)'),
        ('180deg', 'Top to Bottom (180°)'),
    ], string='Button Gradient Angle', default='135deg')

    # Sidebar Gradient
    sidebar_gradient_enabled = fields.Boolean(string='Enable Sidebar Gradient', default=False)
    sidebar_gradient_color1 = fields.Char(string='Sidebar Gradient Start', default='#071A34')
    sidebar_gradient_color2 = fields.Char(string='Sidebar Gradient End', default='#0F3460')
    sidebar_gradient_angle = fields.Selection([
        ('180deg', 'Top to Bottom (180°)'),
        ('90deg', 'Left to Right (90°)'),
        ('135deg', 'Diagonal (135°)'),
    ], string='Sidebar Gradient Angle', default='180deg')

    @api.onchange('gradient_preset')
    def _onchange_gradient_preset(self):
        presets = {
            'ocean_blue': ('#09244B', '#165DFF'),
            'royal_purple': ('#3B0764', '#7E22CE'),
            'emerald_tech': ('#064E3B', '#059669'),
            'sunset_orange': ('#7C2D12', '#EA580C'),
            'cyber_indigo': ('#1E1B4B', '#4338CA'),
            'dark_graphite': ('#111827', '#374151'),
            'rose_crimson': ('#881337', '#E11D48'),
            'midnight_blue': ('#020617', '#1E293B'),
            'aurora_teal': ('#0F172A', '#0D9488'),
        }
        if self.gradient_preset and self.gradient_preset in presets:
            c1, c2 = presets[self.gradient_preset]
            self.navbar_gradient_enabled = True
            self.navbar_gradient_color1 = c1
            self.navbar_gradient_color2 = c2
            self.navbar_gradient_angle = '135deg'
            self.btn_gradient_enabled = True
            self.btn_gradient_color1 = c2
            self.btn_gradient_color2 = c1
            self.btn_gradient_angle = '135deg'

    # Forms
    form_bg = fields.Char(string='Form Background', default='#FFFFFF')
    input_bg = fields.Char(string='Input Background', default='#FFFFFF')
    input_border_color = fields.Char(string='Input Border Color', default='#D1D5DB')
    input_radius = fields.Integer(string='Input Radius (px)', default=6)

    # Font
    font_family = fields.Selection([
        ('system', 'System Default (-apple-system, BlinkMacSystemFont, Segoe UI)'),
        ('arial', 'Arial, sans-serif'),
        ('roboto', 'Roboto, sans-serif'),
        ('inter', 'Inter, sans-serif'),
        ('poppins', 'Poppins, sans-serif'),
        ('open_sans', 'Open Sans, sans-serif'),
        ('montserrat', 'Montserrat, sans-serif')
    ], string='Font Family', default='inter', required=True)
    font_size = fields.Integer(string='Font Size (px)', default=14)
    menu_font_size = fields.Integer(string='Menu Font Size (px)', default=14)
    heading_font_size = fields.Integer(string='Heading Font Size (px)', default=20)
    font_weight = fields.Selection([
        ('normal', 'Normal (400)'),
        ('medium', 'Medium (500)'),
        ('semibold', 'Semi-Bold (600)'),
        ('bold', 'Bold (700)')
    ], string='Font Weight', default='normal')

    def get_font_stack(self):
        self.ensure_one()
        mapping = {
            'system': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            'arial': 'Arial, "Helvetica Neue", Helvetica, sans-serif',
            'roboto': '"Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            'inter': '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            'poppins': '"Poppins", sans-serif',
            'open_sans': '"Open Sans", sans-serif',
            'montserrat': '"Montserrat", sans-serif',
        }
        return mapping.get(self.font_family, mapping['inter'])

    def get_css_variables(self):
        """Return dictionary containing CSS variables for frontend DOM root injection"""
        self.ensure_one()
        shadow_map = {
            'none': 'none',
            'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
            'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
            'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        }
        weight_map = {
            'normal': '400',
            'medium': '500',
            'semibold': '600',
            'bold': '700',
        }
        # Compute dynamic gradients if enabled
        effective_navbar_bg = self.navbar_bg or '#09244B'
        if self.navbar_gradient_enabled and self.navbar_gradient_color1 and self.navbar_gradient_color2:
            if self.navbar_gradient_angle == 'radial':
                effective_navbar_bg = f"radial-gradient(circle, {self.navbar_gradient_color1} 0%, {self.navbar_gradient_color2} 100%)"
            else:
                effective_navbar_bg = f"linear-gradient({self.navbar_gradient_angle}, {self.navbar_gradient_color1} 0%, {self.navbar_gradient_color2} 100%)"

        effective_btn_primary = self.btn_primary_color or '#165DFF'
        if self.btn_gradient_enabled and self.btn_gradient_color1 and self.btn_gradient_color2:
            effective_btn_primary = f"linear-gradient({self.btn_gradient_angle}, {self.btn_gradient_color1} 0%, {self.btn_gradient_color2} 100%)"

        effective_sidebar_bg = self.sidebar_bg or '#071A34'
        if self.sidebar_gradient_enabled and self.sidebar_gradient_color1 and self.sidebar_gradient_color2:
            effective_sidebar_bg = f"linear-gradient({self.sidebar_gradient_angle}, {self.sidebar_gradient_color1} 0%, {self.sidebar_gradient_color2} 100%)"

        return {
            '--sgt-primary': self.primary_color or '#165DFF',
            '--sgt-secondary': self.secondary_color or '#09244B',
            '--sgt-accent': self.accent_color or '#FFB020',
            '--sgt-background': self.background_color or '#F5F7FA',
            '--sgt-card-bg': self.card_background or '#FFFFFF',
            '--sgt-text': self.text_color or '#1F2937',
            '--sgt-text-secondary': self.secondary_text_color or '#6B7280',
            '--sgt-border': self.border_color or '#E5E7EB',
            
            '--sgt-navbar-bg': effective_navbar_bg,
            '--sgt-navbar-text': self.navbar_text_color or '#FFFFFF',
            '--sgt-navbar-hover': self.navbar_hover_color or '#165DFF',

            '--sgt-sidebar-bg': effective_sidebar_bg,
            '--sgt-sidebar-text': self.sidebar_text_color or '#D1D5DB',
            '--sgt-sidebar-hover': self.sidebar_hover_color or '#165DFF',
            '--sgt-sidebar-active': self.sidebar_active_color or '#165DFF',

            '--sgt-btn-primary': effective_btn_primary,
            '--sgt-btn-secondary': self.btn_secondary_color or '#6B7280',
            '--sgt-btn-text': self.btn_text_color or '#FFFFFF',
            '--sgt-btn-radius': f'{self.btn_radius or 6}px',

            '--sgt-card-radius': f'{self.card_radius or 10}px',
            '--sgt-card-shadow': shadow_map.get(self.card_shadow, shadow_map['md']),
            '--sgt-kanban-bg': self.kanban_bg_color or self.card_background or '#FFFFFF',
            '--sgt-list-stripe-bg': 'rgba(0, 0, 0, 0.025)' if self.list_alternate_row else 'transparent',
            '--sgt-list-striped': '1' if self.list_alternate_row else '0',

            '--sgt-form-bg': self.form_bg or '#FFFFFF',
            '--sgt-input-bg': self.input_bg or '#FFFFFF',
            '--sgt-input-border': self.input_border_color or '#D1D5DB',
            '--sgt-input-radius': f'{self.input_radius or 6}px',

            '--sgt-font-family': self.get_font_stack(),
            '--sgt-font-size': f'{self.font_size or 14}px',
            '--sgt-menu-font-size': f'{self.menu_font_size or 14}px',
            '--sgt-heading-font-size': f'{self.heading_font_size or 20}px',
            '--sgt-font-weight': weight_map.get(self.font_weight, '400'),
        }

    def action_apply_to_current_company(self):
        self.ensure_one()
        company = self.env.company
        company.write({'erp_theme_id': self.id})
        config = self.env['sgt.erp.config'].search([('company_id', '=', company.id)], limit=1)
        if config:
            config.write({'theme_id': self.id})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_preview_theme(self):
        """Activate live visual theme preview - directly apply CSS variables to active session"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'sgt_preview_theme_action',
            'params': {
                'theme_name': self.name,
                'css_variables': self.get_css_variables(),
                'is_reset': False,
            }
        }

    def action_reset_preview(self):
        """Revert visual preview to current company active theme"""
        company = self.env.company
        active_theme = company.erp_theme_id or self.search([('style', '=', 'default')], limit=1)
        if not active_theme:
            active_theme = self.search([], limit=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'sgt_preview_theme_action',
            'params': {
                'theme_name': active_theme.name,
                'css_variables': active_theme.get_css_variables(),
                'is_reset': True,
            }
        }

    def action_create_from_preset(self):
        """Clone theme preset into a customizable theme"""
        self.ensure_one()
        new_theme = self.copy({'name': f"{self.name} (Custom Copy)"})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sgt.erp.theme',
            'view_mode': 'form',
            'res_id': new_theme.id,
            'target': 'current',
        }
