# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from datetime import date
import datetime


class missing_receipt_voucher(models.TransientModel):
    _name = "missing.receipt.voucher"

    start = fields.Integer('Starting Ref')
    end = fields.Integer('Ending Ref')

    @api.multi
    def generate_missing_voucher_report(self):
        self.clear_caches()
        if self.end < self.start:
            raise Warning(_('Please enter proper Ref range.'))
        datas = {
            'model': self._name,
            'docids':self.id,
            'start':self.start,
            'end':self.end,
        }
        return self.env['report'].get_action(self, 'weekly_account_report.missing_receipt_voucher', data=datas)
    
    
class report_weekly_account_report_missing_receipt_voucher(models.AbstractModel):
    _name = 'report.weekly_account_report.missing_receipt_voucher'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('weekly_account_report.missing_receipt_voucher')
        print"report: ",report
        docids = self.env[data['model']].browse(data['docids'])
        print"docids: ",docids
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docids,
            'get_missing_vouchers':self.get_missing_vouchers,
        }
        return report_obj.render('weekly_account_report.missing_receipt_voucher', docargs)
    
    def get_missing_vouchers(self, obj):
        print"get_missing_vouchers called"

        res = []
        move_obj = self.env['account.move']
        journal_ids = self.env['account.journal'].search([('name','=','Receipt Voucher')])
        print"journal_ids: ",journal_ids
        
        move_ids = self.env['account.move'].search([('ref','>=',obj.start),
                    ('ref','<=',obj.end),
                    ('journal_id','=',journal_ids[0].id)])
        all_ref = []
        for m in move_ids:
            ref = m.ref or False
            if not ref: continue
            if (int(ref) >= obj.start) and (int(ref) <= obj.end):
                all_ref.append(int(ref))
        all_ref = sorted(all_ref)
        missing_nos = sorted(set(range(obj.start, obj.end + 1)).difference(all_ref))
        print"missing_nos: ",missing_nos
        for no in missing_nos:
            d = {}
            d['no'] = no
            res.append(d)
        
        return res