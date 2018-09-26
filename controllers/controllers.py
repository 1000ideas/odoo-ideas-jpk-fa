# -*- coding: utf-8 -*-
from odoo import http

# class IdeasJpkFa(http.Controller):
#     @http.route('/ideas_jpk_fa/ideas_jpk_fa/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ideas_jpk_fa/ideas_jpk_fa/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ideas_jpk_fa.listing', {
#             'root': '/ideas_jpk_fa/ideas_jpk_fa',
#             'objects': http.request.env['ideas_jpk_fa.ideas_jpk_fa'].search([]),
#         })

#     @http.route('/ideas_jpk_fa/ideas_jpk_fa/objects/<model("ideas_jpk_fa.ideas_jpk_fa"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ideas_jpk_fa.object', {
#             'object': obj
#         })