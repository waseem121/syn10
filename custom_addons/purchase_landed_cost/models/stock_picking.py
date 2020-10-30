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
            exchange_rate = 0.0
            if self.origin:
                purchases = self.env['purchase.order'].search([('name','=',self.origin)])
                if len(purchases):
                    if not purchases[0].has_default_currency:
                        exchange_rate = purchases[0].exchange_rate or 0.0
            cost_dist = cost_dist_obj.create({'exchange_rate':exchange_rate})
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
#        print"purchase_landed_cost get_price_unit: ",res
        return res
    
    @api.multi
    def action_done(self):
        print"purchase laneded  action done called"
        res = super(StockMove, self).action_done()
        add_expense=True
        expense_lines=[]
        for move in self:
            if not move.picking_id:
                continue
            # if move coming from Customer returns picking's scraps
            if move.location_dest_id.usage == 'inventory':
                continue
            if add_expense:
                expense_lines = move._get_expenses(move.product_qty)
                add_expense=False
                
                AccountMove = self.env['account.move']
                new_account_move = self.env['account.move']
                name = False
                if move.inventory_id:
                    name = move.inventory_id.name
                else:
                    name = move.picking_id.name
                AccountMove = AccountMove.search([('ref', '=', name)])
#                purchsaelandedcost
#                if not AccountMove:
#        
#                    date = self._context.get('force_period_date', fields.Date.context_today(self))
#                    AccountMove = AccountMove.create({
#                        'journal_id': journal_id,
#                        'line_ids': move_lines,
#        #                'date': date,
#                        'date': move.picking_id and move.picking_id.min_date or date,
#                        'ref': name})
                if AccountMove:
                    AccountMove.button_cancel()

                    total_expense = 0.0
                    for expense_line in expense_lines:
                        expense_line['move_id'] = AccountMove.id
                        total_expense += expense_line.get('credit',0.0)
                        line_id = self.env['account.move.line'].with_context({'check_move_validity':False}).create(expense_line)

                    print"total_expense: ",total_expense
                    credit_line_ids = AccountMove.line_ids.filtered(lambda l:l.credit)
                    credit = sum(credit_line_ids.mapped('credit'))
                    print"Credit: ",credit
                    
                    
                    debit_line_ids = AccountMove.line_ids.filtered(lambda l:l.debit)
                    debit = sum(debit_line_ids.mapped('debit')) + total_expense
                    debit_line_ids.with_context(
                            {'check_move_validity':False}).write({'credit':0,
                                                                'debit':debit,
                                                                })
                    print"Debit: ",debit
#                    ee
                    if round(credit,10) != round(debit,10):
                        cost_sales_account = self.env['account.account'].search([('name','=','Cost of Sales')])
                        cost_sales_account_id = cost_sales_account[0].id
                        diff_amount = debit - credit
                        print"diff_amount: ",diff_amount
                        
                        price_diff_line = {
                            'name': 'PriceDifference',
                            'product_id': False,
                            'quantity': 0.0,
                            'product_uom_id': False,
                            'ref': name,
                            'partner_id': move.picking_id.partner_id.id if move.picking_id.partner_id else False,
                            'account_id': cost_sales_account_id,
                            'move_id': AccountMove.id,
                            'credit': diff_amount > 0 and diff_amount or 0,
                            'debit': diff_amount < 0 and -diff_amount or 0,
                        }                        
                        line_id = self.env['account.move.line'].with_context({'check_move_validity':False}).create(price_diff_line)
                        print"diff line created"

                    AccountMove.post()
                    
                                             
                  # not needed                              
