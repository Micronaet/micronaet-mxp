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

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order'
    
    def open_material_status_report(self, cr, uid, ids, context=None):
        ''' Open report for this products
        '''
        order_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        product_ids = []
        for line in order_proxy.order_line:
            if line.product_id.id not in product_ids:
                product_ids.append(line.product_id.id)
                
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'status_material_on_order_report',
            'datas': {
                #'object': 'sale.order',
                'product_ids': product_ids,            
                },
            } 
    
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
        # TODO parametrized:
        month_window = 6 # statistic m(x)
        month_order = 2 # not used for now (filter order)
        
        # ---------------------------------------------------------------------
        #                      Load extra data for report:
        # ---------------------------------------------------------------------

        # ---------------------------------------------
        # Minimum for product and default code database
        # ---------------------------------------------
        materials = {} # XXX Master dict for status!
        codes = {} 

        if required_product_ids:
            product_ids = required_product_ids
        else:    
            product_ids = product_pool.search(cr, uid, [], context=context)

        # -------
        # 2. BOM:
        # -------
        boms = {}        
        bom_ids = bom_pool.search(cr, uid, [
            ('bom_id', '=', False), # parent bom
            #('product_id', 'in', product_ids), # only requested product
            ], context=context)
        for bom in bom_pool.browse(cr, uid, bom_ids, context=context):        
            # Save all bom for OC explosion:
            product_id = bom.product_id.id
            boms[product_id] = bom

            # Initial setup for masterials:
            # Load only product_ids materials:
            if product_id not in product_ids:
                continue
            for line in bom.bom_lines:
                material = line.product_id
                if material.id not in materials:
                    # Used data for materials: 
                    materials[material.id] = [
                        material.accounting_qty, # status
                        0.0, # 1. OF
                        0.0, # 2. OC
                        0.0, # 3. mat used in period (to be populate)
                        material.min_stock_level,  # 4. min level
                        material, # 5. save for reach data in report
                        [], # 6. detail OF
                        ]
                    codes[material.default_code] = material.id    

        # ---------------------------------------------------------------------
        # Get material m(x) for production of selected product:
        # ---------------------------------------------------------------------
        from_date = (datetime.now() - timedelta(
            days=30 * month_window)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        lavoration_material_ids = lavoration_pool.search(cr, uid, [
            ('real_date_planned', '>=', from_date),
            ('product', 'in', product_ids), # filter for selected product
            ('state', 'in', ('draft', 'done', 'startworking')), # status check
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

        # ---------------------------------------------------------------------
        # (-) OC lines component in line:
        # ---------------------------------------------------------------------
        order_line_pool = self.pool.get('sale.order.line')
        
        # Only active from accounting
        line_ids = order_line_pool.search(cr, uid, [
            ('order_id.accounting_order', '=', True), # TODO remove
            # TODO add filter for date!!!
            ('order_id.state', 'not in', (
                'cancel', 
                #'draft', # TODO remove when operative
                #'sent'
                ), 
            )
             # filter only for select prod.
            ], context=context)
        for line in order_line_pool.browse(cr, uid, line_ids, context=context):
            #if line.product_id.not_in_status: # XXX jump line?
            #    continue 
                           
            # Direct sold:
            product_id = line.product_id.id            
            if product_id in materials:
                materials[product_id][
                    2] -= line.product_uom_qty
                continue
            
            # Component sold:
            if product_id not in boms:
                _logger.warning('Product without BOM: %s' % (
                    line.product_id.default_code))
                continue

            for material in boms[product_id].bom_lines:
                if material.product_id.id not in materials:
                    continue # jump component (not required)
                materials[material.product_id.id][ # first cell
                    2] -= line.product_uom_qty * material.product_qty

        # ---------------------------------------------------------------------
        # (+) OF lines data:
        # ---------------------------------------------------------------------
        cursor_of = query_pool.get_of_line_quantity_deadline(cr, uid)
        if not cursor_of: # no order status insert!
            _logger.error('Error access OF line table in accounting!')                
        else:
            for supplier_order in cursor_of: # all open OC
                code = supplier_order['CKY_ART'].strip()
                material_id = codes.get(code, False)
                if not material_id or material_id not in materials:
                    _logger.warning('Material code not found: %s!' % code)
                    continue 
                    
                qty = float(supplier_order['NQT_RIGA_O_PLOR'] or 0.0) * (
                    1.0 / supplier_order['NCF_CONV'] if supplier_order[
                        'NCF_CONV'] else 1.0)
                
                materials[material_id][1] += qty
                deadline = supplier_order['DTT_SCAD'].strftime(
                            DEFAULT_SERVER_DATE_FORMAT)
                materials[material_id][6].append(
                    _('%s / %s / %s (il %s) tot.: %s') % (
                        supplier_order['CSG_DOC'],
                        supplier_order['NGB_SR_DOC'],
                        supplier_order['NGL_DOC'],
                        '???' if deadline.startswith('1900') else deadline,
                        qty,     
                        ))                
        return materials        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
