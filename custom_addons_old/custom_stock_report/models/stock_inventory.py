from odoo import fields, models, api, _
from odoo.exceptions import Warning


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def get_lot_status(self):
        self.lot_setting = False
        if self.env['stock.config.settings'].search([], order='id desc', limit=1).group_stock_production_lot:
            self.lot_setting = True

    lot_setting = fields.Boolean(string="Lot Setting", compute="get_lot_status")
    line_ids_two = fields.One2many(comodel_name='stock.inventory.line', inverse_name='inventory_id')

    @api.model
    def default_get(self, fields):
        result = super(StockInventory, self).default_get(fields)
        result['lot_setting'] = True if self.env['stock.config.settings'].search([], order='id desc',
                                                                                 limit=1).group_stock_production_lot else False
        return result
