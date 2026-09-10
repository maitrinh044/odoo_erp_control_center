# SGT ERP Control Center (Odoo 19 Enterprise / Community Edition)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67.svg?style=flat&logo=odoo)](https://www.odoo.com)
[![Module Version](https://img.shields.io/badge/Version-19.0.2.35.0-blue.svg)](https://github.com/maitrinh044/odoo_erp_control_center)
[![License](https://img.shields.io/badge/License-LGPL--3-green.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Test Suite](https://img.shields.io/badge/Tests-97%2F97%20Passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)

**SGT ERP Control Center** là giải pháp trung tâm điều khiển, cấu hình và quản trị hệ thống Odoo ERP chuyên nghiệp dành cho doanh nghiệp và các đơn vị triển khai. Module áp dụng kiến trúc **One ERP Codebase + Multi-tenant/Customer Configuration**, giúp tối ưu hóa việc quản lý cấu hình, phân quyền, giao diện thương hiệu và quy trình nghiệp vụ mà không cần chỉnh sửa trực tiếp mã nguồn.

---

## 🚀 Tính Năng Nổi Bật (Key Features)

### 1. 🎛️ Feature Manager & Dynamic Menu (Bật/Tắt Tính Năng Một Chạm)
- **1-Click Feature Toggle**: Quản trị viên có thể Bật/Tắt tức thì các phân hệ cốt lõi (Mua hàng, Bán hàng, CRM, Kế toán & Hóa đơn, Kho vận, Nhân sự, Đào tạo LMS, Dự án, Lịch hẹn...) chỉ với 1 cú click.
- **Bảo toàn dữ liệu 100%**: Không cần gỡ cài đặt module (`uninstall`), không làm mất chứng từ hay cấu hình đã có.
- **Dynamic Menu Visibility**: Menu tương ứng tự động ẩn/hiện ngay lập tức thông qua cơ chế tự động xóa cache hệ thống (`registry.clear_all_caches()`).
- **Direct Action & URL Guard**: Ngăn chặn người dùng truy cập trực tiếp qua URL hoặc Action vào các chứng từ thuộc tính năng đang bị tắt.
- **Giao diện Danh sách trực quan**: Quản lý gọn gàng với switch bật/tắt nhanh, mã kỹ thuật, phân hệ và mô tả nghiệp vụ.

### 2. 📋 Workflow & Sequential Multi-Level Approval (Quy Trình Phê Duyệt Đa Cấp)
- **Phê duyệt phân tầng theo hạn mức**: Hỗ trợ thiết lập quy trình duyệt nhiều cấp (Trưởng phòng $\rightarrow$ Kế toán trưởng $\rightarrow$ Ban Giám đốc) dựa trên giá trị đơn hàng.
- **Chủ động chọn quy trình (Hybrid Logic)**: Cho phép nhân viên chủ động lựa chọn Quy trình phê duyệt phù hợp ngay khi tạo Báo giá (`sale.order`), Đơn mua hàng (`purchase.order`) hoặc Hóa đơn nhà cung cấp (`account.move`).
- **Runtime Interceptor**: Tự động đánh chặn các hành động xác nhận đơn khi chưa qua đầy đủ các cấp phê duyệt hợp lệ.
- **Mass Approval Wizard**: Phê duyệt hàng loạt nhiều loại chứng từ hỗn hợp trong cùng một thao tác, yêu cầu nhập lý do bắt buộc khi từ chối.
- **Embedded Document Line Tabs**: Xem chi tiết sản phẩm, số lượng, đơn giá và thành tiền trực tiếp trên màn hình của cấp duyệt mà không cần chuyển trang.

### 3. 🎨 Dynamic Theme Engine & Live Theme Preview
- **Cá nhân hóa thương hiệu (White-labeling)**: Tùy chỉnh màu sắc chủ đạo (Primary Color), màu thanh điều hướng (Navbar Color), font chữ và logo công ty.
- **CSS Variables Injection**: Áp dụng thay đổi màu sắc ngay lập tức bằng CSS Variables mà không cần khởi động lại dịch vụ Odoo.
- **Live Theme Preview (OWL 3 Interactive Widget)**: Xem trước giao diện thực tế theo thời gian thực trước khi lưu cấu hình.
- **8 Theme Presets sẵn có**: Sẵn sàng triển khai nhanh các bộ giao diện chuẩn (Corporate Blue, Emerald Growth, Sunset Amber, Modern Dark, v.v.).

### 4. 📊 Hardware Telemetry & System Health Monitor
- **Biểu đồ sóng thời gian thực (Real-time Waveform Canvas)**: Đo lường CPU, RAM, Disk I/O và số lượng Database Connection theo thời gian thực (phong cách Windows Task Manager).
- **Health Dashboard**: Giám sát dung lượng ổ cứng, kích thước cơ sở dữ liệu, trạng thái sao lưu (Backup) và tình trạng Container Docker.

### 5. 👥 Visual Permission Matrix & Role Presets
- **Ma trận phân quyền trực quan**: Phân quyền chi tiết (Xem, Thêm, Sửa, Xóa, Xuất file) theo dạng lưới ma trận.
- **Thiết lập vai trò mẫu (Role Presets)**: Cung cấp sẵn các vai trò tiêu chuẩn (Sales Manager, Salesman, Accountant, HR Admin...) với phạm vi dữ liệu (`own`, `department`, `company`).

---

## 🛠️ Yêu Cầu Kỹ Thuật (Technical Requirements)

- **Odoo Version**: 19.0 Community / Enterprise
- **Python Version**: 3.10 trở lên
- **Dependencies**: `base`, `web`, `mail`
- **Tùy chọn tích hợp**: `sale_management`, `purchase`, `account`, `crm`, `stock`, `hr`, `project`, `lms`

---

## 📦 Cài Đặt & Cấu Hình (Installation)

### 1. Clone repository vào thư mục addons của bạn
```bash
cd /path/to/your/odoo/addons
git clone https://github.com/maitrinh044/odoo_erp_control_center.git sgt_erp_control_center
```

### 2. Cập nhật danh sách ứng dụng trong Odoo
- Khởi động Odoo và đăng nhập với quyền Quản trị viên (Admin).
- Kích hoạt **Developer Mode** (Chế độ nhà phát triển).
- Mở menu **Ứng dụng (Apps)** $\rightarrow$ Bấm **Cập nhật danh sách ứng dụng (Update Apps List)**.
- Tìm kiếm `SGT ERP Control Center` và bấm **Kích hoạt (Install)**.

### 3. Hoặc cập nhật qua dòng lệnh (CLI / Docker)
```bash
odoo -u sgt_erp_control_center -d <your_database_name> --stop-after-init
```

---

## 🧪 Chạy Kiểm Thử Tự Động (Automated Testing)

Module đi kèm bộ kiểm thử toàn diện với **97/97 tests pass 100%**:

```bash
odoo -d <database_name> --test-enable --stop-after-init -u sgt_erp_control_center --test-tags=sgt_erp_control_center
```

**Các nhóm kiểm thử chính:**
- `TestSgtErpControlCenter`: Kiểm thử Dashboard, Cấu hình tổng thể và White-labeling.
- `TestSgtErpFeatureAndPackage`: Kiểm thử bật/tắt tính năng, ẩn/hiện menu động và kiểm soát cache.
- `TestWorkflowRuntimeInterceptor`: Kiểm thử đánh chặn phê duyệt bán hàng, kiểm tra hạn mức và trường bắt buộc CRM.
- `TestPurchaseAccountApproval`: Kiểm thử phê duyệt đa cấp trên Mua hàng và Hóa đơn chi phí.
- `TestWorkflowSelection`: Kiểm thử nhân viên chủ động chọn quy trình trên đơn hàng.
- `TestDemoProductsAndSalesman`: Kiểm thử dữ liệu 50 sản phẩm mẫu và phân quyền Salesman.
- `TestMassApprovalAndDemoData`: Kiểm thử duyệt hàng loạt nhiều chứng từ.
- `TestHealthLiveStats`: Kiểm thử đọc số liệu phần cứng thời gian thực.

---

## 📂 Cấu Trúc Thư Mục (Folder Structure)

```text
sgt_erp_control_center/
├── __init__.py
├── __manifest__.py                  # Metadata & dependencies module
├── controllers/                     # API Webhook & Health check endpoints
├── data/                            # Dữ liệu mặc định (Features, Workflows, Themes, 50 Products)
├── i18n/                            # Tệp dịch đa ngôn ngữ (vi_VN)
├── models/                          # Database models & business logic
│   ├── erp_feature.py               # Quản lý tính năng & đồng bộ menu
│   ├── erp_feature_guard.py         # Bộ chặn truy cập trực tiếp URL
│   ├── erp_workflow.py              # Định nghĩa quy trình & cấp phê duyệt
│   ├── erp_purchase_workflow.py     # Tích hợp quy trình Mua hàng
│   ├── erp_account_workflow.py      # Tích hợp quy trình Kế toán / Hóa đơn
│   ├── erp_workflow_interceptor.py  # Đánh chặn phê duyệt Bán hàng & CRM
│   ├── erp_theme.py                 # Quản lý giao diện & CSS Variables
│   ├── erp_config.py                # Cấu hình thương hiệu & white-labeling
│   ├── erp_permission_matrix.py     # Ma trận phân quyền
│   └── ...
├── static/                          # CSS/SCSS, OWL JavaScript Widgets & XML Templates
├── tests/                           # Bộ kiểm thử tự động (Unit & Integration Tests)
├── views/                           # Giao diện XML (Forms, Lists, Kanbans, Menus)
└── wizard/                          # Các trình hướng dẫn (Setup Wizard, Approval Wizard)
```

---

## 📄 Bản Quyền (License)

Dự án được phát hành theo giấy phép [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html).  
© 2026 SGT ERP Team. All rights reserved.
