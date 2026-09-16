# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError

@tagged('post_install', '-at_install', 'sgt_erp_control_center')
class TestPurchaseAccountApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workflow = cls.env['sgt.erp.workflow']
        cls.Level = cls.env['sgt.erp.workflow.level']
        cls.PurchaseOrder = cls.env['purchase.order']
        cls.AccountMove = cls.env['account.move']

        group_user = cls.env.ref('base.group_user')
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        group_purchase_manager = cls.env.ref('purchase.group_purchase_manager')
        group_account_user = cls.env.ref('account.group_account_invoice')
        group_account_manager = cls.env.ref('account.group_account_manager')

        # Test users
        cls.user_purchaser = cls.env['res.users'].create({
            'name': 'Purchasing Staff',
            'login': 'purchaser_user',
            'email': 'purchaser@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_user.id, group_account_user.id])]
        })
        cls.user_lead = cls.env['res.users'].create({
            'name': 'Purchasing Team Lead',
            'login': 'purchase_lead',
            'email': 'purchase_lead@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_manager.id])]
        })
        cls.user_director = cls.env['res.users'].create({
            'name': 'Chief Financial Officer',
            'login': 'cfo_approver',
            'email': 'cfo@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_manager.id, group_account_manager.id])]
        })

        cls.vendor = cls.env['res.partner'].create({'name': 'SGT Standard Vendor'})
        cls.product = cls.env['product.product'].create({
            'name': 'ERP Industrial Supply',
            'list_price': 5000000.0,
            'standard_price': 5000000.0,
            'taxes_id': [(5, 0, 0)],
            'supplier_taxes_id': [(5, 0, 0)],
        })

        # 2-level Purchase Workflow
        cls.po_wf = cls.Workflow.create({
            'name': '2-Level Purchase Approval Workflow Test',
            'workflow_type': 'purchase',
            'require_approval': True,
            'approval_mode': 'sequential',
            'amount_threshold': 20000000.0, # >= 20M triggers approval
        })
        cls.po_lvl1 = cls.Level.create({
            'name': 'Level 1: Purchasing Team Lead',
            'workflow_id': cls.po_wf.id,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_lead.id])],
            'amount_min': 20000000.0,
        })
        cls.po_lvl2 = cls.Level.create({
            'name': 'Level 2: CFO',
            'workflow_id': cls.po_wf.id,
            'sequence': 20,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_director.id])],
            'amount_min': 50000000.0,
        })

        # 1-level Vendor Bill Workflow (Chief Accountant / CFO approval)
        cls.inv_wf = cls.Workflow.create({
            'name': 'Vendor Bill Approval Workflow Test',
            'workflow_type': 'account',
            'require_approval': True,
            'approval_mode': 'sequential',
            'amount_threshold': 30000000.0, # >= 30M
        })
        cls.inv_lvl1 = cls.Level.create({
            'name': 'Level 1: Director Payment Approval',
            'workflow_id': cls.inv_wf.id,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_director.id])],
            'amount_min': 30000000.0,
        })

    def test_01_purchase_order_under_threshold_direct_confirm(self):
        """Purchase order under threshold confirms directly."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1,
                'price_unit': 5000000.0,
                'tax_ids': [(5, 0, 0)],
            })]
        })
        self.assertEqual(po.amount_total, 5000000.0)
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        self.assertEqual(po.sgt_approval_state, 'not_required')

    def test_02_purchase_order_sequential_multi_level_approval(self):
        """Purchase order exceeding threshold sequentially flows 2 levels and auto-confirms."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.vendor.id,
            'sgt_approval_workflow_id': self.po_wf.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 12,
                'price_unit': 5000000.0,
                'tax_ids': [(5, 0, 0)],
            })]
        })
        self.assertEqual(po.amount_total, 60000000.0)

        # Purchaser clicks confirm -> switches to to_approve
        po.button_confirm()
        self.assertEqual(po.sgt_approval_state, 'to_approve')
        self.assertEqual(len(po.sgt_approval_line_ids), 2)

        # Clicking again while not yet approved -> blocked by UserError
        with self.assertRaises(UserError):
            po.button_confirm()

        line1 = po.sgt_approval_line_ids[0]
        line2 = po.sgt_approval_line_ids[1]
        self.assertEqual(line1.state, 'pending')
        self.assertEqual(line2.state, 'waiting')

        # Level 1 (Team Lead) approves
        line1.with_user(self.user_lead).action_approve(note="Approved purchase quantity")
        self.assertEqual(line1.state, 'approved')
        self.assertEqual(line2.state, 'pending')
        self.assertEqual(po.sgt_approval_state, 'to_approve')
        self.assertIn(po.state, ('draft', 'sent', 'to approve'))

        # Level 2 (CFO) approves -> automatically confirms purchase order
        line2.with_user(self.user_director).action_approve(note="Budget balanced, approved")
        self.assertEqual(line2.state, 'approved')
        self.assertEqual(po.sgt_approval_state, 'approved')
        self.assertEqual(po.state, 'purchase')

    def test_03_purchase_order_rejection(self):
        """Purchase order rejected at level 1 stops the whole workflow."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.vendor.id,
            'sgt_approval_workflow_id': self.po_wf.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 6,
                'price_unit': 5000000.0,
                'tax_ids': [(5, 0, 0)],
            })]
        })
        po.button_confirm()
        self.assertEqual(po.sgt_approval_state, 'to_approve')

        line1 = po.sgt_approval_line_ids[0]
        line1.with_user(self.user_lead).action_reject(note="Vendor price is too high")

        self.assertEqual(line1.state, 'rejected')
        self.assertEqual(po.sgt_approval_state, 'rejected')

    def test_04_account_move_vendor_bill_multi_level_approval(self):
        """Vendor bill exceeding threshold is blocked from posting until approved."""
        bill = self.AccountMove.with_user(self.user_purchaser).create({
            'move_type': 'in_invoice',
            'partner_id': self.vendor.id,
            'sgt_approval_workflow_id': self.inv_wf.id,
            'invoice_date': '2026-09-09',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 8,
                'price_unit': 5000000.0,
                'tax_ids': [(5, 0, 0)],
            })]
        })
        self.assertEqual(bill.amount_total, 40000000.0)

        # Click action_post() -> switches to to_approve
        bill.action_post()
        self.assertEqual(bill.sgt_approval_state, 'to_approve')
        self.assertEqual(len(bill.sgt_approval_line_ids), 1)

        # Clicking again when not approved -> blocked by UserError
        with self.assertRaises(UserError):
            bill.action_post()

        inv_line = bill.sgt_approval_line_ids[0]
        self.assertEqual(inv_line.state, 'pending')

        # CFO approves -> auto-post bill
        inv_line.with_user(self.user_director).action_approve(note="Valid invoice, approved to post")
        self.assertEqual(inv_line.state, 'approved')
        self.assertEqual(bill.sgt_approval_state, 'approved')
        self.assertEqual(bill.state, 'posted')

    def test_05_unauthorized_user_blocked_on_purchase_and_bill(self):
        """Unauthorized user attempting approval is blocked by AccessError."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.vendor.id,
            'sgt_approval_workflow_id': self.po_wf.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10,
                'price_unit': 5000000.0,
                'tax_ids': [(5, 0, 0)],
            })]
        })
        po.button_confirm()
        self.assertEqual(po.sgt_approval_state, 'to_approve')

        line1 = po.sgt_approval_line_ids[0]
        # Purchaser cannot self-approve level 1 of Team Lead
        with self.assertRaises(AccessError):
            line1.with_user(self.user_purchaser).action_approve()
