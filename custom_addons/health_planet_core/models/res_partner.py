# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    customer = fields.Boolean(string='Is a Customer', default=True,
                              help="Check this box if this contact is a Customer.")
                              	
