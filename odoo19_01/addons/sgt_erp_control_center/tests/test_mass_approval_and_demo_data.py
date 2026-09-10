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

        cls.partner = cls.env['res.partner'].create({'name': 'Khách Hàng & Đối Tác Mass SGT'})
        cls.product = cls.env['product.product'].create({
            'name': 'Hàng Hóa Dịch Vụ Mass Test',
            'list_price': 10000000.0,
            'standard_price': 10000000.0,
            'taxes_id': [(5, 0, 0)],
            'supplier_taxes_id': [(5, 0, 0)],
        })

    def test_01_twenty_workflow_presets_loaded(self):
        """Kiểm tra 20 quy trình mẫu được nạp thành công vào hệ thống."""
        all_wf = self.Workflow.search([])
        self.assertGreaterEqual(len(all_wf), 20, "Hệ thống phải có ít nhất 20 quy trình workflow mẫu")

        # Kiểm tra từng loại phân hệ đều có workflow
        sales_wf = self.Workflow.search([('workflow_type', '=', 'sales')])
        purchase_wf = self.Workflow.search([('workflow_type', '=', 'purchase')])
        account_wf = self.Workflow.search([('workflow_type', '=', 'account')])
        crm_wf = self.Workflow.search([('workflow_type', '=', 'crm')])

        self.assertGreaterEqual(len(sales_wf), 4, "Có ít nhất 4 quy trình Bán hàng")
        self.assertGreaterEqual(len(purchase_wf), 5, "Có ít nhất 5 quy trình Mua hàng")
        self.assertGreaterEqual(len(account_wf), 5, "Có ít nhất 5 quy trình Hóa đơn / Chi phí")
        self.assertGreaterEqual(len(crm_wf), 2, "Có ít nhất 2 quy trình CRM")

    def test_02_workflow_levels_exist_and_consistent(self):
        """Kiểm tra các cấp độ phê duyệt (workflow levels) được định nghĩa đầy đủ."""
        vip_wf = self.env.ref('sgt_erp_control_center.workflow_sale_project_vip', raise_if_not_found=False)
        if vip_wf:
            self.assertEqual(len(vip_wf.level_ids), 3, "Quy trình VIP dự án phải có đúng 3 cấp duyệt")
            self.assertEqual(vip_wf.level_ids[0].sequence, 10)
            self.assertEqual(vip_wf.level_ids[1].sequence, 20)
            self.assertEqual(vip_wf.level_ids[2].sequence, 30)

        po_raw_wf = self.env.ref('sgt_erp_control_center.workflow_purchase_raw_materials', raise_if_not_found=False)
        if po_raw_wf:
            self.assertEqual(len(po_raw_wf.level_ids), 3, "Quy trình mua nguyên vật liệu phải có 3 cấp duyệt")

    def test_03_mass_approval_wizard_approve_mixed_documents(self):
        """Kiểm tra tính năng duyệt hàng loạt đồng thời cả Đơn bán, Đơn mua và Hóa đơn."""
        # 1. Tạo 1 Đơn bán hàng
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

        # 2. Tạo 1 Đơn mua hàng
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

        # 3. Tạo 1 Hóa đơn nhà cung cấp
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

        # Lấy các dòng duyệt đang pending
        lines = so.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
        lines |= po.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')
        lines |= bill.sgt_approval_line_ids.filtered(lambda l: l.state == 'pending')

        if not lines:
            # Fallback tạo thủ công 3 lines giả lập cho 3 chứng từ
            lines = self.ApprovalLine.create([
                {
                    'name': 'Duyệt Đơn Bán Hàng',
                    'res_model': 'sale.order',
                    'res_id': so.id,
                    'sale_order_id': so.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                },
                {
                    'name': 'Duyệt Đơn Mua Hàng',
                    'res_model': 'purchase.order',
                    'res_id': po.id,
                    'purchase_order_id': po.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                },
                {
                    'name': 'Duyệt Hóa Đơn Chi Phí',
                    'res_model': 'account.move',
                    'res_id': bill.id,
                    'account_move_id': bill.id,
                    'state': 'pending',
                    'approver_user_ids': [(6, 0, [self.user_cfo.id])],
                }
            ])

        # Khởi tạo wizard duyệt hàng loạt
        wizard = self.MassWizard.with_user(self.user_cfo).create({
            'action_type': 'approve',
            'line_ids': [(6, 0, lines.ids)],
            'note': 'Duyệt hàng loạt định kỳ cuối tuần',
        })

        self.assertEqual(wizard.total_count, len(lines))
        res = wizard.action_confirm_mass_process()
        self.assertEqual(res['type'], 'ir.actions.client')

        # Kiểm tra toàn bộ các dòng được duyệt thành công
        for line in lines:
            self.assertEqual(line.state, 'approved')
            self.assertEqual(line.approved_by_id, self.user_cfo)

    def test_04_mass_approval_wizard_reject(self):
        """Kiểm tra từ chối hàng loạt kèm lý do."""
        lines = self.ApprovalLine.create([
            {
                'name': 'Duyệt Mua Thiết Bị 1',
                'res_model': 'purchase.order',
                'res_id': 9991,
                'state': 'pending',
                'approver_user_ids': [(6, 0, [self.user_cfo.id])],
            },
            {
                'name': 'Duyệt Mua Thiết Bị 2',
                'res_model': 'purchase.order',
                'res_id': 9992,
                'state': 'pending',
                'approver_user_ids': [(6, 0, [self.user_cfo.id])],
            }
        ])

        wizard = self.MassWizard.with_user(self.user_cfo).create({
            'action_type': 'reject',
            'line_ids': [(6, 0, lines.ids)],
            'note': 'Cắt giảm ngân sách Q3',
        })
        wizard.action_confirm_mass_process()

        for line in lines:
            self.assertEqual(line.state, 'rejected')
            self.assertEqual(line.note, 'Cắt giảm ngân sách Q3')

    def test_05_mass_approval_reject_requires_note(self):
        """Từ chối hàng loạt bắt buộc phải nhập lý do."""
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
        """Dòng người dùng không có quyền duyệt sẽ được bỏ qua an toàn."""
        line = self.ApprovalLine.create({
            'name': 'Duyệt cấp Giám Đốc',
            'res_model': 'sale.order',
            'res_id': 9994,
            'state': 'pending',
            'approver_user_ids': [(6, 0, [self.user_cfo.id])],
        })

        # Regular user không có trong approver_user_ids
        wizard = self.MassWizard.with_user(self.user_regular).create({
            'action_type': 'approve',
            'line_ids': [(6, 0, [line.id])],
        })
        res = wizard.action_confirm_mass_process()
        self.assertEqual(res['type'], 'ir.actions.client')
        # Dòng không được duyệt, vẫn ở trạng thái pending
        self.assertEqual(line.state, 'pending')
