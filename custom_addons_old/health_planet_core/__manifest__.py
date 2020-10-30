# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Health Planet Core Customization',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 82,
    'summary': 'Manage customer requirement',
    'description': """
This module aims to fulfill Health Planet's business requirement.
==================================================

    * Customer Form modification

       """,
    'website': 'https://www.odoo.com/',
    'depends': [ 'health_planet', 'sales_team'],
    'data': [
	 'views/res_partner_view.xml',
             'views/template.xml'
    ],
    'demo': [],
    'qweb': ['static/src/xml/pos.xml'],
    'installable': True,
    'application': True,
}
