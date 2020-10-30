# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
##################################################################################

from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.onchange('product_qty','bom_line_ids')
    def onchange_product_qty(self):
        if (len(self.bom_line_ids) == 1):
            if self.product_tmpl_id.weight > 0.0:
                self.bom_line_ids.sudo().product_qty = float(self.product_tmpl_id.weight) * float(self.product_qty)
                # self.bom_line_ids.change_product_qty(
                #     float(float(self.product_tmpl_id.weight) * float(self.product_qty)))

                #       float(self.product_tmpl_id.weight) * float(self.product_qty))
                # self.sudo().bom_line_ids = [(4, 0, {'product_id': self.bom_line_ids.product_id.id,
                #                              'product_qty': float(self.product_tmpl_id.weight) * float(
                #                                  self.product_qty)})]
                # print("bom_line_ids",self.bom_line_ids)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.onchange('product_id')
    def change_product_qty(self):
        for each in self:
            if len(each.bom_id.bom_line_ids) == 1:
                each.product_qty = float(float(each.bom_id.product_tmpl_id.weight) * float(each.bom_id.product_qty))
