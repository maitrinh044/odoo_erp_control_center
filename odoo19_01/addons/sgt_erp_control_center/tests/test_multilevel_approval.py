# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, AccessError

class TestMultilevelApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Workflow = cls.env['sgt.erp.workflow']
        cls.Level = cls.env['sgt.erp.workflow.level']
        cls.Line = cls.env['sgt.erp.approval.line']
        cls.SaleOrder = cls.env['sale.order']

        # Deactivate existing sales workflows to avoid interference
        cls.Workflow.search([('workflow_type', '=', 'sales')]).write({'active': False})

        # Create test users
        group_user = cls.env.ref('base.group_user')
        cls.user_sales = cls.env['res.users'].create({
            'name': 'Sales Rep Multilevel',
            'login': 'sales_rep_ml',
            'email': 'sales_rep_ml@example.com',
            'group_ids': [(6, 0, [group_user.id, cls.env.ref('sales_team.group_sale_salesman').id])]
        })
        cls.user_lead = cls.env['res.users'].create({
            'name': 'Team Lead Approver',
            'login': 'team_lead_approver',
            'email': 'team_lead@example.com',
            'group_ids': [(6, 0, [group_user.id, cls.env.ref('sales_team.group_sale_salesman').id])]
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Sales Manager Approver',
            'login': 'sales_mgr_approver',
            'email': 'mgr@example.com',
            'group_ids': [(6, 0, [group_user.id, cls.env.ref('sales_team.group_sale_manager').id])]
        })
        cls.user_director = cls.env['res.users'].create({
            'name': 'Director Approver',
            'login': 'director_approver',
            'email': 'director@example.com',
            'group_ids': [(6, 0, [group_user.id, cls.env.ref('sales_team.group_sale_manager').id])]
        })

        cls.partner = cls.env['res.partner'].create({'name': 'VIP Multi-level Customer'})
        cls.product = cls.env['product.product'].create({
            'name': 'Premium ERP Product',
            'list_price': 10000000.0,
            'taxes_id': [(5, 0, 0)],
        })

        # Create 3-level workflow
        cls.wf = cls.Workflow.create({
            'name': '3-Level Sales Approval Workflow',
            'workflow_type': 'sales',
            'require_approval': True,
            'approval_mode': 'sequential',
            'amount_threshold': 20000000.0, # >= 20M triggers approval
        })

        cls.lvl1 = cls.Level.create({
            'name': 'Level 1: Team Lead',
            'workflow_id': cls.wf.id,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_lead.id])],
            'amount_min': 20000000.0,
        })
        cls.lvl2 = cls.Level.create({
            'name': 'Level 2: Manager',
            'workflow_id': cls.wf.id,
            'sequence': 20,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_manager.id])],
            'amount_min': 50000000.0,
        })
        cls.lvl3 = cls.Level.create({
            'name': 'Level 3: Director',
            'workflow_id': cls.wf.id,
            'sequence': 30,
            'approver_type': 'user',
            'approver_user_ids': [(6, 0, [cls.user_director.id])],
            'amount_min': 100000000.0,
        })

    def _create_order(self, qty=1):
        return self.SaleOrder.create({
            'partner_id': self.partner.id,
            'user_id': self.user_sales.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': qty,
                'price_unit': 10000000.0,
            })]
        })

    def test_01_multilevel_workflow_creation(self):
        """Test workflow configuration and approval levels"""
        self.assertEqual(self.wf.level_count, 3)
        self.assertEqual(self.wf.approval_mode, 'sequential')

        levels = self.wf.get_applicable_levels(120000000.0)
        self.assertEqual(len(levels), 3, "120M order must satisfy all 3 approval levels")

        levels_low = self.wf.get_applicable_levels(30000000.0)
        self.assertEqual(len(levels_low), 1, "30M order only satisfies Level 1")

    def test_02_sequential_approval_progression(self):
        """Test complete 3-level sequential approval progression"""
        order = self._create_order(qty=12) # 120M
        self.assertEqual(order.amount_total, 120000000.0)

        # Sales rep confirms order -> over threshold -> changes to to_approve
        order.with_user(self.user_sales).action_confirm()
        self.assertEqual(order.sgt_approval_state, 'to_approve')
        self.assertEqual(len(order.sgt_approval_line_ids), 3)

        # Test initial states
        line1 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 10)
        line2 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 20)
        line3 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 30)

        self.assertEqual(line1.state, 'pending')
        self.assertEqual(line2.state, 'waiting')
        self.assertEqual(line3.state, 'waiting')
        self.assertEqual(order.sgt_current_approval_line_id, line1)

        # Level 1 (Team Lead) approves
        line1.with_user(self.user_lead).action_approve(note="Approved Level 1")
        self.assertEqual(line1.state, 'approved')
        self.assertEqual(line2.state, 'pending')
        self.assertEqual(line3.state, 'waiting')
        self.assertEqual(order.sgt_approval_state, 'to_approve')
        self.assertEqual(order.sgt_current_approval_line_id, line2)

        # Level 2 (Manager) approves
        line2.with_user(self.user_manager).action_approve(note="Approved Level 2")
        self.assertEqual(line2.state, 'approved')
        self.assertEqual(line3.state, 'pending')
        self.assertEqual(order.sgt_current_approval_line_id, line3)

        # Level 3 (Director) approves -> Completed -> Auto confirms order!
        line3.with_user(self.user_director).action_approve(note="Approved by Director")
        self.assertEqual(line3.state, 'approved')
        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.state, 'sale', "Order must automatically transition to sale state after final approval")

    def test_03_rejection_at_intermediate_level(self):
        """Test rejection at intermediate level -> stops progression"""
        order = self._create_order(qty=12) # 120M
        order.with_user(self.user_sales).action_confirm()

        line1 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 10)
        line2 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 20)
        line3 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 30)

        # Level 1 approves OK
        line1.with_user(self.user_lead).action_approve()

        # Level 2 rejects
        line2.with_user(self.user_manager).action_reject(note="Discount does not comply with policy")
        self.assertEqual(line2.state, 'rejected')
        self.assertEqual(line3.state, 'skipped', "Subsequent levels must be skipped when previous level is rejected")
        self.assertEqual(order.sgt_approval_state, 'rejected')
        self.assertEqual(order.state, 'draft', "Rejected order must not be confirmed")

    def test_04_direct_mode_approval(self):
        """Test Direct Mode: Only highest level approves"""
        self.wf.approval_mode = 'direct'
        order = self._create_order(qty=12) # 120M
        order.with_user(self.user_sales).action_confirm()

        # In direct mode, only the highest level (Director) is generated
        self.assertEqual(len(order.sgt_approval_line_ids), 1)
        line = order.sgt_approval_line_ids[0]
        self.assertEqual(line.level_id, self.lvl3)
        self.assertEqual(line.state, 'pending')

        # Director approves -> immediately complete
        line.with_user(self.user_director).action_approve()
        self.assertEqual(order.sgt_approval_state, 'approved')
        self.assertEqual(order.state, 'sale')

        # Reset mode
        self.wf.approval_mode = 'sequential'

    def test_05_unauthorized_approver_blocked(self):
        """Test unauthorized approver is blocked with AccessError"""
        order = self._create_order(qty=12)
        order.with_user(self.user_sales).action_confirm()

        line1 = order.sgt_approval_line_ids.filtered(lambda l: l.sequence == 10)
        # Sales rep cannot approve Level 1
        with self.assertRaises(AccessError):
            line1.with_user(self.user_sales).action_approve()

        # Manager cannot approve Level 1 (assigned to Team Lead)
        with self.assertRaises(AccessError):
            line1.with_user(self.user_manager).action_approve()

    def test_06_approval_wizard(self):
        """Test interaction via approval wizard"""
        order = self._create_order(qty=12)
        order.with_user(self.user_sales).action_confirm()

        line1 = order.sgt_current_approval_line_id
        wizard = self.env['sgt.erp.approval.wizard'].with_user(self.user_lead).create({
            'line_id': line1.id,
            'action_type': 'approve',
            'note': 'Approved via UI wizard',
        })
        wizard.action_confirm()
        self.assertEqual(line1.state, 'approved')
        self.assertIn('Approved via UI wizard', line1.note)
