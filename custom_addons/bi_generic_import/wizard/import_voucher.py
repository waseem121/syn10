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

class ImportVoucher(models.TransientModel):
    _name = "import.voucher"

    file = fields.Binary('File')
    import_option = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')],string='Select',default='csv')
#    filename = fields.Char('Filename')


    @api.multi
    def import_csv(self):

        """Load Inventory data from the CSV file."""
        Account = self.env['account.account']
        Journal = self.env['account.journal']
        Move = self.env['account.move']
        Currency = self.env['res.currency']
        MoveLine = self.env['account.move.line'].with_context({'check_move_validity':False})
        
        if not self.file:
            raise exceptions.Warning(_("No file selected, Please upload a file!"))
        
        if self.import_option == 'csv': 
            """Load data from the CSV file."""
            
            keys=['date', 'journal','number','account',
                    'debit','credit','label','comment','particulars',
                    'currency','exchange_rate']
                    
            csv_data = base64.b64decode(self.file)
            data_file = cStringIO.StringIO(csv_data)
            data_file.seek(0)
            file_reader = []
            csv_reader = csv.reader(data_file, delimiter=',')
            try:
                file_reader.extend(csv_reader)
            except Exception:
                raise exceptions.Warning(_("Invalid file!"))
            
            all_vals, all_numbers, all_journals, values = [], [], [], {}
            for i in range(len(file_reader)):
                if i==0:
                    continue
                try:
                     field= map(str, file_reader[i])
                except ValueError:
                     raise exceptions.Warning(_("Dont Use Charecter only use numbers"))
                
                values = dict(zip(keys, field))
                date = values['date'].split(" ")[0]
#                print"Date: ",date
#                if str(values['number']) != str(2):
#                    continue
                
                journal_ids = Journal.search([('name','=',values['journal'])])
                if not len(journal_ids):
                    raise Warning(_("'%s' Journal not found!") %values['journal'])
                
                account_ids = Account.search([('code','=',values['account'])])
                if not len(account_ids):
                    raise Warning(_("'%s' Account not found!") %values['account'])
                
                currency_id = False
                exchange_rate = 0.0
                currency = values['currency'] or ''
                if currency and currency != 'KWD':
                    exchange_rate = values['exchange_rate'] or 0.0
                    currency_ids = Currency.search([('name','=',values['currency'])])
                    if not len(currency_ids):
                        raise Warning(_("'%s' Currency not found!") %values['currency'])
                    if not exchange_rate:
                        raise Warning(_("'%s' needs exchange rates!") %values['currency'])
                    exchange_rate = float(values['exchange_rate']) or 0.0
                    currency_id = currency_ids[0].id
                    
                    exchange_rate = 1.0 / exchange_rate
                    print"exchange_rate: ",exchange_rate
                    print"values['debit']: ",values['debit']
                    print"values['credittt']: ",values['credit']
                    if values['debit'] and float(values['debit']) > 0:
#                        amount_currency = float(values['debit'])
#                        values['debit'] = float(values['debit']) * exchange_rate
                        amount_currency = float(values['debit']) * exchange_rate
                    if values['credit'] and float(values['credit']) > 0:
#                        amount_currency = float(values['credit']) * -1
#                        values['credit'] = float(values['credit']) * exchange_rate
                        amount_currency = (float(values['credit']) * exchange_rate) * -1
                    print"amount_currency: ",amount_currency
                        
                
                number = str(values['number'])
#                print"number: ",number
                
                vals = {'date':date,
                        'number':number,
                        'journal_id':journal_ids[0].id,
                        'account':account_ids[0],
                        'debit':values['debit'] or 0.0,
                        'credit':values['credit'] or 0.0,
                        'label':values['label'],
                        'comment':values['comment'],
                        'particulars':values['particulars'] or '',
#                                    'currency_id':currency_id,
#                                    'exchange_rate':exchange_rate,
#                                    'amount_currency':amount_currency,
                                }
                if currency and currency != 'KWD':
                    vals.update({'amount_currency':amount_currency,
                        'exchange_rate':exchange_rate,
                        'currency_id':currency_id,
                        })
                else:
                    vals.update({'currency_id':97})
                all_vals.append(vals)
                all_numbers.append(number)
                all_journals.append(journal_ids[0].id)
                
            all_numbers= list(set(all_numbers))
            all_journals= list(set(all_journals))
#            print"all numbers: ",all_numbers
            
            # validation for debit and credit amount
            for number in all_numbers:
                for journal_id in all_journals:
                    debit, credit = 0.0, 0.0
                    for v in all_vals:
                        if str(v['number']) == str(number) and v['journal_id'] == journal_id:
    #                        print"vvvv: ",v
                            debit += float(v['debit'])
                            credit += float(v['credit'])
                    if round(credit,3) != round(debit,3):
                        print"number: ",number
    #                    print"vv number: ",v['number']
                        print"debit: ",debit
                        print"credit: ",credit
                        journal = Journal.browse(journal_id)
                        raise Warning(_("'%s' Debit credit mismatch for Journal '%s'") %(number,journal.name),)
                    
            # creating the voucher
            for number in all_numbers:
                for journal_id in all_journals:
                    AccountMove = False
                    for v in all_vals:
    #                    if str(v['number']) != str(number):
    #                        continue
                        if str(v['number']) == str(number) and v['journal_id'] == journal_id:
                            if not AccountMove:
                                AccountMove = Move.create({'name':number,
                                        'date':v['date'],
                                        'journal_id':v['journal_id'],
                                        'narration':v['comment'],
                                        })
                                print"AccountMove: ",AccountMove

                            account = v['account']
                            line_vals = {
        #                        'ref': number,
                                'name': v['label'],
                                'partner_id': account.partner_id and account.partner_id.id or False,
                                'debit': float(v['debit']),
                                'credit': float(v['credit']),
                                'account_id': account.id,
                                'x_particulars': v['particulars'],
        #                        'currency_id': v['currency_id'],
        #                        'amount_currency': v['amount_currency'],
        #                        'exchange_rate': v['exchange_rate'],
                                'move_id': AccountMove.id,
                            }
                            if v['currency_id'] != 97:
                                line_vals.update({'amount_currency':v['amount_currency'],
                                    'exchange_rate':v['exchange_rate'],
                                    'currency_id':v['currency_id']})
                            MoveLine.create(line_vals)
                            print"move line created"
                    AccountMove.post()

            return True
