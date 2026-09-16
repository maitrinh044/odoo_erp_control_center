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
            'name': 'Test Customer Company',
            'email': 'customer@test.com',
        })

        # Test product
        cls.product = cls.Product.create({
            'name': 'Premium ERP Consulting Service',
            'type': 'service',
            'list_price': 1000000.0,
            'taxes_id': [(5, 0, 0)],
        })

        # Test users
        group_user = cls.env.ref('base.group_user')
        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')

        cls.sales_user = cls.User.create({
            'name': 'Test Sales Staff',
            'login': 'sales_rep_test',
            'email': 'sales_rep@test.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_user.id])],
        })

        cls.approver_user = cls.User.create({
            'name': 'Sales Director Approver',
            'login': 'sales_approver_test',
            'email': 'sales_approver@test.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_manager.id])],
        })

        # Workflow rule for Sales: threshold 50,000,000 VND
        cls.sale_workflow = cls.Workflow.create({
            'name': 'Sales Approval Threshold 50M',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 50000000.0,
            'approver_user_ids': [(6, 0, [cls.approver_user.id])],
            'company_id': cls.env.company.id,
            'active': True,
        })

    def test_01_order_under_threshold_direct_confirm(self):
        """Order under threshold (10M < 50M) confirms directly without being blocked."""
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

        # Confirm order
        order.action_confirm()
        self.assertEqual(order.state, 'sale', "Order under threshold should be confirmed successfully")
        self.assertEqual(order.sgt_approval_state, 'not_required')

    def test_02_order_over_threshold_blocked_for_normal_user(self):
        """Order over threshold (60M > 50M) switches to to_approve and blocks direct confirmation."""
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

        # First confirm click by sales_user -> switches to to_approve
        res = order.action_confirm()
        self.assertEqual(res.get('tag'), 'display_notification')
        self.assertEqual(order.sgt_approval_state, 'to_approve', "Approval state must switch to to_approve")
        self.assertNotEqual(order.state, 'sale', "Order must not be in sale state without approval")
        self.assertEqual(order.sgt_approval_workflow_id, self.sale_workflow)

        # Intentionally clicking confirm a second time while to_approve -> Must raise UserError
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_03_unauthorized_user_cannot_approve(self):
        """Unauthorized user cannot approve sales order."""
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

        # Attempt approval by sales_user (not in approver_user_ids)
        with self.assertRaises(AccessError):
            order.with_user(self.sales_user).action_approve_order()

    def test_04_authorized_approver_can_approve_and_confirm(self):
        """Authorized approver successfully approves and order confirms."""
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

        # Approved by approver_user
        order.with_user(self.approver_user).action_approve_order()

        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.sgt_approver_id, self.approver_user)
        self.assertTrue(order.sgt_approval_date)
        self.assertEqual(order.state, 'sale', "After approval, order must be confirmed successfully")

    def test_05_auto_approve_when_approver_confirms(self):
        """If approver clicks confirm directly on an order over threshold, system auto-approves immediately."""
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
        # Direct confirm click by approver_user
        order.action_confirm()

        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.sgt_approver_id, self.approver_user)
        self.assertEqual(order.state, 'sale')

    def test_06_reject_order_flow(self):
        """Verify order rejection workflow."""
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

        # Reject by approver_user
        order.with_user(self.approver_user).action_reject_order()
        self.assertEqual(order.sgt_approval_state, 'rejected')
        self.assertEqual(order.state, 'draft')

    def test_07_crm_lead_required_fields_validation(self):
        """Verify CRM Lead stage change is blocked when required fields are missing."""
        # Create CRM workflow
        crm_workflow = self.Workflow.create({
            'name': 'CRM Mandatory Stage Change Fields',
            'workflow_type': 'crm',
            'require_approval': True,
            'required_fields': 'phone,email_from,expected_revenue',
            'company_id': self.env.company.id,
            'active': True,
        })

        stage_1 = self.CrmStage.create({'name': 'Survey Stage'})
        stage_2 = self.CrmStage.create({'name': 'Proposal Stage'})

        lead = self.CrmLead.create({
            'name': 'ERP Project Opportunity Customer ABC',
            'stage_id': stage_1.id,
            'email_from': 'contact@abc.vn',
            # Missing phone and expected_revenue
        })

        # Switch to stage_2 without required fields -> raises ValidationError
        with self.assertRaises(ValidationError):
            lead.write({'stage_id': stage_2.id})

        # Fill in required fields
        lead.write({
            'phone': '0901234567',
            'expected_revenue': 150000000.0,
        })

        # Now stage_2 change succeeds
        lead.write({'stage_id': stage_2.id})
        self.assertEqual(lead.stage_id, stage_2, "After filling required fields, lead moves to new stage successfully")