#                    lines = self.env['purchase.cost.distribution.line'].search(
#                        [('picking_id', '=', move.picking_id.id)])
#                    if len(lines):
#                        distribution = lines[0].distribution
#                        difference_amount = distribution.difference_amount
#                        print"difference_amount: ",difference_amount
#                        if difference_amount != 0.0:
#                            expense_account_ids = []
#                            for l in distribution.expense_lines:
#                                expense_account_ids.append(l.account_id.id)
#
#                            cost_sales_account = self.env['account.account'].search([('name','=','Cost of Sales')])
#                            cost_sales_account_id = cost_sales_account[0].id
#                            
#                            debit_line_ids = AccountMove.line_ids.filtered(lambda l:l.debit)
##                            debit = distribution.amount_total
#                            debit = distribution.calculated_amount_total
#                            debit_line_ids.with_context(
#                                    {'check_move_validity':False}).write({'credit':0,
#                                                                        'debit':debit,
#                                                                        })
##                            credit = debit - total_expense
#                            credit = distribution.total_purchase
#                            credit_line_ids = AccountMove.line_ids.filtered(lambda l:l.account_id.id not in expense_account_ids and l.credit)
#                            credit_line_ids.with_context(
#                                    {'check_move_validity':False}).write({'credit':credit,
#                                                                        'debit':0,
#                                                                        })
#                            price_diff_line = {
#                                'name': 'PriceDifference',
#                                'product_id': False,
#                                'quantity': 0.0,
#                                'product_uom_id': False,
#                                'ref': name,
#                                'partner_id': move.picking_id.partner_id.id if move.picking_id.partner_id else False,
#                                'account_id': cost_sales_account_id,
#                                'move_id': AccountMove.id,
#                            }
#                            if difference_amount > 0:# Debit cost of sales
#                                price_diff_line['credit'] = 0
#                                price_diff_line['debit'] = abs(difference_amount)
#
#                            if difference_amount < 0:# Credit cost of sales
#                                price_diff_line['credit'] = abs(difference_amount)
#                                price_diff_line['debit'] = 0
#                            print"difference_amount: ",difference_amount
#                            
#                            line_id = self.env['account.move.line'].with_context({
#                                    'check_move_validity':False}).create(price_diff_line)                            
#                            print"all entries created"
                    # not needed
                            
                            

