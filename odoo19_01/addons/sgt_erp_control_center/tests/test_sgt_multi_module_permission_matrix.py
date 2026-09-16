# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSgtMultiModulePermissionMatrix(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RolePreset = cls.env['sgt.erp.role.preset']
        cls.Matrix = cls.env['sgt.erp.permission.matrix']
        cls.Wizard = cls.env['sgt.erp.add.module.matrix.wizard']
        cls.IrModel = cls.env['ir.model']
        cls.IrModule = cls.env['ir.module.module']

        cls.model_sale_order = cls.IrModel.search([('model', '=', 'sale.order')], limit=1)
        cls.model_crm_lead = cls.IrModel.search([('model', '=', 'crm.lead')], limit=1)
        cls.model_res_partner = cls.IrModel.search([('model', '=', 'res.partner')], limit=1)

        cls.module_sale = cls.IrModule.search([('name', '=', 'sale')], limit=1)
        cls.module_crm = cls.IrModule.search([('name', '=', 'crm')], limit=1)

    def test_01_role_preset_can_have_multiple_modules(self):
        """Verify 1 Role Preset can be granted permissions for multiple modules simultaneously."""
        role = self.RolePreset.create({
            'name': 'Multi-Module Manager',
            'code': 'multi_mod_manager',
            'data_scope': 'team',
        })

        # Add permissions for Sales module
        line_sale = self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': self.model_sale_order.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
            'data_scope': 'team',
        })

        # Add permissions for CRM module
        line_crm = self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': self.model_crm_lead.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
            'data_scope': 'team',
        })

        # Add permissions for Contacts module
        line_partner = self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': self.model_res_partner.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': False,
            'perm_unlink': False,
            'data_scope': 'all',
        })

        # Verify Role Preset links 3 models from 3 different modules
        self.assertEqual(role.matrix_count, 3, "Role must have 3 permission lines in matrix")
        self.assertIn(line_sale, role.permission_matrix_ids)
        self.assertIn(line_crm, role.permission_matrix_ids)
        self.assertIn(line_partner, role.permission_matrix_ids)

        # Check module info computed automatically
        self.assertTrue(line_sale.module_shortdesc)
        self.assertTrue(line_crm.module_shortdesc)
        self.assertTrue(line_partner.module_shortdesc)

    def test_02_wizard_add_multi_module_models(self):
        """Verify Wizard quickly adds permissions for multiple modules simultaneously."""
        role = self.RolePreset.create({
            'name': 'Universal Director',
            'code': 'universal_director',
            'data_scope': 'all',
        })

        # Open wizard and select both modules: sale and crm
        wizard = self.Wizard.create({
            'role_preset_id': role.id,
            'module_ids': [(6, 0, [self.module_sale.id, self.module_crm.id])],
            'filter_mode': 'primary',
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
            'data_scope': 'all',
        })

        # Trigger preview
        wizard._onchange_module_and_settings()
        models_in_preview = wizard.line_ids.mapped('model_id.model')
        self.assertIn('sale.order', models_in_preview, "sale.order must be in preview")
        self.assertIn('crm.lead', models_in_preview, "crm.lead must be in preview")

        # Apply wizard
        res = wizard.action_add_to_matrix()
        self.assertEqual(res.get('params', {}).get('type'), 'success')

        # Verify lines created in Role
        created_models = role.permission_matrix_ids.mapped('model_id.model')
        self.assertIn('sale.order', created_models)
        self.assertIn('crm.lead', created_models)

    def test_03_record_rules_generated_for_all_matrix_models(self):
        """Verify Record Rules generated automatically for all models in Role matrix."""
        role = self.RolePreset.create({
            'name': 'Branch Officer',
            'code': 'branch_officer',
            'data_scope': 'team',
        })

        self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': self.model_sale_order.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
            'data_scope': 'team',
        })
        self.Matrix.create({
            'role_preset_id': role.id,
            'model_id': self.model_crm_lead.id,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': False,
            'data_scope': 'team',
        })

        role._sync_record_rules()
        self.assertTrue(role.security_group_id)

        rules = role.rule_ids
        rule_models = rules.mapped('model_id.model')
        self.assertIn('sale.order', rule_models, "Record Rule for sale.order must be generated")
        self.assertIn('crm.lead', rule_models, "Record Rule for crm.lead must be generated")
