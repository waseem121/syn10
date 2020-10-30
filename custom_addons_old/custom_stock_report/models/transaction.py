# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import fields, models, api, _
from odoo.exceptions import Warning


# from odoo.addons import decimal_precision as dp


class InventoryTransaction(models.Model):
    _name = 'stock.inventory.transaction'

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search(
            [('scrap_location', '=', True), ('company_id', 'in', [self.env.user.company_id.id, False])], limit=1).id

    def _get_default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    name = fields.Char(string="Name")
    # move_ids = fields.One2many(
    #     'stock.move', 'inventory_id', string='Created Moves',
    #     states={'done': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('stock.inventory'))
    location_id = fields.Many2one(
        'stock.location', 'Location', domain="[('usage', '=', 'internal')]",
        required=True, default=_get_default_location_id)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        required=True, domain="[('scrap_location', '=', True)]")
    # reason = fields.Char(string="Reason", copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Validated'), ('cancel', 'Cancel')],
                             default='draft')
    transaction_line_ids = fields.One2many('stock.inventory.transaction.lines', 'transaction_id')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('stock.inventory.transaction')
        res = super(InventoryTransaction, self).create(vals)
        return res

    @api.multi
    def action_validate(self):
        if self.product_qty == 0:
            raise Warning(_("Quantity is Zero.....!!!!!!"))
        quants = self.env['stock.quant'].search(
            [('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id)])
        if quants:
            val = sum([x.qty for x in quants])
            # if self.product_qty <= val:
            #     source_picking_type = self.env['stock.picking.type'].search(
            #         [('default_location_src_id', '=', self.location_id.id), ('code', '=', 'internal')], limit=1)
            #     picking_order = self.env['stock.picking'].sudo().create({
            #         'picking_type_id': source_picking_type.id,
            #         'location_id': self.location_id.id,
            #         'location_dest_id': self.scrap_location_id.id,
            #         'move_type': 'direct',
            #         'move_lines': [(0, 0, {
            #             'name': self.product_id.name,
            #             'product_uom': self.product_id.uom_po_id.id,
            #             'product_id': self.product_id.id,
            #             'product_uom_qty': self.product_qty,
            #             'procure_method': 'make_to_stock',
            #             'location_id': self.location_id.id,
            #             'location_dest_id': self.scrap_location_id.id, })]
            #     })
            raise Warning(_("!!....all condition TRUE but module under construction please try after update...!!"))
            # self.state = 'confirm'
            # else:
        raise Warning(_("Not Enough Quantity....!!!!!!!!!"))

        # else:

        raise Warning(_("Product Not Available at This %s Location...!!!!") % self.location_id.name)

    # self.env['stock.move'].sudo().create({
    #     'name': self.product_id.name,
    #     'product_uom': self.product_id.uom_po_id.id,
    #     'product_id': self.product_id.id,
    #     'product_uom_qty': self.product_qty,
    #     'procure_method': 'make_to_stock',
    #     'location_id': self.location_id.id,
    #     'location_dest_id': self.scrap_location_id.id, })
    # self.picking_ids += picking_order
    # print "-------------------------------picking order ", picking_order, picking_order.name

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
        print "Click the Cancel button"

    @api.multi
    def action_reset_draft(self):
        self.state = 'draft'
        print "Click the Reset button"


class TransactionLines(models.Model):
    _name = 'stock.inventory.transaction.lines'
    _description = "Inventory Line"

    # inventory_id = fields.Many2one('stock.inventory', 'Inventory', index=True, ondelete='cascade')
    transaction_id = fields.Many2one(comodel_name='stock.inventory.transaction', string="Transaction")
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_id = fields.Many2one(
        'product.product', 'Product', index=True, required=True)
    product_name = fields.Char(
        'Product Name', related='product_id.name', store=True, readonly=True)
    product_code = fields.Char(
        'Product Code', related='product_id.default_code', store=True)
    product_uom_id = fields.Many2one(
        'product.uom', 'Product Unit of Measure', required=True,
        default=lambda self: self.env.ref('product.product_uom_unit', raise_if_not_found=True))
    product_qty = fields.Float(
        'Checked Quantity', default=0)
    # digits=dp.get_precision('Product Unit of Measure'), default=0)
    location_id = fields.Many2one(
        'stock.location', 'Location', index=True, required=True)
    # TDE FIXME: necessary ? only in order -> replace by location_id
    location_name = fields.Char(
        'Location Name', related='location_id.complete_name', store=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True)
    prod_lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id','=',product_id)]")
    # TDE FIXME: necessary ? -> replace by location_id
    prodlot_name = fields.Char(
        'Serial Number Name',
        related='prod_lot_id.name', store=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', 'Company', related='transaction_id.company_id',
        index=True, readonly=True, store=True)

    # TDE FIXME: necessary ? -> replace by location_id
    state = fields.Selection(
        'Status', related='transaction_id.state', readonly=True)
    theoretical_qty = fields.Float(
        'Theoretical Quantity', readonly=True, store=True)
    #         'Theoretical Quantity',, readonly=True, store=True)

    # inventory_location_id = fields.Many2one(
    # digits = dinvenrprecision('Product Unit of Measure') stock.location', ')
    # Location', related='transaction_id.location_id', related_sudo=False)

    @api.one
    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id')
    def _compute_theoretical_qty(self):
        if not self.product_id:
            self.theoretical_qty = 0
            return
        theoretical_qty = sum([x.qty for x in self._get_quants()])
        if self.product_uom_id and self.product_id.uom_id != self.product_uom_id:
            # theoretical_qty and
            theoretical_qty = self.product_id.uom_id._compute_quantity(theoretical_qty, self.product_uom_id)
        self.theoretical_qty = theoretical_qty

    # @api.onchange('product_id')
    # def onchange_product(self):
    #     res = {}
    #     # If no UoM or incorrect UoM put default one from product
    #     if self.product_id:
    #         self.product_uom_id = self.product_id.uom_id
    #         res['domain'] = {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
    #     return res
    #
    # @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    # def onchange_quantity_context(self):
    #     if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
    #         self._compute_theoretical_qty()
    #         self.product_qty = self.theoretical_qty
    #
    # @api.multi
    # def write(self, values):
    #     values.pop('product_name', False)
    #     res = super(TransactionLines, self).write(values)
    #     return res

    # @api.model
    # def create(self, values):
    #     values.pop('product_name', False)
    #     if 'product_id' in values and 'product_uom_id' not in values:
    #         values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
    #     existings = self.search([
    #         ('product_id', '=', values.get('product_id')),
    #         ('inventory_id.state', '=', 'confirm'),
    #         ('location_id', '=', values.get('location_id')),
    #         ('partner_id', '=', values.get('partner_id')),
    #         ('package_id', '=', values.get('package_id')),
    #         ('prod_lot_id', '=', values.get('prod_lot_id'))])
    #     res = super(TransactionLines, self).create(values)
    #     if existings:
    #         raise UserError(_("You cannot have two inventory adjustements in state 'in Progess' with the same product"
    #                           "(%s), same location(%s), same package, same owner and same lot. Please first validate"
    #                           "the first inventory adjustement with this product before creating another one.") %
    #                         (res.product_id.display_name, res.location_id.display_name))
    #     return res

    # def _get_quants(self):
    #     return self.env['stock.quant'].search([
    #         ('company_id', '=', self.company_id.id),
    #         ('location_id', '=', self.location_id.id),
    #         ('lot_id', '=', self.prod_lot_id.id),
    #         ('product_id', '=', self.product_id.id),
    #         ('owner_id', '=', self.partner_id.id),
    #         ('package_id', '=', self.package_id.id)])
    #
    # def _get_move_values(self, qty, location_id, location_dest_id):
    #     self.ensure_one()
    #     return {
    #         'name': _('INV:') + (self.inventory_id.name or ''),
    #         'product_id': self.product_id.id,
    #         'product_uom': self.product_uom_id.id,
    #         'product_uom_qty': qty,
    #         'date': self.inventory_id.date,
    #         'company_id': self.inventory_id.company_id.id,
    #         'inventory_id': self.inventory_id.id,
    #         'state': 'confirmed',
    #         'restrict_lot_id': self.prod_lot_id.id,
    #         'restrict_partner_id': self.partner_id.id,
    #         'location_id': location_id,
    #         'location_dest_id': location_dest_id,
    #     }
    #
    # def _fixup_negative_quants(self):
    #     """ This will handle the irreconciable quants created by a force availability followed by a
    #     return. When generating the moves of an inventory line, we look for quants of this line's
    #     product created to compensate a force availability. If there are some and if the quant
    #     which it is propagated from is still in the same location, we move it to the inventory
    #     adjustment location before getting it back. Getting the quantity from the inventory
    #     location will allow the negative quant to be compensated.
    #     """
    #     self.ensure_one()
    #     for quant in self._get_quants().filtered(lambda q: q.propagated_from_id.location_id.id == self.location_id.id):
    #         # send the quantity to the inventory adjustment location
    #         move_out_vals = self._get_move_values(quant.qty, self.location_id.id,
    #                                               self.product_id.property_stock_inventory.id)
    #         move_out = self.env['stock.move'].create(move_out_vals)
    #         self.env['stock.quant'].quants_reserve([(quant, quant.qty)], move_out)
    #         move_out.action_done()
    #
    #         # get back the quantity from the inventory adjustment location
    #         move_in_vals = self._get_move_values(quant.qty, self.product_id.property_stock_inventory.id,
    #                                              self.location_id.id)
    #         move_in = self.env['stock.move'].create(move_in_vals)
    #         move_in.action_done()
    #