#                    if AccountMove:
                    total_debit, total_credit = 0.0, 0.0
                    for line in AccountMove.line_ids:
                        total_credit += line.credit
                        total_debit += line.debit

                    print"total_credit: ",total_credit
                    print"total_debit: ",total_debit
                    if round(total_credit,3) != round(total_debit,3):
                        # for supplier returns of product in average costing method, in anglo saxon mode
                        diff_amount = total_debit - total_credit
                        price_diff_account = move.product_id.property_account_creditor_price_difference
                        if not price_diff_account:
                            price_diff_account = move.product_id.categ_id.property_account_creditor_price_difference_categ
                        if not price_diff_account:
                            raise UserError(_(
                                'Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
                        price_diff_line = {
                            'name': 'Price Difference adjustment',
                            'product_id': move.product_id.id,
                            'quantity': move.product_qty,
                            'product_uom_id': move.product_id.uom_id.id,
                            'ref': move.picking_id.name,
                            'partner_id': move.picking_id.partner_id.id if move.picking_id.partner_id else False,
                            'credit': diff_amount > 0 and diff_amount or 0,
                            'debit': diff_amount < 0 and -diff_amount or 0,
                            'account_id': price_diff_account.id,
                            'move_id': AccountMove.id,
                        }
                        line_id = self.env['account.move.line'].with_context({'check_move_validity':False}).create(price_diff_line)

                    AccountMove.post()

            # update products cost in line
            picking = move.picking_id or False
            if not picking:
                continue
            if picking.picking_type_id and picking.picking_type_id.code == 'incoming':
                inv_line = self.env['account.invoice.line']
                product = move.product_id
                self._cr.execute("""SELECT l.id FROM account_invoice i, account_invoice_line l 
                    WHERE i.id=l.invoice_id AND i.state='draft' AND 
                    l.product_id = %s """, 
                    (product.id,))
                query_res = self._cr.fetchall()
                if len(query_res):
                    line_ids = [x[0] for x in query_res]
                    if len(line_ids):
                        lines = inv_line.browse(line_ids)
                        for line in lines:
                            line.write({'cost_price':product.standard_price})

        return res
    
    def _get_expenses(self, qty):
        res= []
        
        if self.location_id.usage == 'supplier' and self.product_id.cost_method == 'average':
            pur_dist_line_id = self.env['purchase.cost.distribution.line'].search(
                [('picking_id', '=', self.picking_id.id),
                 ('move_id', '=', self.id),
                 ('product_id', '=', self.product_id.id),
                 ('distribution.state', '=', 'done')])
                 
            add_expense=True
            for each_picking_line in pur_dist_line_id:
                expense_amount_org = pur_dist_line_id.expense_amount
                print"expense_amount_org: ",expense_amount_org

                if add_expense:
                    for each_expense in each_picking_line.expense_lines.filtered(lambda l: l.expense_amount > 0.00):
                        print"each_expense: ",each_expense
                        expense_id = each_expense.distribution_expense or False
                        print"expense_id: ",expense_id
                        if expense_id:
                            expense_amount = expense_id.expense_amount_currency
                            print"expense_amount in : ",expense_amount

                        land_cost_vals = {
#                            'name': each_expense.type.name,
                            'name': expense_id.ref or each_expense.type.name,
                            'product_id': self.product_id.id,
                            'quantity': qty,
                            'product_uom_id': self.product_id.uom_id.id,
                            'ref': self.picking_id.name,
                            'partner_id': self.picking_id.partner_id.id if self.picking_id.partner_id else False,
                            'credit': float(expense_amount),
                            'debit': 0,
                            'account_id': expense_id.account_id.id,
                        }


                        # update foreign amount in journal entry start
                        picking = self.picking_id or False
                        if picking:
                            picking_currency_id = picking.company_id and picking.company_id.currency_id.id or False
                            expense_currency_id = expense_id.currency_id and expense_id.currency_id.id or False
                            
                            if (picking_currency_id and expense_currency_id):
                                if picking_currency_id != expense_currency_id:
                                    expense_amount = expense_id.expense_amount
                                    exchange_rate = each_picking_line.distribution and each_picking_line.distribution.exchange_rate or 0.0
                                    land_cost_vals['amount_currency'] = expense_amount * -1.0
                                    land_cost_vals['currency_id'] = expense_currency_id
                                    land_cost_vals['exchange_rate'] = exchange_rate
                        # update foreign amount in journal entry end

                        res.append((land_cost_vals))
                    add_expense=False
        
        return res
    
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            if self.product_id.cost_method == 'average':
                valuation_amount = cost if self.location_id.usage in ['supplier', 'production'] and self.location_dest_id.usage == 'internal' else self.product_id.standard_price
            else:
                valuation_amount = cost if self.product_id.cost_method == 'real' else self.product_id.standard_price
        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
#        debit_value = self.company_id.currency_id.round(valuation_amount * qty)
        debit_value = round((valuation_amount * qty),10)
        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value):
            if self.product_id.cost_method == 'standard':
                raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.product_id.name,))
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
        partner_id = (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False
        if self.location_id.usage == 'supplier' and self.product_id.cost_method == 'average':
            pur_dist_line_id = self.env['purchase.cost.distribution.line'].search(
                [('picking_id', '=', self.picking_id.id),
                 ('move_id', '=', self.id),
                 ('product_id', '=', self.product_id.id),
                 ('distribution.state', '=', 'done')])
            print"pur_dist_line_id: ",pur_dist_line_id
#            print"pur_dist_line_id unit Cost: ",pur_dist_line_id.standard_price_old
            if pur_dist_line_id:
                costing = pur_dist_line_id.standard_price_old * pur_dist_line_id.product_qty
#                print"costing: ",costing
                credit_value = costing
                debit_value = credit_value
        origin_credit_value =credit_value
        
        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'debit': debit_value if debit_value > 0 else 0,
            'credit': -debit_value if debit_value < 0 else 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
            'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference
            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
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
        return res