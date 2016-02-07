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
from openerp import SUPERUSER_ID#, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class mrp_production_unload(osv.osv):
    ''' Create object mrp.production.material seems the bom explosed on product
        quantity used as a model for bom list
        This object is use also for mrp.production.workcenter.line only for keep
        the list of fields instead of create another object
    '''
    _name = "mrp.production.unload"
    _description= "Production used material"
    _rec_name = "product_id"

    _columns = {
        'product_id':fields.many2one(
            'product.product', 'Product', required=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'quantity': fields.float('Quantity', digits=(16, 2)),
        'uom_id': fields.related(
            'product_id', 'uom_id', type='many2one', relation='product.uom', 
            string='UOM'),
        'mrp_production_id': fields.many2one(
            'mrp.production', 'Production order', ondelete='cascade'),
        }

class MrpProduction(osv.osv):
    ''' Extra field for lavoration
    '''
    _inherit = 'mrp.production'

    def unload_from_bom(self, cr, uid, ids, context=None):
        ''' Change list of element according to weight and bom
        '''
        return self._action_unload_from_bom(
            cr, uid, ids[0], context=context)
    
    def _action_unload_from_bom(self, cr, uid, item_id, context=None):
        ''' Generic function called from create elements or button for load
            sub material according to BOM selected and quantity
            item_id is the id of mrp.production (integer not list)
            This material is only for see store status, non used for lavorations
        '''
        production_browse = self.browse(cr, uid, item_id, context=context)
        if not production_browse.bom_id and not production_browse.product_qty:
            return True # TODO raise error

        # Delete all elements:
        material_pool = self.pool.get('mrp.production.unload')
        material_ids = material_pool.search(cr, uid, [
            ('mrp_production_id','=',item_id)], context=context)
        material_pool.unlink(cr, uid, material_ids, context=context)

        # Create elements from bom:
        for element in production_browse.bom_id.bom_lines:
            quantity = element.product_qty * production_browse.product_qty \
                / production_browse.bom_id.product_qty \
                if production_browse.bom_id.product_qty else 0.0
            material_pool.create(cr, uid, {
                'product_id': element.product_id.id,
                'lot_id': False,
                'quantity': quantity,
                'uom_id': element.product_id.uom_id.id,
                'mrp_production_id': item_id,
                }, context=context)
        return True

    
    _columns = {
        'bom_unload_ids':fields.one2many(
            'mrp.production.unload', 'mrp_production_id', 
            'BOM material lines'),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),        
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
