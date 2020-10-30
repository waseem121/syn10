from odoo import api, fields, models
 
class website_config_setting(models.TransientModel):
    _inherit = 'website.config.settings'
    
    clarico_header_style_one = fields.Char('Clarico header style1',related='website_id.clarico_header_style_one')
    clarico_header_style_two = fields.Char("Clarico header style2",related='website_id.clarico_header_style_two')
    clarico_header_style_three = fields.Char("Clarico header style3",related='website_id.clarico_header_style_three')
