# SGT ERP Control Center (Odoo 19 Enterprise / Community Edition)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67.svg?style=flat&logo=odoo)](https://www.odoo.com)
[![Module Version](https://img.shields.io/badge/Version-19.0.2.45.0-blue.svg)](https://github.com/maitrinh044/odoo_erp_control_center)
[![License](https://img.shields.io/badge/License-LGPL--3-green.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Test Suite](https://img.shields.io/badge/Tests-97%2F97%20Passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)

**SGT ERP Control Center** is a professional management, configuration, and control center solution for Odoo ERP systems designed for enterprises and implementation partners. The module adopts a **One ERP Codebase + Multi-tenant/Customer Configuration** architecture, optimizing configuration management, access rights, visual branding, and business workflows without modifying core source code.

---

## 🚀 Key Features

### 1. 🎛️ Feature Manager & Dynamic Menu (One-Click Feature Toggle)
- **1-Click Feature Toggle**: Administrators can instantly toggle core modules (Purchasing, Sales, CRM, Accounting & Invoicing, Inventory, HR, LMS Training, Projects, Appointments...) with a single click.
- **100% Data Preservation**: No need to uninstall modules (`uninstall`), ensuring zero data loss of existing documents or configurations.
- **Dynamic Menu Visibility**: Corresponding menus automatically hide or show immediately via registry cache clearing (`registry.clear_all_caches()`).
- **Direct Action & URL Guard**: Blocks users from directly accessing documents via URL or action when the associated feature is disabled.
- **Intuitive List UI**: Clean management view with quick toggle switches, technical codes, modules, and business descriptions.

### 2. 📋 Workflow & Sequential Multi-Level Approval
- **Tiered Threshold Approval**: Configure multi-level approval workflows (Team Lead $\rightarrow$ Chief Accountant $\rightarrow$ Board of Directors) based on document total amount.
- **Proactive Workflow Selection (Hybrid Logic)**: Allows employees to proactively select an appropriate approval workflow when creating Quotations (`sale.order`), Purchase Orders (`purchase.order`), or Vendor Bills (`account.move`).
- **Runtime Interceptor**: Automatically intercepts document confirmation actions until all required approval levels have been granted.
- **Mass Approval Wizard**: Batch process mixed documents simultaneously, requiring a mandatory note upon rejection.
- **Embedded Document Line Tabs**: Inspect product details, quantities, unit prices, and sub-totals directly on the approver screen without navigating away.

### 3. 🎨 Dynamic Theme Engine & Live Theme Preview
- **White-labeling & Branding**: Customize Primary Colors, Navbar Colors, typography, and company logos.
- **CSS Variables Injection**: Instantly apply color and style changes via CSS Variables without restarting Odoo services.
- **Live Theme Preview (OWL 3 Interactive Widget)**: Real-time interactive preview before saving configurations.
- **8 Pre-built Theme Presets**: Ready-to-use themes including Corporate Blue, Emerald Growth, Sunset Amber, Modern Dark, Luxury Gold, and more.

### 4. 📊 Hardware Telemetry & System Health Monitor
- **Real-time Waveform Canvas**: Live CPU, RAM, Disk I/O, and Database Connection telemetry monitoring (Windows Task Manager style).
- **Health Dashboard**: Real-time storage capacity, database size, backup status, and Docker container health monitoring.

### 5. 👥 Visual Permission Matrix & Role Presets
- **Visual Permission Grid**: Granular permission matrix (Read, Write, Create, Delete, Export) per model and module.
- **Role Presets**: Preconfigured standard roles (Sales Manager, Sales User, Accountant, HR Admin...) with data scopes (`own`, `team`, `all`).

---

## 🛠️ Technical Requirements

- **Odoo Version**: 19.0 Community / Enterprise
- **Python Version**: 3.10+
- **Dependencies**: `base`, `web`, `mail`
- **Optional Integrations**: `sale_management`, `purchase`, `account`, `crm`, `stock`, `hr`, `project`, `lms`

---

## 📦 Installation & Configuration

### 1. Clone the repository into your addons directory
```bash
cd /path/to/your/odoo/addons
git clone https://github.com/maitrinh044/odoo_erp_control_center.git sgt_erp_control_center
```

### 2. Update Apps List in Odoo
- Launch Odoo and log in with Administrator credentials.
- Enable **Developer Mode**.
- Go to **Apps** $\rightarrow$ Click **Update Apps List**.
- Search for `SGT ERP Control Center` and click **Install**.

### 3. Or update via CLI / Docker
```bash
odoo -u sgt_erp_control_center -d <your_database_name> --stop-after-init
```

---

## 🧪 Automated Testing

The module comes with a comprehensive test suite with **97/97 tests passing 100%**:

```bash
odoo -d <database_name> --test-enable --stop-after-init -u sgt_erp_control_center --test-tags=sgt_erp_control_center
```

**Key Test Suites:**
- `TestSgtErpControlCenter`: Tests Dashboard, Global Config, and White-labeling.
- `TestSgtErpFeatureAndPackage`: Tests feature toggles, dynamic menu visibility, and cache invalidation.
- `TestWorkflowRuntimeInterceptor`: Tests sales approval interceptor, amount thresholds, and mandatory CRM fields.
- `TestPurchaseAccountApproval`: Tests multi-level approval for Purchasing and Vendor Bills.
- `TestWorkflowSelection`: Tests employee workflow selection on documents.
- `TestDemoProductsAndSalesman`: Tests 50 demo products and Salesman role isolation.
- `TestMassApprovalAndDemoData`: Tests mass approval and rejection workflows.
- `TestHealthLiveStats`: Tests real-time hardware telemetry collectors.

---

## 📂 Folder Structure

```text
sgt_erp_control_center/
├── __init__.py
├── __manifest__.py                  # Metadata & dependencies
├── controllers/                     # API Webhook & Health check endpoints
├── data/                            # Default data (Features, Workflows, Themes, 50 Products)
├── i18n/                            # Multilingual translation files (vi_VN)
├── models/                          # Database models & business logic
│   ├── erp_feature.py               # Feature manager & dynamic menu sync
│   ├── erp_feature_guard.py         # Direct action & URL access guard
│   ├── erp_workflow.py              # Workflow engine & approval levels
│   ├── erp_purchase_workflow.py     # Purchase order workflow integration
│   ├── erp_account_workflow.py      # Vendor bill / accounting workflow integration
│   ├── erp_workflow_interceptor.py  # Sales & CRM runtime interceptors
│   ├── erp_theme.py                 # Theme engine & CSS variables
│   ├── erp_config.py                # Branding & white-labeling configuration
│   ├── erp_permission_matrix.py     # Permission matrix engine
│   └── ...
├── static/                          # CSS/SCSS, OWL JavaScript Widgets & XML Templates
├── tests/                           # Automated test suite (Unit & Integration Tests)
├── views/                           # XML Views (Forms, Lists, Kanbans, Menus)
└── wizard/                          # Wizards (Setup Wizard, Approval Wizard, Mass Approval)
```

---

## 📄 License

This project is licensed under [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html).  
© 2026 SGT ERP Team. All rights reserved.
