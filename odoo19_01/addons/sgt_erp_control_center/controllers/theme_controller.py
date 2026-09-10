# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

class SgtThemeController(http.Controller):

    @http.route('/sgt_erp/active_theme', type='jsonrpc', auth='user')
    def get_active_theme(self):
        user = request.env.user
        theme = user.get_effective_theme()
        company = user.company_id
        config = request.env['sgt.erp.config'].sudo().search([('company_id', '=', company.id)], limit=1)

        css_variables = {}
        if theme:
            css_variables = theme.get_css_variables()

        data = {
            'theme_name': theme.name if theme else 'Default',
            'css_variables': css_variables,
            'browser_title': config.browser_title if config and config.browser_title else 'SGT ERP',
            'product_name': config.product_name if config and config.product_name else 'SGT ERP',
            'footer_text': config.footer_text if config and config.footer_text else '',
        }
        return data

    @http.route('/sgt_erp/login_logo', type='http', auth='public')
    def get_login_logo(self, **kw):
        company_id = request.params.get('company_id')
        if not company_id and hasattr(request.env, 'company') and request.env.company:
            company_id = request.env.company.id
        domain = [('company_id', '=', int(company_id))] if company_id else []
        config = request.env['sgt.erp.config'].sudo().search(domain, limit=1)
        if not config:
            config = request.env['sgt.erp.config'].sudo().search([], limit=1)
        if config and config.login_logo:
            image_data = base64.b64decode(config.login_logo)
            content_type = 'image/png'
            if image_data.startswith(b'\xff\xd8\xff'):
                content_type = 'image/jpeg'
            elif image_data.startswith(b'<svg') or b'<svg' in image_data[:100]:
                content_type = 'image/svg+xml'
            elif image_data.startswith(b'GIF8'):
                content_type = 'image/gif'
            elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:16]:
                content_type = 'image/webp'
            headers = [
                ('Content-Type', content_type),
                ('Content-Length', len(image_data)),
                ('Cache-Control', 'public, max-age=3600'),
            ]
            return request.make_response(image_data, headers)
        return request.redirect('/web/binary/company_logo')

    @http.route('/sgt_erp/login_background', type='http', auth='public')
    def get_login_background(self, **kw):
        company_id = request.params.get('company_id')
        if not company_id and hasattr(request.env, 'company') and request.env.company:
            company_id = request.env.company.id
        domain = [('company_id', '=', int(company_id))] if company_id else []
        config = request.env['sgt.erp.config'].sudo().search(domain, limit=1)
        if not config:
            config = request.env['sgt.erp.config'].sudo().search([], limit=1)
        if config and config.login_background:
            image_data = base64.b64decode(config.login_background)
            content_type = 'image/png'
            if image_data.startswith(b'\xff\xd8\xff'):
                content_type = 'image/jpeg'
            elif image_data.startswith(b'<svg') or b'<svg' in image_data[:100]:
                content_type = 'image/svg+xml'
            elif image_data.startswith(b'GIF8'):
                content_type = 'image/gif'
            elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:16]:
                content_type = 'image/webp'
            headers = [
                ('Content-Type', content_type),
                ('Content-Length', len(image_data)),
                ('Cache-Control', 'public, max-age=3600'),
            ]
            return request.make_response(image_data, headers)
        return request.not_found()

