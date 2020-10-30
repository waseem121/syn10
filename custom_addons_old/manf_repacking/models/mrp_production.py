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
from odoo.exceptions import Warning


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.multi
    def post_inventory(self):
        res = super(MrpProduction, self).post_inventory()
        if len(self.move_raw_ids) == 1:
            new_price = self.move_raw_ids.product_uom_qty * self.move_raw_ids.price_unit
            for each in self.move_finished_ids:
                product_tot_price = (each.product_id.qty_available - each.product_uom_qty) * each.product_id.standard_price
                each.price_unit = ((product_tot_price + new_price) / (each.product_id.qty_available))
                each.product_id.standard_price = each.price_unit
        return res

    @api.multi
    def action_assign(self):
        for production in self:
            move_to_assign = production.move_raw_ids.filtered(lambda x: x.state in ('confirmed', 'waiting', 'assigned'))
            products = []
            for each in move_to_assign:
                each.quantity_available = each.product_id.qty_available
                if each.product_id.qty_available < each.product_uom_qty:
                    products.append(str(each.product_id.product_tmpl_id.name))
            if len(products)> 0:
                message = "Raw material "
                for word in products:
                    message += str(word)+", "
                message += " not enough"
                raise Warning(message)
        res = super(MrpProduction, self).action_assign()
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('state', 'product_uom_qty', 'reserved_availability')
    def _qty_available(self):
        for move in self:
            # For consumables, state is available so availability = qty to do
            if move.state == 'assigned':
                move.quantity_available = move.product_uom_qty
                move.quantity_available = self.product_id.qty_available
            elif move.product_id.uom_id and move.product_uom:
                move.quantity_available = move.product_id.uom_id._compute_quantity(move.reserved_availability,
                                                                                   move.product_uom)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: