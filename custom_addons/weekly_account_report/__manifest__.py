{
    'name': 'Weekly Account Report',
    'version': '1.0',
    'category': 'Reporting',
    'website': 'wassim.sheikh@gmail.com',
    'description': "",
    'author': "Waseem Shaikh",
    'depends': ['base','sale','direct_sale'],
    'data': [
        'views/res_config_view.xml',
        'wizard/weekly_report_view.xml',
        'wizard/collection_report_view.xml',
        'wizard/missing_receipt_voucher_view.xml',
        'report/weekly_report_template.xml',
        'report/collection_report_template.xml',
        'report/missing_receipt_voucher.xml',
        'report/report.xml',
    ],
    'installable': True,
    'auto_install': False
}
