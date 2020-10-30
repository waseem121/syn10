# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp

class product_template_inherited(models.Model):
	_inherit = "product.template"

	def _get_default_uom_id(self):
		return self.env["product.uom"].search([], limit=1, order='id').id
		
	uom_so_id  = fields.Many2one('product.uom','Sale Unit of Measure' ,default=_get_default_uom_id, required=True)


class Product_pricelist_items(models.Model):
	_inherit = "product.pricelist.item"

	uom_id = fields.Many2one('product.uom' , 'Pricelist UOM')

class Sale_Order_inherited(models.Model):
	_inherit = "sale.order"

	product_uom_ids = fields.Many2many('product.uom',string='Unit of Measuresss')

	@api.onchange('pricelist_id')
	def _get_items_details(self):
		product_uom_ids = []
		for line in self.pricelist_id.item_ids:
			product_uom_ids.append(line.uom_id.id)
		if product_uom_ids:
			self.product_uom_ids = product_uom_ids
			# values.append(line.uom_id.id)
		# return [('id','in',values)]

class Sale_Order_line_inherited(models.Model):
	_inherit = "sale.order.line"

	def _get_items_details(self):
		values=[]
		for line in self.order_id.pricelist_id.item_ids:
			values.append(line.uom_id.id)
		return [('id','in',values)]

	customer_id = fields.Many2one('res.partner',related="order_id.partner_id")
	# product_uom = fields.Many2one('product.uom', string='Unit of Measuresss', required=True , domain=lambda self: self._get_items_details())




	@api.multi
	@api.onchange('product_id')
	def product_id_change(self):
		if not self.product_id:
			return {'domain': {'product_uom': []}}

		vals = {}
		# values = []
		domain = {'product_uom': [('category_id', '=', self.product_id.uom_so_id.category_id.id)]}
		# if self.customer_id:
		# 	for line in self.customer_id.property_product_pricelist.item_ids:
		# 		values.append(line.uom_id.id)
		# # return [('id','in',values)]
		# domain = {'product_uom': [('id', 'in', values)]}

		if not self.product_uom or (self.product_id.uom_so_id.id != self.product_uom.id):
			vals['product_uom'] = self.product_id.uom_so_id
			vals['product_uom_qty'] = 1.0
		product = self.product_id.with_context(
			lang=self.order_id.partner_id.lang,
			partner=self.order_id.partner_id.id,
			quantity=vals.get('product_uom_qty') or self.product_uom_qty,
			date=self.order_id.date_order,
			pricelist=self.order_id.pricelist_id.id,
			uom=self.product_uom.id
		)
		result = {'domain': domain}
		title = False
		message = False
		warning = {}
		if product.sale_line_warn != 'no-message':
			title = _("Warning for %s") % product.name
			message = product.sale_line_warn_msg
			warning['title'] = title
			warning['message'] = message
			result = {'warning': warning}
			if product.sale_line_warn == 'block':
				self.product_id = False
				return result

		name = product.name_get()[0][1]
		if product.description_sale:
			name += '\n' + product.description_sale
		vals['name'] = name

		self._compute_tax_id()

		if self.order_id.pricelist_id and self.order_id.partner_id:
			vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
		self.update(vals)

		return result

	@api.multi
	def _get_display_price(self, product):
		# TO DO: move me in master/saas-16 on sale.order
		if self.order_id.pricelist_id.discount_policy == 'with_discount':
			for items in self.order_id.pricelist_id.item_ids:
				if self.product_uom.id == items.uom_id.id:
					return product.with_context(pricelist=self.order_id.pricelist_id.id).price

				# else:
				# 	return product.lst_price
				# 	break
		product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)
		final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
		base_price, currency_id = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.order_id.pricelist_id.id)
		if currency_id != self.order_id.pricelist_id.currency_id.id:
			base_price = self.env['res.currency'].browse(currency_id).with_context(product_context).compute(base_price, self.order_id.pricelist_id.currency_id)
		# negative discounts (= surcharge) are included in the display price
		print(base_price , "base_price" , final_price ,"final_price" , rule_id , " rule_id")
		return max(base_price, final_price)	
