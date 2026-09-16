# -*- coding: utf-8 -*-
{
    'name': 'SGT ERP Control Center',
    'version': '19.0.2.45.0',
    'summary': 'Centralized configuration, white-labeling, theme engine, feature toggle, and ERP administration',
    'description': """
SGT ERP Control Center (Version 2)
==================================
Central addon designed to configure, manage, and personalize the Odoo ERP system for each enterprise client.
Acts as a centralized control center for all ERP configurations, allowing implementation teams to deploy 
without modifying core source code per client (One ERP Codebase + Customer Configuration).

Key Highlights:
- Intuitive Control Center Dashboard displaying client info, versioning, feature status, and system health.
- Live Theme Preview (OWL Interactive Widget): Real-time visual preview for colors, typography, and layouts.
- Multi-step Guided Setup Wizard: 5-step guided wizard for swift client onboarding.
- Workflow & Approval Builder: Define dynamic multi-level approval stages with monetary threshold triggers.
- Runtime Approval Interceptors: Enforce approval limits on Sale Orders, Purchase Orders, and Vendor Bills.
- Visual Permission Matrix: 1-click visual matrix to configure CRUD user rights and role presets.
- Dynamic Theme Engine: Manage UI styling via real-time CSS Variables without server restarts.
- 8 Enterprise Theme Presets and custom preset cloning.
- Advanced System Health: Track disk usage, database size, backup status, and container uptime.
- Real-Time Hardware Telemetry: Task-manager style canvas charts monitoring CPU, RAM, Disk, and DB pools.
- Online License Client & Update Manager: Manage updates and online license verification with offline fallback.
    """,
    'category': 'Administration',
    'author': 'SaigonTrade (SGT)',
    'website': 'https://saigontrade.vn',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'sale', 'crm', 'purchase', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/theme_presets.xml',
        'data/feature_data.xml',
        'data/package_presets.xml',
        'data/role_presets.xml',
        'data/update_data.xml',
        'data/default_config.xml',
        'data/backup_cron.xml',
        'data/workflow_demo_data.xml',
        'data/product_demo_data.xml',
        'views/setup_wizard_views.xml',
        'views/control_center_views.xml',
        'views/health_dashboard_views.xml',
        'views/backup_views.xml',
        'views/erp_config_views.xml',
        'views/theme_views.xml',
        'views/feature_views.xml',
        'views/package_views.xml',
        'views/workflow_views.xml',
        'views/integration_views.xml',
        'views/add_module_matrix_wizard_views.xml',
        'views/role_preset_views.xml',
        'views/permission_matrix_views.xml',
        'views/update_views.xml',
        'views/license_views.xml',
        'views/res_company_views.xml',
        'views/res_users_views.xml',
        'views/audit_log_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/approval_wizard_views.xml',
        'views/mass_approval_wizard_views.xml',
        'views/login_templates.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sgt_erp_control_center/static/src/scss/backend.scss',
            'sgt_erp_control_center/static/src/scss/navbar.scss',
            'sgt_erp_control_center/static/src/scss/forms.scss',
            'sgt_erp_control_center/static/src/scss/list.scss',
            'sgt_erp_control_center/static/src/scss/kanban.scss',
            'sgt_erp_control_center/static/src/scss/health_monitor.scss',
            'sgt_erp_control_center/static/src/js/theme_service.js',
            'sgt_erp_control_center/static/src/js/live_theme_preview.js',
            'sgt_erp_control_center/static/src/js/system_health_live_chart.js',
            'sgt_erp_control_center/static/src/xml/theme_preview.xml',
            'sgt_erp_control_center/static/src/xml/live_theme_preview.xml',
            'sgt_erp_control_center/static/src/xml/system_health_live_chart.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
