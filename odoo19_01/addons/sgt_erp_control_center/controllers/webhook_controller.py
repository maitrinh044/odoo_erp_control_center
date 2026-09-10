# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class SgtWebhookController(http.Controller):

    @http.route('/sgt_erp/webhook/ping', type='http', auth='public', methods=['GET'], csrf=False)
    def webhook_ping(self, **kw):
        """Simple health check endpoint for Webhook Receiver"""
        data = {
            'status': 'active',
            'service': 'SGT ERP Webhook Gateway',
            'server_time': fields.Datetime.to_string(fields.Datetime.now()),
        }
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/sgt_erp/webhook/<string:token>', type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def handle_webhook(self, token, **kw):
        """
        Public endpoint to receive external webhooks from third parties (Zalo OA, Facebook, CRM Webhooks, etc.)
        Token matches against sgt.erp.integration.client_id
        """
        Integration = request.env['sgt.erp.integration'].sudo()
        integration = Integration.search([
            ('client_id', '=', token),
            ('active', '=', True),
        ], limit=1)

        if not integration:
            # Fallback search by integration_type == 'webhook' and name
            integration = Integration.search([
                ('integration_type', '=', 'webhook'),
                ('name', '=', token),
                ('active', '=', True),
            ], limit=1)

        if not integration:
            _logger.warning("SGT ERP Webhook: Rejected payload for invalid or inactive token: %s", token)
            data = {
                'status': 'error',
                'error': 'invalid_token',
                'message': 'Webhook token not recognized or integration is inactive.'
            }
            return request.make_response(
                json.dumps(data),
                status=404,
                headers=[('Content-Type', 'application/json')]
            )

        # Record incoming event timestamp and verify connection
        integration.write({
            'last_check': fields.Datetime.now(),
            'status': 'connected',
            'last_error': False,
        })

        _logger.info("SGT ERP Webhook: Successfully processed event for integration '%s' (ID: %d)", integration.name, integration.id)

        response_data = {
            'status': 'success',
            'integration': integration.name,
            'integration_type': integration.integration_type,
            'received_at': fields.Datetime.to_string(fields.Datetime.now()),
        }
        return request.make_response(
            json.dumps(response_data),
            status=200,
            headers=[('Content-Type', 'application/json')]
        )
