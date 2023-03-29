# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from decimal import Decimal

class AccountMoveExtension(models.Model):
    
    _inherit = 'account.move'
    
    dev_mercancia = fields.Boolean(string="Devolución de Mercancía")
    stock_pick = fields.Many2one(comodel_name="stock.picking", string="Albarán Asociado")
    confirm_move_type = fields.Boolean(compute='compute_confirmed_move_type')
    qty_uom = fields.Float(
        'Reserved', default=0.0, digits='Product Unit of Measure')
    
    @api.onchange('dev_mercancia')
    def empty_sp(self):
        if not self.dev_mercancia:
            self.stock_pick = ''
            
    #revisar
    @api.onchange('stock_pick')
    def determine_client(self):
        if self.stock_pick.partner_id.id != self.partner_id.id:
            self.partner_id = self.stock_pick.partner_id
    
    def action_post(self):
        for __record in self:
            if __record.move_type in ['out_refund']:
                account_move_lines = {}
                stock_move_lines = {}
                stock_move_lines_ratio = {}
                stock_move_lines_rounding = {}
                stock_move_lines_uom = {}
                
                
                
                for y in __record.stock_pick.move_line_ids:
                    stock_move_lines.update({y.product_id.id: y.qty_done})
                    stock_move_lines_uom.update({y.product_id.id: y.product_uom_id.id})

                    stock_move_lines_ratio.update({y.product_id.id: y.product_uom_id.ratio})
                    
                    numbepel = Decimal(str(y.product_uom_id.rounding)).as_tuple().exponent
                    numepel_clean = int(numbepel) * -1
                    stock_move_lines_rounding.update({y.product_id.id: numepel_clean})
                
                for x in __record.invoice_line_ids:
                    real_quantity = x.quantity * x.product_uom_id.ratio
                    quantity_test = round(real_quantity / stock_move_lines_ratio[x.product_id.id], stock_move_lines_rounding[x.product_id.id])
                    
                    if stock_move_lines_uom[x.product_id.id] == x.product_uom_id.id:
                        account_move_lines.update({x.product_id.id: x.quantity})
                    else:
                        account_move_lines.update({x.product_id.id: quantity_test})
    

                if account_move_lines == stock_move_lines:
                    self.env['stock.picking'].browse(__record.stock_pick.id).write({
                            'nota_cred': __record.name
                    }) 
                    return super(AccountMoveExtension, self).action_post()
                else:
                    raise UserError('La nota de crédito no coincide en los productos y/o en las cantidades con la devolución de inventario. Por favor verifique e intente nuevamente.')
            else:
                return super(AccountMoveExtension, self).action_post()
            
        
    
    
    def compute_confirmed_move_type(self):
            for move in self:
                move.confirm_move_type = move.move_type != 'out_refund'

      