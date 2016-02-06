# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID #, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class SaleOrderLine(orm.Model):
    """ Model name: SaleOrderLine
    """
    
    _inherit = 'sale.order.line'

    def create_splitted_order(self, cr, uid, ids, context=None):
        # get section
        line_proxy = self.browse(
            cr, uid, ids, context=context)[0]
        section = 0    
        for line in line_proxy.order_id.order_line:        
            res = line.split_order_id.section
            if type(res) == int and res > section:
                section = res
        section += 1
        
        item_id = self.pool.get('sale.order').create_order_from_line(
            cr, uid, line_proxy, section, context=context)
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Split order',
            'res_model': 'sale.order',
            'res_id': item_id,
            'view_type': 'form',
            'view_mode': 'form',
            #'view_id': view_id,
            #'target': 'new',
            #'nodestroy': True,
            #'context': {'active_ids': active_ids}
            }
            
    def open_splitted_order(self, cr, uid, ids, context=None):
        item_id = self.browse(
            cr, uid, ids, context=context)[0].split_order_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Master order',
            'res_model': 'sale.order',
            'res_id': item_id,
            'view_type': 'form',
            'view_mode': 'form',
            #'view_id': view_id,
            #'target': 'new',
            #'nodestroy': True,
            #'context': {'active_ids': active_ids}
            }
        
    _columns = {
        'split_order_id': fields.many2one('sale.order', 'Split order'),
        }
        
class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """
    _inherit = 'sale.order'

    # Button event:
    def go_master_order(self, cr, uid, ids, context=None):
        ''' Return to master cancel order
        '''
        item_id = self.browse(cr, uid, ids, context=context)[0].master_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Master order',
            'res_model': 'sale.order',
            'res_id': item_id,
            'view_type': 'form',
            'view_mode': 'form',
            #'view_id': view_id,
            #'target': 'new',
            #'nodestroy': True,
            #'context': {'active_ids': active_ids}
            }
        
    # --------
    # Utility:
    # --------
    def create_order_from_line(self, cr, uid, line_proxy, section, 
            context=None):
        ''' Utility function for create order from line
        '''
        # Pool used:
        line_pool = self.pool.get('sale.order.line')
        
        # Create new split order from line_
        parent_header = line_proxy.order_id
        order_id = self.create(cr, uid, {
            # Manage field:
            'is_splitted': True,     
            'master_id': parent_header.id,       
            'section': section,
            
            # Order field to copy:
            'name': '%s-%s' % (parent_header.name, section),
            'date_order': parent_header.date_order,
            'deadline_order': parent_header.deadline_order,
            #'date_valid': parent_header.date_valid, # mx_sale
            'validity': parent_header.validity,
            'client_order_ref': parent_header.client_order_ref,
            'note': parent_header.note,
            'transport': parent_header.transport,
            'package': parent_header.package,
            'delivery_note': parent_header.delivery_note,
            'incoterm': parent_header.incoterm.id,
            'user_id': parent_header.user_id.id,
            'section_id': parent_header.section_id.id,
            'fiscal_position': parent_header.fiscal_position.id,
            # categ_ids
            'payment_term': parent_header.payment_term.id,

            'partner_id': parent_header.partner_id.id,
            'pricelist_id': parent_header.pricelist_id.id,
            'address_id': parent_header.address_id.id,
            'invoice_id': parent_header.invoice_id.id,
            'carrier_id': parent_header.carrier_id.id,
            
            # Present?
            #'quotation_mode': parent_header.quotation_mode,
            
            }, context=context)
            # analysis_ids

        # ---------------
        # Duplicate line:
        # ---------------
        line_pool.create(cr, uid, {
            'order_id': order_id,
            'name': line_proxy.name,
            'product_id': line_proxy.product_id.id,
            'product_uom_qty': line_proxy.product_uom_qty,
            'product_uom': line_proxy.product_uom.id,
            'date_deadline': line_proxy.date_deadline,
            'price_unit': line_proxy.price_unit,
            'analysis_required': line_proxy.analysis_required,
            #'tax_id'            
            }, context=context)    
            
        # -------------------
        # Update parent line:    
        # -------------------
        line_pool.write(cr, uid, line_proxy.id, {
            'split_order_id': order_id
            }, context=context) 
            
        # -----------------
        # WF: Confirm order
        # -----------------
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'sale.order', order_id, 'order_confirm', cr)

        # TODO write is_master?
        # TODO cancel orer when last (here)!!!!    
        return order_id
        
    # ------------------------
    # Override confirm button:    
    # ------------------------
    def action_button_confirm(self, cr, uid, ids, context=None):
        ''' Not confirmed the order just cancel and create suborders
        '''
        section = 0
        lines = self.browse(cr, uid, ids, context=context)[0].order_line
        if len(lines) == 1:
            return super(SaleOrder, self).action_button_confirm(
                cr, uid, ids, context=context)
                          
        active_ids = []                        
        for line in lines:
            # -----------------------
            # Create order from line:
            # -----------------------
            section += 1
            active_ids.append(
                self.create_order_from_line(
                    cr, uid, line, section, context=context))
        
        self.write(cr, uid, ids, {
            'is_master': True,
            }, context=context)
        # Cancel order (now there's child confirmed)
        #wf_service = netsvc.LocalService('workflow')
        #wf_service.trg_validate(uid, 'sale.order', ids[0], 'cancel', cr)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Splitted order',
            'res_model': 'sale.order',
            'res_id': active_ids,
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'view_id': view_id,
            #'target': 'new',
            #'nodestroy': True,
            #'context': {'active_ids': active_ids}
            }

    
    _columns = {
        'section': fields.integer('Section'), 
        'master_id': fields.many2one('sale.order.line', 'Master'),
        'master_section': fields.integer('Section'), 
        'is_splitted': fields.boolean('Is splitted'),
        'is_master': fields.boolean('Is master'), # needed?
        
        'splitted_line_ids': fields.one2many('sale.order.line', 
            'split_order_id', 'Spiltted line'), 
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
