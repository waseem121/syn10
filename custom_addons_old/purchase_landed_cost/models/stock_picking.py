# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from openerp import models, api, fields
from lxml import etree
from openerp.tools.translate import _
from openerp.osv import osv


# from mock.mock import self


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #     @api.multi
    #     def action_open_landed_cost(self):
    #         self.ensure_one()
    #         mod_obj = self.env['ir.model.data']
    #         model, action_id = tuple(
    #             mod_obj.get_object_reference(
    #                 'purchase_landed_cost',
    #                 'action_purchase_cost_distribution'))
    #         action = self.env[model].browse(action_id).read()[0]
    #
    #         line_obj = self.env['purchase.cost.distribution.line']
    #         lines = line_obj.search([('picking_id', '=', self.id)])
    #         if not lines:
    # #            if self.state == 'done':
    # #                raise osv.except_osv(_('Error!'),_("You cannot create landed cost after the product is received."))
    #             # ## Create new cost distribution
    #             cost_dist_obj = self.env['purchase.cost.distribution']
    #             cost_dist = cost_dist_obj.create({})
    #             move_list = []
    #             for move in self.move_lines:
    #                 for operation_id in self.pack_operation_product_ids:
    #                     if operation_id.product_id.id == move.product_id.id and operation_id.qty_done > 0:
    #                         move_list.append(move.id)
    #
    #             for move_id in list(set(move_list)):
    #                 self.env['purchase.cost.distribution.line'].create({
    #                     'distribution': cost_dist.id,
    #                     'move_id': move_id,
    #                 })
    #             ids = [cost_dist.id]
    #         else:
    #             ids = set([x.distribution.id for x in lines])
    #
    #         if len(ids) == 1:
    #             res = mod_obj.get_object_reference(
    #                 'purchase_landed_cost', 'purchase_cost_distribution_form')
    #             action['views'] = [(res and res[1] or False, 'form')]
    #             action['res_id'] = list(ids)[0]
    #         else:
    #             action['domain'] = "[('id', 'in', %s)]" % list(ids)
    #
    #         return action

    @api.multi
    def action_open_landed_cost(self):
        self.ensure_one()

        mod_obj = self.env['ir.model.data']
        model, action_id = tuple(
            mod_obj.get_object_reference(
                'purchase_landed_cost',
                'action_purchase_cost_distribution'))
        action = self.env[model].browse(action_id).read()[0]

        line_obj = self.env['purchase.cost.distribution.line']
        lines = line_obj.search([('picking_id', '=', self.id)])

        if not lines:
            #            if self.state == 'done':
            #                raise osv.except_osv(_('Error!'),_("You cannot create landed cost after the product is received."))
            ### Create new cost distribution
            cost_dist_obj = self.env['purchase.cost.distribution']
            cost_dist = cost_dist_obj.create({})
            print "cost_dist: ", cost_dist
            for move in self.move_lines:
                self.env['purchase.cost.distribution.line'].create({
                    'distribution': cost_dist.id,
                    'move_id': move.id,
                })
            ids = [cost_dist.id]
        else:
            ids = set([x.distribution.id for x in lines])

        if len(ids) == 1:
            res = mod_obj.get_object_reference(
                'purchase_landed_cost', 'purchase_cost_distribution_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = list(ids)[0]
        else:
            action['domain'] = "[('id', 'in', %s)]" % list(ids)

        return action

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context

        res = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                        submenu=submenu)
        if view_type == 'form':
            print "context: ", context
            print "view_id: ", view_id
            is_incoming = False
            picking_type_id = context.get('default_picking_type_id', False)
            if not picking_type_id:
                if context.get('active_id', False) and context.get('active_model', False) == 'purchase.order':
                    is_incoming = True
                elif context.get('active_id', False) and context.get('active_model', False) == 'stock.picking':
                    picking_type = self.env['stock.picking'].browse(context['active_id']).picking_type_id.code
                    is_incoming = True if picking_type == 'incoming' else False
            else:
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                is_incoming = True if picking_type.code == 'incoming' else False
            print "is_incoming: ", is_incoming
            doc = etree.XML(res['arch'])
            node_btn = doc.xpath("//button[@name='action_open_landed_cost']")

            if not is_incoming:
                parent = node_btn[0].find("..")
                parent.remove(node_btn[0])

            node_btn = doc.xpath("//button[@name='do_new_transfer']")
            for node in node_btn:
                #                if picking_type.code == 'incoming':
                if is_incoming:
                    node.set('confirm', _("Are you sure landed cost has been assigned?"))
            res['arch'] = etree.tostring(doc)
            #        print "res['arch']: ",res['arch']
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def get_price_unit(self):
        """ Returns the unit price to store on the quant """
        res = super(StockMove, self).get_price_unit()
        cost_line_id = self.env['purchase.cost.distribution.line'].search([('move_id', '=', self.id)])
        if cost_line_id:
            res = cost_line_id.standard_price_new
        return res

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()
        res = []
        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            if self.product_id.cost_method == 'average':
                valuation_amount = cost if self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'internal' else self.product_id.standard_price
            else:
                valuation_amount = cost if self.product_id.cost_method == 'real' else self.product_id.standard_price
        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount * qty)

        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value):
            if self.product_id.cost_method == 'standard':
                raise UserError(_(
                    "The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (
                                    self.product_id.name,))
            return []
        credit_value = debit_value

        if self.product_id.cost_method == 'average' and self.company_id.anglo_saxon_accounting:
            # in case of a supplier return in anglo saxon mode, for products in average costing method, the stock_input
            # account books the real purchase price, while the stock account books the average price. The difference is
            # booked in the dedicated price difference account.
            if self.location_dest_id.usage == 'supplier' and self.origin_returned_move_id and self.origin_returned_move_id.purchase_line_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
            # in case of a customer return in anglo saxon mode, for products in average costing method, the stock valuation
            # is made using the original average price to negate the delivery effect.
            if self.location_id.usage == 'customer' and self.origin_returned_move_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
                credit_value = debit_value
        partner_id = (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(
            self.picking_id.partner_id).id) or False

        origin_credit_value = credit_value
        expense_total = 0.00
        expense_amount = 0.00
        if self.location_id.usage == 'supplier' and self.product_id.cost_method == 'average':
            pur_dist_line_id = self.env['purchase.cost.distribution.line'].search(
                [('picking_id', '=', self.picking_id.id),
                 ('move_id', '=', self.id),
                 ('product_id', '=', self.product_id.id),
                 ('distribution.state', '=', 'done')])
            #             pur_dist_line_id = self.env['purchase.cost.distribution.line'].search([('picking_id', '=', self.picking_id.id),
            #                                                                                    ('product_id', '=', self.product_id.id),
            #                                                                                    ('distribution.state', '=', 'done')], limit=1)
            for each_picking_line in pur_dist_line_id:
                for each_expense in each_picking_line.expense_lines.filtered(lambda l: l.expense_amount > 0.00):
                    if each_expense.currency_id != each_picking_line.distribution.currency_id:
                        expense_amount = each_expense.currency_id.compute(each_expense.expense_amount,
                                                                          each_picking_line.distribution.currency_id,
                                                                          round=True)
                    else:
                        expense_amount = each_expense.expense_amount
                    expense_amount = round(expense_amount, self.company_id.currency_id.decimal_places)
                    land_cost_vals = {
                        'name': each_expense.type.name,
                        'product_id': self.product_id.id,
                        'quantity': qty,
                        'product_uom_id': self.product_id.uom_id.id,
                        'ref': self.picking_id.name,
                        'partner_id': self.picking_id.partner_id.id if self.picking_id.partner_id else False,
                        'credit': expense_amount,
                        'debit': 0,
                        'account_id': each_expense.distribution_expense.account_id.id,
                    }
                    res.append((0, 0, land_cost_vals))
                    expense_total += expense_amount

        credit_value -= expense_total
        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'debit': debit_value,
            'credit': 0,
            'account_id': debit_account_id,
        }

        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value,
            'debit': 0,
            'account_id': credit_account_id,
        }

        res += [(0, 0, credit_line_vals), (0, 0, debit_line_vals)]
        if origin_credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - origin_credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference
            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_(
                    'Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
            price_diff_line = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': self.picking_id.name,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
            res.append((0, 0, price_diff_line))
        # print "Res------------------", res
        print "\n self._context >>>>>>>>> ",self._context
        if self._context.get('from_scrap_adjustment',False):
            # for scrap adjustment flow from "Scrap Adjustments" menu
            res1 = []
            for each in res:
                # print "inside for >>>>>>>>>"
                value = list(each)
                if value[2]:
                    # print "\n value[2] >>>>>>>>. ", value[2]
                    value[2].update({'location_id': self.location_id.id})
                    if value[2].get('location_id'):
                        # print "\n get location >>>>>>>>>>", self.location_id
                        # print "\n location value[2].get('location_id') >>>>>>>>>>", value[2].get('location_id')
                        rec = self.env['account.analytic.default'].search(
                            [('location_id', 'in', [value[2].get('location_id'), self.location_dest_id.id]),
                             ('account_id', '=', value[2].get('account_id'))],
                            limit=1)
                        if rec:
                            # print "\n rec >>>>>>>>... ", rec
                            value[2].update({'analytic_account_id': rec.analytic_id.id})
                    res1.append(tuple(value))
                    res = res1
        return res
