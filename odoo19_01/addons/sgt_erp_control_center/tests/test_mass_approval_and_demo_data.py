# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError

@tagged('post_install', '-at_install', 'sgt_erp_control_center')
class TestMassApprovalAndDemoData(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workflow = cls.env['sgt.erp.workflow']
        cls.Level = cls.env['sgt.erp.workflow.level']
        cls.ApprovalLine = cls.env['sgt.erp.approval.line']
        cls.MassWizard = cls.env['sgt.erp.mass.approval.wizard']
        cls.SaleOrder = cls.env['sale.order']
        cls.PurchaseOrder = cls.env['purchase.order']
        cls.AccountMove = cls.env['account.move']

        group_user = cls.env.ref('base.group_user')
        group_sale_manager = cls.env.ref('sales_team.group_sale_manager')
        group_purchase_manager = cls.env.ref('purchase.group_purchase_manager')
        group_account_manager = cls.env.ref('account.group_account_manager')

        # Admin / Executive Approver User having manager rights across all 3 modules
        cls.user_cfo = cls.env['res.users'].create({
            'name': 'CFO Mass Approver',
            'login': 'cfo_mass_user',
            'email': 'cfo_mass@example.com',
            'group_ids': [(6, 0, [
                group_user.id,
                group_sale_manager.id,
                group_purchase_manager.id,
                group_account_manager.id
            ])]
        })

        # Regular user without approval rights
        cls.user_regular = cls.env['res.users'].create({
            'name': 'Regular Staff User',
            'login': 'regular_staff_user',
            'email': 'regular@example.com',
            'group_ids': [(6, 0, [group_user.id])]
        })

        cls.partner = cls.env['res.partner'].create({'name': 'Mass SGT Customer & Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Mass Test Goods & Services',
            'list_price': 10000000.0,
            'standard_price': 10000000.0,
            'taxes_id': [(5, 0, 0)],
            'supplier_taxes_id': [(5, 0, 0)],
        })

    def test_01_twenty_workflow_presets_loaded(self):
        """Verify 20 workflow presets are loaded successfully into system."""
        all_wf = self.Workflow.search([])
        self.assertGreaterEqual(len(all_wf), 20, "System must have at least 20 workflow presets")

        # Check each workflow type has presets
        sales_wf = self.Workflow.search([('workflow_type', '=', 'sales')])
        purchase_wf = self.Workflow.search([('workflow_type', '=', 'purchase')])
        account_wf = self.Workflow.search([('workflow_type', '=', 'account')])
        crm_wf = self.Workflow.search([('workflow_type', '=', 'crm')])

        self.assertGreaterEqual(len(sales_wf), 4, "At least 4 Sales workflows")
        self.assertGreaterEqual(len(purchase_wf), 5, "At least 5 Purchase workflows")
        self.assertGreaterEqual(len(account_wf), 5, "At least 5 Invoice / Expense workflows")
        self.assertGreaterEqual(len(crm_wf), 2, "At least 2 CRM workflows")

    def test_02_workflow_levels_exist_and_consistent(self):
        """Verify workflow approval levels are defined consistently."""
        vip_wf = self.env.ref('sgt_erp_control_center.workflow_sale_project_vip', raise_if_not_found=False)
        if vip_wf:
            self.assertEqual(len(vip_wf.level_ids), 3, "VIP Project workflow must have 3 approval levels")
            self.assertEqual(vip_wf.level_ids[0].sequence, 10)
            self.assertEqual(vip_wf.level_ids[1].sequence, 20)
            self.assertEqual(vip_wf.level_ids[2].sequence, 30)

        po_raw_wf = self.env.ref('sgt_erp_control_center.workflow_purchase_raw_materials', raise_if_not_found=False)
        if po_raw_wf:
            self.assertEqual(len(po_raw_wf.level_ids), 3, "Raw materials purchase workflow must have 3 levels")

    def test_03_mass_approval_wizard_approve_mixed_documents(self):
        """Verify mass approval wizard approves mixed Sales Orders, Purchase Orders, and Invoices."""
        # 1. Create Sales Order
        so = self.SaleOrder.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 3,
                'price_unit': 10000000.0, # 30M
                'tax_ids': [(5, 0, 0)],
            })]
        })
        so.action_confirm()

        # 2. Create Purchase Order
        po = self.PurchaseOrder.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 4,
                'price_unit': 10000000.0, # 40M
                'tax_ids': [(5, 0, 0)],
            })]
        })
        po.button_confirm()

        # 3. Create Vendor Bill
        bill = self.AccountMove.create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2026-09-09',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
                'price_unit': 10000000.0, # 50M
                'tax_ids': [(5, 0, 0)],
            })]
        })
        bill.action_post()

        # Get pending approval lines
        lines = so.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
        lines |= po.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
        lines |= bill.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')

        if not lines:
            # Fallback create 3 mock lines for the 3 documents
            lines = self.ApprovalLine.create([
                {
                    'name': 'Approve Sales Order',
                    'res_model': 'sale.order',
                    'res_id': so.id,
                    'sale_order_id': so.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                },
                {
                    'name': 'Approve Purchase Order',
                    'res_model': 'purchase.order',
                    'res_id': po.id,
                    'purchase_order_id': po.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                },
                {
                    'name': 'Approve Expense Bill',
                    'res_model': 'account.move',
                    'res_id': bill.id,
                    'account_move_id': bill.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                }
            ])

        # Initialize mass approval wizard
        wizard = self.MassWizard.with_user(self.user_cfo).create({
            'action_type': 'approve',
            'line_ids': [(6, 0, lines.ids)],
            'note': 'Weekend scheduled mass approval',
        })

        self.assertEqual(wizard.total_count, len(lines))
        res = wizard.action_confirm_mass_process()
        self.assertEqual(res['type'], 'ir.actions.client')

        # Check all lines approved successfully
        for line in lines:
            self.assertEqual(line.state, 'approved')
            self.assertEqual(line.approved_by_id, self.user_cfo)

    def test_04_mass_approval_wizard_reject(self):
        """Verify mass rejection with note."""
        lines = self.ApprovalLine.create([
            {
                'name': 'Approve Equipment Purchase 1',
                'res_model': 'purchase.order',
                'res_id': 9991,
                'state': 'pending',
                'approver_user_ids': [(6, 0, [self.user_cfo.id])],
            },
            {
                'name': 'Approve Equipment Purchase 2',
                'res_model': 'purchase.order',
                'res_id': 9992,
                'state': 'pending',
                'approver_user_ids': [(6, 0, [self.user_cfo.id])],
            }
        ])

        wizard = self.MassWizard.with_user(self.user_cfo).create({
            'action_type': 'reject',
            'line_ids': [(6, 0, lines.ids)],
            'note': 'Q3 budget cut',
        })
        wizard.action_confirm_mass_process()

        for line in lines:
            self.assertEqual(line.state, 'rejected')
            self.assertEqual(line.note, 'Q3 budget cut')

    def test_05_mass_approval_reject_requires_note(self):
        """Mass rejection requires a note."""
        line = self.ApprovalLine.create({
            'name': 'Test Line',
            'res_model': 'sale.order',
            'res_id': 9993,
            'state': 'pending',
            'approver_user_ids': [(6, 0, [self.user_cfo.id])],
        })
        wizard = self.MassWizard.with_user(self.user_cfo).create({
            'action_type': 'reject',
            'line_ids': [(6, 0, [line.id])],
            'note': '',
        })
        with self.assertRaises(UserError):
            wizard.action_confirm_mass_process()

    def test_06_unauthorized_lines_skipped_safely(self):
        """Lines without authorization are safely skipped."""
        line = self.ApprovalLine.create({
            'name': 'Director Level Approval',
            'res_model': 'sale.order',
            'res_id': 9994,
            'state': 'pending',
            'approver_user_ids': [(6, 0, [self.user_cfo.id])],
        })

        # Regular user not in approver_user_ids
        wizard = self.MassWizard.with_user(self.user_regular).create({
            'action_type': 'approve',
            'line_ids': [(6, 0, [line.id])],
        })
        res = wizard.action_confirm_mass_process()
        self.assertEqual(res['type'], 'ir.actions.client')
        # Line not approved, remains pending
        self.assertEqual(line.state, 'pending')
