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
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """    
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    #                                 Utility:
    # -------------------------------------------------------------------------
    def get_stock_status_depend_on_order(
            self, cr, uid, required_product_ids=None, context=None):
        ''' Procedure for calculate status of material depend on orders
            (supplier and customer)
            required_product_ids: selected product for get materials
        '''
        # Pool used:
        product_pool = self.pool.get('product.product')
        bom_pool = self.pool.get('mrp.bom')
        lavoration_pool = self.pool.get('mrp.production.workcenter.line')
        query_pool = self.pool.get('micronaet.accounting')
                
        # Parameters:
        month_window = 2 # parameters for m(x)
        
        # ---------------------------------------------------------------------
        #                      Load extra data for report:
        # ---------------------------------------------------------------------
        # 1. Minimum for product and default code database
        materials = {} # XXX Master dict for status!
        codes = {} 

        if required_product_ids:
            product_ids = required_product_ids
        else:    
            product_ids = product_pool.search(cr, uid, [], context=context)

        # 2. BOM:
        boms = {}        
        bom_ids = bom_pool.search(cr, uid, [
            ('bom_id', '=', False), # parent bom
            ('product_id', 'in', product_ids), # only requested product
            ], context=context)
        for bom in bom_pool.browse(cr, uid, bom_ids, context=context):        
            # Initial setup for masterials:
            for line in bom.bom_lines:
                product = line.product_id
                if product.id not in materials:
                    # Used data for materials: 
                    materials[product.id] = [
                        product.accounting_qty, # status
                        product.minimum_qty or 0.0,  # min level
                        product.default_code, # code
                        0.0, # tot used in period (next step will be populate)
                        ]
                    codes[product.default_code] = product.id    
            
            # Save bom for OC explosion:        
            boms[bom.product_id.id] = bom

        # 3. Get material m(x) for production of selected product:
        from_date = (datetime.now() - timedelta(
            days=30 * month_window)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        lavoration_material_ids = lavoration_pool.search(cr, uid, [
            ('real_date_planned', '>=', from_date),
            ('product', 'in', product_ids), # filter for selected product
            ('state', 'in', ('done', 'startworking')), # started or closed
            ], context=context)
        for lavoration in lavoration_pool.browse(
                cr, uid, lavoration_material_ids, context=context):
            for material in lavoration.bom_material_ids:
                material_id = material.product_id.id                
                if material_id in materials:
                    materials[material_id][3] += material.quantity or 0.0
                else:
                    pass # warning
        # TODO m(x) change UOM?

        # ----------------------------------------
        # 1. (+) component for order line product:
        # ----------------------------------------
        order_line_pool = self.pool.get('sale.order.line')
        
        # Only active from accounting
        line_ids = order_line_pool.search(cr, uid, [
            ('product_id', 'in', product_ids), # filter only for select prod.
            ], context=context)
        for line in order_line_pool.browse(cr, uid, line_ids):
            #if line.product_id.not_in_status: # XXX jump line?
            #    continue                
            product_id = line.product_id.id
            if product_id not in products:
                pass # XXX warning?
            
            if product_id not in boms:
                _logger.warning('Product without BOM: %s' % (
                    line.product_id.default_code))
                pass
                
            for component in boms[product_id].bom_lines:
                materials[component.product_id.id][ # first cell
                    0] -= line.product_uom_qty * component.product_qty

        # ---------------------
        # 2. (+) OF lines data:
        # ---------------------
        cursor_of = query_pool.get_of_line_quantity_deadline(cr, uid)
        if not cursor_of: # no order status insert!
            _logger.error('Error access OF line table in accounting!')                
        else:
            for supplier_order in cursor_of: # all open OC
                code = supplier_order['CKY_ART'].strip()
                material_id = codes.get(code, False)
                if not product_id:
                    _logger.error('Product code not found: %s!' % code)
                    pass 
                    
                # Check only selected product component:
                if material_id not in materials:
                    pass 
                    
                qty = float(supplier_order['NQT_RIGA_O_PLOR'] or 0.0) * (
                    1.0 / supplier_order['NCF_CONV'] if supplier_order[
                        'NCF_CONV'] else 1.0)
                if material_id not in materials:
                    _logger.warning('Product not present in DB? (%s)' % code)                    
                    pass                    
                materials[material_id][0] += qty
        return materials        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
