# -*- coding: utf-8 -*-
{
    'name': 'SGT ERP Control Center',
    'version': '19.0.2.39.0',
    'summary': 'Trung tâm cấu hình, white-labeling, theme, feature toggle và quản trị ERP',
    'description': """
SGT ERP Control Center (Version 2)
==================================
Addon trung tâm dùng để cấu hình, quản lý và cá nhân hóa hệ thống Odoo ERP cho từng khách hàng.
Đóng vai trò là trung tâm điều khiển toàn bộ cấu hình ERP, giúp đội triển khai không phải chỉnh sửa
source code riêng cho từng khách hàng (One ERP Codebase + Customer Configuration).

Các tính năng nổi bật:
- Control Center Dashboard trực quan hiển thị thông tin khách hàng, phiên bản, trạng thái chức năng và health check.
- Live Theme Preview (OWL Interactive Widget): Xem trước màu sắc, typography và bố cục theo thời gian thực.
- Multi-step Guided Setup Wizard: Hướng dẫn cấu hình hệ thống 5 bước cho kỹ thuật viên triển khai.
- Workflow & Approval Builder: Định nghĩa các bước quy trình và luân chuyển phê duyệt đa cấp theo hạn mức.
- Runtime Approval Interceptor: Tự động chặn xác nhận đơn bán vượt hạn mức và kiểm soát trường bắt buộc CRM.
- Visual Permission Matrix: Thiết lập ma trận phân quyền người dùng trực quan một chạm.
- Dynamic Theme Engine: Quản lý màu sắc bằng biến CSS Variables không cần restart Odoo.
- 8 Theme Presets sẵn có và khả năng nhân bản từ Preset.
- Advanced System Health: Đo lường Disk Usage, Database Size, Backup Status và Deployment Container.
- Real-Time Hardware Telemetry: Biểu đồ dạng sóng trực quan đo CPU, RAM, Disk, DB connections theo thời gian thực (OWL 3 + HTML5 Canvas phong cách Task Manager).
- Online License Client & Update Manager: Quản lý phiên bản cập nhật và kích hoạt bản quyền từ xa an toàn.
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
