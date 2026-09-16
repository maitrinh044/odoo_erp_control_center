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
            'name': 'Test Purchaser User',
            'login': 'purchaser_selection_test',
            'email': 'purchaser_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_user.id, group_account_user.id])]
        })
        cls.user_salesman = cls.env['res.users'].create({
            'name': 'Test Salesman User',
            'login': 'salesman_selection_test',
            'email': 'salesman_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_sale_user.id])]
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Test Manager Approver',
            'login': 'manager_selection_test',
            'email': 'manager_sel@example.com',
            'group_ids': [(6, 0, [group_user.id, group_purchase_manager.id, group_sale_manager.id])]
        })

        cls.partner = cls.env['res.partner'].create({'name': 'SGT Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'SGT Test Product',
            'list_price': 10000000.0,
            'standard_price': 10000000.0,
            'taxes_id': [(5, 0, 0)],
            'supplier_taxes_id': [(5, 0, 0)],
        })

        # Create 2 Purchase workflows with same threshold
        cls.wf_po_furniture = cls.Workflow.create({
            'name': 'Office Furniture & Equipment Procurement',
            'workflow_type': 'purchase',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_po_facility = cls.Workflow.create({
            'name': 'Facility & Warehouse Lease Workflow',
            'workflow_type': 'purchase',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

        # Create 2 Sales workflows with same threshold
        cls.wf_so_standard = cls.Workflow.create({
            'name': 'Standard Sales Approval Workflow',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_so_discount = cls.Workflow.create({
            'name': 'Special Project Discount Workflow',
            'workflow_type': 'sales',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

        # Create 2 Invoicing workflows
        cls.wf_inv_regular = cls.Workflow.create({
            'name': 'Standard Vendor Bill Approval Workflow',
            'workflow_type': 'account',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })
        cls.wf_inv_capex = cls.Workflow.create({
            'name': 'CAPEX Fixed Asset Bill Approval Workflow',
            'workflow_type': 'account',
            'require_approval': True,
            'amount_threshold': 5000000.0,
            'approver_user_ids': [(6, 0, [cls.user_manager.id])]
        })

    def test_01_manual_workflow_selection_on_purchase_order(self):
        """Staff manually selects Furniture workflow -> system applies that exact workflow."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.partner.id,
            'sgt_approval_workflow_id': self.wf_po_furniture.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Chairs and Desks',
                'product_qty': 2,
                'price_unit': 10000000.0,
                'date_planned': '2026-09-09',
            })]
        })
        self.assertEqual(po.sgt_approval_workflow_id, self.wf_po_furniture)
        
        # Request approval
        po.action_request_approval()
        self.assertEqual(po.sgt_approval_state, 'to_approve')
        self.assertEqual(po.sgt_approval_workflow_id, self.wf_po_furniture)
        self.assertTrue(po.sgt_approval_line_ids)
        self.assertEqual(po.sgt_approval_line_ids[0].workflow_id, self.wf_po_furniture)

    def test_02_manual_workflow_selection_on_sale_order(self):
        """Sales rep manually selects Special Discount workflow -> system applies that exact workflow."""
        so = self.SaleOrder.with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'sgt_approval_workflow_id': self.wf_so_discount.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Solution Package',
                'product_uom_qty': 2,
                'price_unit': 10000000.0,
            })]
        })
        self.assertEqual(so.sgt_approval_workflow_id, self.wf_so_discount)

        # Confirm order (triggers approval)
        so.action_confirm()
        self.assertEqual(so.sgt_approval_state, 'to_approve')
        self.assertEqual(so.sgt_approval_workflow_id, self.wf_so_discount)
        self.assertTrue(so.sgt_approval_line_ids)
        self.assertEqual(so.sgt_approval_line_ids[0].workflow_id, self.wf_so_discount)

    def test_03_fallback_auto_workflow_when_unselected(self):
        """When workflow is empty -> system automatically falls back to matching threshold workflow."""
        po = self.PurchaseOrder.with_user(self.user_purchaser).create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': 'Backup Consumables',
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
        """Accountant manually selects CAPEX workflow -> system maps CAPEX workflow."""
        bill = self.AccountMove.with_user(self.user_purchaser).create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2026-09-09',
            'sgt_approval_workflow_id': self.wf_inv_capex.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'name': 'CAPEX Server Invoice',
                'quantity': 2,
                'price_unit': 10000000.0,
            })]
        })
        self.assertEqual(bill.sgt_approval_workflow_id, self.wf_inv_capex)

        # Post bill triggers approval
        bill.action_post()
        self.assertEqual(bill.sgt_approval_state, 'to_approve')
        self.assertEqual(bill.sgt_approval_workflow_id, self.wf_inv_capex)
        self.assertTrue(bill.sgt_approval_line_ids)
        self.assertEqual(bill.sgt_approval_line_ids[0].workflow_id, self.wf_inv_capex)
