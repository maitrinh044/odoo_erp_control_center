# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError, ValidationError

class TestWorkflowRuntimeInterceptor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workflow = cls.env['sgt.erp.workflow']
        cls.SaleOrder = cls.env['sale.order']
        cls.CrmLead = cls.env['crm.lead']
        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']
        cls.User = cls.env['res.users']
        cls.CrmStage = cls.env['crm.stage']

        # Clean existing sales workflow rules to avoid collision
        cls.Workflow.search([('workflow_type', 'in', ['sales', 'crm'])]).write({'active': False})

        # Test partner
        cls.customer = cls.Partner.create({
            'name': 'Công ty Khách Hàng Test',
            'email': 'customer@test.com',
        })

        # Test product
        cls.product = cls.Product.create({
            'name': 'Dịch vụ Tư vấn ERP Cao cấp',
            'type': 'service',
            'list_price': 1000000.0,
            'taxes_id': [(5, 0, 0)],
        })

        # Test users
        group_user = cls.env.ref('base.group_user')
        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')

        cls.sales_user = cls.User.create({
            'name': 'Nhân viên Kinh doanh Test',
            'login': 'sales_rep_test',
            'email': 'sales_rep@test.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_user.id])],
        })

        cls.approver_user = cls.User.create({
            'name': 'Giám đốc Kinh doanh Approver',
            'login': 'sales_approver_test',
            'email': 'sales_approver@test.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_manager.id])],
        })

        # Workflow rule for Sales: threshold 50,000,000 VND
        cls.sale_workflow = cls.Workflow.create({
            'name': 'Hạn mức bán hàng 50M',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 50000000.0,
            'approver_user_ids': [(6, 0, [cls.approver_user.id])],
            'company_id': cls.env.company.id,
            'active': True,
        })

    def test_01_order_under_threshold_direct_confirm(self):
        """Đơn hàng dưới hạn mức (10M < 50M) được xác nhận trực tiếp không bị chặn"""
        order = self.SaleOrder.with_user(self.sales_user).create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 10,
                    'price_unit': 1000000.0, # 10,000,000 VND
                })
            ]
        })
        self.assertEqual(order.amount_total, 10000000.0)
        self.assertEqual(order.sgt_approval_state, 'not_required')

        # Xác nhận đơn hàng
        order.action_confirm()
        self.assertEqual(order.state, 'sale', "Đơn hàng dưới hạn mức phải được xác nhận thành công")
        self.assertEqual(order.sgt_approval_state, 'not_required')

    def test_02_order_over_threshold_blocked_for_normal_user(self):
        """Đơn hàng vượt hạn mức (60M > 50M) chuyển sang to_approve và chặn xác nhận trực tiếp"""
        order = self.SaleOrder.with_user(self.sales_user).create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 60,
                    'price_unit': 1000000.0, # 60,000,000 VND
                })
            ]
        })
        self.assertEqual(order.amount_total, 60000000.0)

        # Lần bấm xác nhận đầu tiên bởi sales_user -> chuyển sang to_approve
        res = order.action_confirm()
        self.assertEqual(res.get('tag'), 'display_notification')
        self.assertEqual(order.sgt_approval_state, 'to_approve', "Trạng thái phê duyệt phải chuyển sang to_approve")
        self.assertNotEqual(order.state, 'sale', "Đơn hàng không được ở trạng thái sale khi chưa duyệt")
        self.assertEqual(order.sgt_approval_workflow_id, self.sale_workflow)

        # Cố tình bấm xác nhận lần thứ hai khi đang to_approve -> Phải raise UserError
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_03_unauthorized_user_cannot_approve(self):
        """Người dùng không có thẩm quyền không thể phê duyệt đơn hàng"""
        order = self.SaleOrder.create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 80,
                    'price_unit': 1000000.0,
                })
            ]
        })
        order.action_request_approval()
        self.assertEqual(order.sgt_approval_state, 'to_approve')

        # Thử duyệt bằng sales_user (không thuộc approver_user_ids)
        with self.assertRaises(AccessError):
            order.with_user(self.sales_user).action_approve_order()

    def test_04_authorized_approver_can_approve_and_confirm(self):
        """Người duyệt có thẩm quyền phê duyệt thành công và đơn chuyển sang xác nhận"""
        order = self.SaleOrder.create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 70,
                    'price_unit': 1000000.0,
                })
            ]
        })
        order.action_request_approval()
        self.assertEqual(order.sgt_approval_state, 'to_approve')

        # Duyệt bởi approver_user
        order.with_user(self.approver_user).action_approve_order()

        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.sgt_approver_id, self.approver_user)
        self.assertTrue(order.sgt_approval_date)
        self.assertEqual(order.state, 'sale', "Sau khi phê duyệt, đơn hàng phải được xác nhận thành công")

    def test_05_auto_approve_when_approver_confirms(self):
        """Nếu chính người duyệt bấm Xác nhận đơn hàng vượt hạn mức, hệ thống tự động phê duyệt ngay"""
        order = self.SaleOrder.with_user(self.approver_user).create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 90,
                    'price_unit': 1000000.0, # 90M
                })
            ]
        })
        # Bấm xác nhận trực tiếp bởi approver_user
        order.action_confirm()

        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.sgt_approver_id, self.approver_user)
        self.assertEqual(order.state, 'sale')

    def test_06_reject_order_flow(self):
        """Kiểm tra quy trình từ chối phê duyệt đơn hàng"""
        order = self.SaleOrder.create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 100,
                    'price_unit': 1000000.0,
                })
            ]
        })
        order.action_request_approval()

        # Từ chối duyệt bởi approver_user
        order.with_user(self.approver_user).action_reject_order()
        self.assertEqual(order.sgt_approval_state, 'rejected')
        self.assertEqual(order.state, 'draft')

    def test_07_crm_lead_required_fields_validation(self):
        """Kiểm tra CRM Lead chặn luân chuyển giai đoạn khi thiếu trường bắt buộc"""
        # Tạo workflow CRM
        crm_workflow = self.Workflow.create({
            'name': 'CRM Chuyển Giai Đoạn Bắt Buộc',
            'workflow_type': 'crm',
            'require_approval': True,
            'required_fields': 'phone,email_from,expected_revenue',
            'company_id': self.env.company.id,
            'active': True,
        })

        stage_1 = self.CrmStage.create({'name': 'Giai đoạn Khảo sát'})
        stage_2 = self.CrmStage.create({'name': 'Giai đoạn Đề xuất'})

        lead = self.CrmLead.create({
            'name': 'Cơ hội Dự án ERP Khách hàng ABC',
            'stage_id': stage_1.id,
            'email_from': 'contact@abc.vn',
            # Thiếu phone và expected_revenue
        })

        # Chuyển sang stage_2 mà chưa điền đủ -> Bắn ValidationError
        with self.assertRaises(ValidationError):
            lead.write({'stage_id': stage_2.id})

        # Bổ sung đầy đủ thông tin
        lead.write({
            'phone': '0901234567',
            'expected_revenue': 150000000.0,
        })

        # Giờ chuyển stage_2 thành công
        lead.write({'stage_id': stage_2.id})
        self.assertEqual(lead.stage_id, stage_2, "Sau khi điền đủ trường bắt buộc, lead chuyển giai đoạn thành công")
