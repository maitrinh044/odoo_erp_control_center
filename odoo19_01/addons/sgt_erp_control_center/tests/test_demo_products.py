# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install', 'sgt_erp_control_center')
class TestDemoProductsAndSalesman(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductTemplate = cls.env['product.template']
        cls.ProductProduct = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.RolePreset = cls.env['sgt.erp.role.preset']
        cls.ResUsers = cls.env['res.users']

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Products Customer',
            'email': 'customer_test_products@example.com',
        })

    def test_01_fifty_demo_products_loaded(self):
        """Verify that demo products are loaded into the database."""
        skus = [
            # IT (15)
            'IT-LAP-001', 'IT-LAP-002', 'IT-LAP-003', 'IT-PC-001', 'IT-MON-001',
            'IT-MON-002', 'IT-PRI-001', 'IT-PRI-002', 'IT-NET-001', 'IT-NET-002',
            'IT-SRV-001', 'IT-ACC-001', 'IT-ACC-002', 'IT-ACC-003', 'IT-PRJ-001',
            # Furniture (10)
            'FUR-DSK-001', 'FUR-CHR-001', 'FUR-CHR-002', 'FUR-TB-001', 'FUR-CAB-001',
            'FUR-BRD-001', 'FAC-WTR-001', 'FAC-AIR-001', 'FAC-SHR-001', 'FAC-LGT-001',
            # Stationery (10)
            'STA-PPR-001', 'STA-PPR-002', 'STA-PEN-001', 'STA-HLT-001', 'STA-FIL-001',
            'STA-NTB-001', 'STA-STP-001', 'STA-TAP-001', 'STA-INK-001', 'STA-INK-002',
            # Services (15)
            'SRV-ERP-001', 'SRV-MS365-001', 'SRV-GW-001', 'SRV-TRN-001', 'SRV-ITM-001',
            'SRV-CLD-001', 'SRV-NET-001', 'SRV-DSG-001', 'SRV-CNS-001', 'SRV-CA-001',
            'SRV-INV-001', 'SRV-SEC-001', 'SRV-BKP-001', 'SRV-TEL-001', 'SRV-MDA-001'
        ]
        self.assertEqual(len(skus), 50, "SKU list must contain 50 products.")
        
        found_products = self.ProductTemplate.search([('default_code', 'in', skus)])
        self.assertGreaterEqual(len(found_products), 50, "All 50 demo products must exist in the database.")

    def test_02_product_attributes_consistency(self):
        """Verify product attributes consistency (price, category, UoM)."""
        demo_products = self.ProductTemplate.search([
            ('default_code', '=like', 'IT-%'),
        ]) | self.ProductTemplate.search([
            ('default_code', '=like', 'FUR-%'),
        ]) | self.ProductTemplate.search([
            ('default_code', '=like', 'FAC-%'),
        ]) | self.ProductTemplate.search([
            ('default_code', '=like', 'STA-%'),
        ]) | self.ProductTemplate.search([
            ('default_code', '=like', 'SRV-%'),
        ])

        self.assertGreaterEqual(len(demo_products), 50)
        for p in demo_products:
            self.assertTrue(p.name, f"Product {p.default_code} must have a name.")
            self.assertGreater(p.list_price, 0, f"Product {p.default_code} must have list_price > 0.")
            self.assertGreater(p.standard_price, 0, f"Product {p.default_code} must have standard_price > 0.")
            self.assertTrue(p.categ_id, f"Product {p.default_code} must have a category.")
            self.assertTrue(p.uom_id, f"Product {p.default_code} must have a UoM.")
            self.assertTrue(p.sale_ok, f"Product {p.default_code} must have sale_ok enabled.")
            self.assertTrue(p.purchase_ok, f"Product {p.default_code} must have purchase_ok enabled.")

    def test_03_salesman_preset_has_sale_group(self):
        """Verify that Sales User role preset includes salesman group."""
        sales_preset = self.env.ref('sgt_erp_control_center.role_preset_sales_user')
        sale_group = self.env.ref('sales_team.group_sale_salesman')
        self.assertIn(sale_group, sales_preset.group_ids, "Role preset Sales User must contain standard Salesman group.")

    def test_04_salesman_can_create_order_with_demo_product(self):
        """Verify salesman can create a quotation with demo product."""
        sales_preset = self.env.ref('sgt_erp_control_center.role_preset_sales_user')
        sales_user = self.ResUsers.create({
            'name': 'Test Salesman Product User',
            'login': 'salesman_product_test',
            'email': 'salesman_prod@test.com',
            'role_preset_id': sales_preset.id,
        })
        sales_user.action_apply_role_preset()

        # Find demo laptop product
        lap = self.ProductProduct.search([('default_code', '=', 'IT-LAP-001')], limit=1)
        self.assertTrue(lap, "Product IT-LAP-001 must exist as product.product.")

        # Create sales order with sales_user
        order = self.SaleOrder.with_user(sales_user).create({
            'partner_id': self.partner.id,
            'user_id': sales_user.id,
            'order_line': [(0, 0, {
                'product_id': lap.id,
                'product_uom_qty': 2.0,
                'price_unit': lap.list_price,
            })]
        })
        self.assertTrue(order.exists(), "Salesman must be able to create Sales Order successfully.")
        self.assertEqual(order.amount_untaxed, 2 * 24500000.0)
