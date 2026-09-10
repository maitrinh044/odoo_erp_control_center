# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

@tagged('post_install', '-at_install', 'sgt_erp_control_center')
class TestWorkflowSelection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workflow = cls.env['sgt.erp.workflow']
        cls.Level = cls.env['sgt.erp.workflow.level']
        cls.PurchaseOrder = cls.env['purchase.order']
        cls.SaleOrder = cls.env['sale.order']
        cls.AccountMove = cls.env['account.move']

        group_user = cls.env.ref('base.group_user')
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        group_purchase_manager = cls.env.ref('purchase.group_purchase_manager')
        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')
        group_account_user = cls.env.ref('account.group_account_invoice')

        # Test users
        cls.user_purchaser = cls.env['res.users'].create({
            'name': 'Nhân Viên Mua Hàng Test',
            'login': 'purchaser_selection_test',
            'email': 'purchaser_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_user.id, group_account_user.id])]
        })
        cls.user_salesman = cls.env['res.users'].create({
            'name': 'Nhân Viên Bán Hàng Test',
            'login': 'salesman_selection_test',
            'email': 'salesman_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_user.id])]
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Trưởng Phòng Duyệt Test',
            'login': 'manager_selection_test',
            'email': 'manager_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_manager.id, group_sale_manager.id])]
        })

        cls.partner = cls.env['res.partner'].create({'name': 'Đối Tác Thử Nghiệm SGT'})
        cls.product = cls.env['product.product'].create({
            'name': 'Sản Phẩm Thử Nghiệm SGT',
            'list_price': 10000000.0,
            'standard_price': 10000000.0,
            'taxes_id': [(5, 0, 0)],
            'supplier_taxes_id': [(5, 0, 0)],
        })

        # Tạo 2 quy trình Mua hàng có cùng ngưỡng tiền
        cls.wf_po_furniture = cls.Workflow.create({
            'name': 'Quy trình mua sắm nội thất thiết bị văn phòng',
            'workflow_type': 'purchase',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_po_facility = cls.Workflow.create({
            'name': 'Quy trình thuê văn phòng kho bãi',
            'workflow_type': 'purchase',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

        # Tạo 2 quy trình Bán hàng có cùng ngưỡng tiền
        cls.wf_so_standard = cls.Workflow.create({
            'name': 'Quy trình bán hàng thông thường',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_so_discount = cls.Workflow.create({
            'name': 'Quy trình chiết khấu dự án đặc biệt',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

        # Tạo 2 quy trình Hóa đơn
        cls.wf_inv_regular = cls.Workflow.create({
            'name': 'Quy trình duyệt hóa đơn nhà cung cấp thường',
            'workflow_type': 'account',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_inv_capex = cls.Workflow.create({
            'name': 'Quy trình duyệt hóa đơn tài sản cố định CAPEX',
            'workflow_type': 'account',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

    def test_01_manual_workflow_selection_on_purchase_order(self):
        """Nhân viên chủ động chọn Quy trình mua sắm nội thất -> Hệ thống áp dụng đúng quy trình đó."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.partner.id,
            'sgt_approval_workflow_id': self.wf_po_furniture.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Ghế và Bàn làm việc',
                'product_qty': 2,
                'price_unit': 10000000.0,
                'date_planned': '2026-09-09',
            })]
        })
        self.assertEqual(po.sgt_approval_workflow_id, self.wf_po_furniture)
        
        # Gửi duyệt
        po.action_request_approval()
        self.assertEqual(po.sgt_approval_state, 'to_approve')
        self.assertEqual(po.sgt_approval_workflow_id, self.wf_po_furniture)
        self.assertTrue(po.sgt_approval_line_ids)
        self.assertEqual(po.sgt_approval_line_ids[0].workflow_id, self.wf_po_furniture)

    def test_02_manual_workflow_selection_on_sale_order(self):
        """Nhân viên kinh doanh chủ động chọn Quy trình chiết khấu đặc biệt -> Hệ thống áp dụng đúng quy trình đó."""
        so = self.SaleOrder.with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'sgt_approval_workflow_id': self.wf_so_discount.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Gói giải pháp',
                'product_uom_qty': 2,
                'price_unit': 10000000.0,
            })]
        })
        self.assertEqual(so.sgt_approval_workflow_id, self.wf_so_discount)

        # Xác nhận đơn hàng (kích hoạt duyệt)
        so.action_confirm()
        self.assertEqual(so.sgt_approval_state, 'to_approve')
        self.assertEqual(so.sgt_approval_workflow_id, self.wf_so_discount)
        self.assertTrue(so.sgt_approval_line_ids)
        self.assertEqual(so.sgt_approval_line_ids[0].workflow_id, self.wf_so_discount)

    def test_03_fallback_auto_workflow_when_unselected(self):
        """Khi để trống quy trình -> Hệ thống tự động fallback tìm quy trình phù hợp."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Vật tư dự phòng',
                'product_qty': 2,
                'price_unit': 10000000.0,
                'date_planned': '2026-09-09',
            })]
        })
        self.assertFalse(po.sgt_approval_workflow_id)

        # Confirm triggers approval
        po.button_confirm()
        self.assertEqual(po.sgt_approval_state, 'to_approve')
        self.assertTrue(po.sgt_approval_workflow_id)
        self.assertTrue(po.sgt_approval_workflow_id.require_approval)

    def test_04_manual_workflow_selection_on_vendor_bill(self):
        """Người tạo hóa đơn chủ động chọn Quy trình CAPEX -> Hệ thống map đúng quy trình CAPEX."""
        bill = self.AccountMove.with_user(self.user_purchaser).create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2026-09-09',
            'sgt_approval_workflow_id': self.wf_inv_capex.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Hóa đơn máy chủ CAPEX',
                'quantity': 2,
                'price_unit': 10000000.0,
            })]
        })
        self.assertEqual(bill.sgt_approval_workflow_id, self.wf_inv_capex)

        # Vào sổ kích hoạt duyệt
        bill.action_post()
        self.assertEqual(bill.sgt_approval_state, 'to_approve')
        self.assertEqual(bill.sgt_approval_workflow_id, self.wf_inv_capex)
        self.assertTrue(bill.sgt_approval_line_ids)
        self.assertEqual(bill.sgt_approval_line_ids[0].workflow_id, self.wf_inv_capex)
