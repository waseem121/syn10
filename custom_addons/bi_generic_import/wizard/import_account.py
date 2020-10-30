# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo.exceptions import Warning
from odoo import models, fields, exceptions, api, _
from xlrd import open_workbook
import xlrd
import os
import tempfile
import binascii
from xlwt import Workbook
import xlwt

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
# for xls 
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class ImportAccount(models.TransientModel):
    _name = "import.account"

    file = fields.Binary('File')
    import_option = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')],string='Select',default='csv')
#    filename = fields.Char('Filename')

    @api.multi
    def import_csv(self):

        """Load Inventory data from the CSV file."""
        Account = self.env['account.account']
        Partner = self.env['res.partner']
        AccountType = self.env['account.account.type']
        if not self.file:
            raise exceptions.Warning(_("No file selected, Please upload a file!"))
        
        if self.import_option == 'csv': 
            """Load data from the CSV file."""
            
            keys=['code', 'name','type','account_type','parent_code','partner_code']
                    
            csv_data = base64.b64decode(self.file)
            data_file = cStringIO.StringIO(csv_data)
            data_file.seek(0)
            file_reader = []
            csv_reader = csv.reader(data_file, delimiter=',')
            try:
                file_reader.extend(csv_reader)
            except Exception:
                raise exceptions.Warning(_("Invalid file!"))
            
            all_vals, values = [], {}
            for i in range(len(file_reader)):
                if i==0:
                    continue
                try:
                     field= map(str, file_reader[i])
                except ValueError:
                     raise exceptions.Warning(_("Dont Use Charecter only use numbers"))
                
                values = dict(zip(keys, field))
                account_id = False
                account_ids = Account.search([('code','=',values['parent_code'])])
                if account_ids:
                    account_id = account_ids[0].id
                
                partner_id=False
                partner_ids = Partner.search([('ref','=',values['partner_code'])])
                if partner_ids:
                    partner_id = partner_ids[0].id
#                if not len(partner_ids):
#                    raise Warning(_("'%s' Partner not found!") %values['partner_code'])
                
                type_ids = AccountType.search([('name','=',values['type'])])
                if not len(type_ids):
                    raise Warning(_("'%s' Type not found!") %values['type'])
                print"type_ids: ",type_ids
                
                account_type = values['account_type']
                if account_type == 'View':account_type ='view'
                if account_type == 'Regular':account_type ='other'
                if account_type == 'Receivable':account_type ='receivable'
                if account_type == 'Payable':account_type ='payable'
                if account_type == 'Liquidity':account_type ='liquidity'
                if account_type == 'Consolidation':account_type ='consolidation'
                if account_type == 'Closed':account_type ='closed'
                reconcile=False
                if account_type in ('receivable','payable'):
                    reconcile = True
                all_vals.append({'code':values['code'],
                                    'name':values['name'],
                                    'reconcile':reconcile,
                                    'user_type_id':type_ids[0].id,
                                    'account_type':account_type,
                                    'parent':account_id,
                                    'partner':partner_id,
                                })

                
            # all product's validation done, now create the picking and its moves
            for v in all_vals:
                account = Account.create({'code': v['code'],
                            'name': v['name'],
                            'user_type_id': v['user_type_id'],
                            'type': v['account_type'],
                            'parent_id': v['parent'],
                            'reconcile': v['reconcile'],
                            'partner_id': v['partner']})
                print"account created::::: ",account
                
            res = {}
            return res
#        else:
#            fp = tempfile.NamedTemporaryFile(delete = False,suffix=".xlsx")
#            fp.write(binascii.a2b_base64(self.file))
#            fp.seek(0)
#            workbook = xlrd.open_workbook(fp.name)
#            sheet = workbook.sheet_by_index(0)
#            
#
#            
#            move_vals, values = [], {}
#            for row_no in range(sheet.nrows):
#                if row_no <= 0:
#                    fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
#                else:
##                    line = (map(lambda row:isinstance(row.value, unicode) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
##                    line = (map(lambda row:isinstance(row.value, unicode) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
#                    line = sheet.row_values(row_no)
#                    if line:
#                        if self.import_by == 'barcode':
#                            if len(line) == 2:
#                                raise Warning(_("Please provide UOM in file or choose different import by option"))
#                            values.update({'code':line[0],
#                                        'quantity':line[1],
#                                        'uom':line[2]})
#                        else:
#                            values.update({'code':line[0],
#                                        'quantity':line[1]})
#                        
#                        product, uom = self._get_product_and_uom(values)
#                        if product and uom:
#                            move_vals.append({'product':product,
#                                                'uom':uom,
#                                                'qty':values['quantity']
#                                            })
#                        else:
#                            raise Warning(_("'%s' Product Not Found!") %values['code'])
#                        
#            # all product's validation done, now create the picking and its moves
#            picking = Picking.create({'picking_type_id':self.picking_type_id.id,
#                        'move_type':'direct',
#                        'min_date':self.transfer_date,
#                        'location_id':self.location_id.id,
#                        'location_dest_id':self.location_dest_id.id})
#                        
#            for val in move_vals:
#                res = picking.write({
#                    'move_lines': [(0, 0, 
#                            {'product_id': val.get('product').id, 
#                                'name': val.get('product').name,
#                                'location_id' : self.location_id.id, 
#                                'location_dest_id' : self.location_dest_id.id, 
#                                'product_uom' : uom.id,
#                                'date' : self.transfer_date,
#                                'date_expected' : self.transfer_date,
#                                'product_uom_qty': val.get('qty')
#                                })]
#                            })
#                print"move line updated"
#                        
##            picking.action_confirm()
##            picking.force_assign()
#            res = {}
#            return res