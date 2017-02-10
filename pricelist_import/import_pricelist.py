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
import xlrd
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

class ProductPricelist(orm.Model):
    """ Model name: ProductPricelist
    """
    _inherit = 'product.pricelist'
    
    def schedule_import_xls_pricelist(self, cr, uid, context=None):
        ''' Import pricelist file schedule action
        '''
        xls_file = 'pricelist.xls'
        xls_path = '/home/administrator/etl/pricelist'
        max_row = 50000
        max_col = 50
        
        version_pool = self.pool.get('product.pricelist.version')
        item_pool = self.pool.get('product.pricelist.item')
        product_pool = self.pool.get('product.product')
        
        # ---------------------------------------------------------------------
        # Open pricelist XLS file:
        # ---------------------------------------------------------------------
        xls_filename = os.path.join(xls_path, xls_file)
        _logger.info('Start import: %s' % xls_filename)

        try:
            # from xlrd.sheet import ctype_text
            WB = xlrd.open_workbook(xls_filename)
            WS = WB.sheet_by_index(0)
        except:
            raise osv.except_osv(
                _('Import file: %s') % xls_filename, 
                _('Error opening XLS file: %s' % (sys.exc_info(), )),
                )

        page = WS.name
        

        # ---------------------------------------------------------------------
        # Pricelist creation or found:        
        # ---------------------------------------------------------------------
        pricelist_ids = self.search(cr, uid, [
            ('xls_filename', '=', xls_file),
            # TODO page!
            ], context=context)
        if pricelist_ids:
            pricelist_id = pricelist_ids[0]
        else:
            pricelist_id = self.create(cr, uid, {   
                'name': '%s [%s]' % (xls_file, page),
                'xls_filename': xls_file,
                'xls_page': page,
                'type': 'sale',
                # TODO currency                                
                }, context=context)

        # ---------------------------------------------------------------------
        # Pricelist versione creation or found
        # ---------------------------------------------------------------------
        version_ids = version_pool.search(cr, uid, [
            ('pricelist_id', '=', pricelist_id),
            # TODO page!
            ], context=context)
        if version_ids:
            version_id = version_ids[0]
        else:
            version_id = version_pool.create(cr, uid, {   
                'pricelist_id': pricelist_id,
                'name': 'Version %s' % page,
                'active': True,
                # TODO currency                                
                }, context=context)
        
        # ---------------------------------------------------------------------
        # Pricelist rule for every product:
        # ---------------------------------------------------------------------
        item_ids = item_pool.search(cr, uid, [
            ('base_pricelist_id', '=', version_id),
            ], context=context)
        if item_ids:
            item_pool.unlink(cr, uid, item_ids)
        
        xls_log = ''
        col_code = 0
        col_pricelist = False
        
        start = False
        for line in range(0, max_row):        
            try:
                row = WS.row(line)
            except:
                _logger.warning('File end at line: %s' % line)
                break 
            if not start and row[0].value == 'default_code':
                for col in range(1, max_col): 
                    try:
                        if row[col].value != 'pricelist':
                            continue
                    except: # read error
                        break
                    start = True
                    col_pricelist = col     
                    break 
                    
                if start:
                    continue
                else:
                    _logger.error('No pricelist column found')
                    break
            if not start:
                continue             
            
            default_code = row[0].value
            if not default_code:
                continue # jump line
                
            try:    
                product_price = row[col_pricelist].value
            except:
                product_price = 0.0 # TODO error
            # Search product code:
            product_ids = product_pool.search(cr, uid, [
                ('default_code', '=', default_code),
                ], context=context)
            if not product_ids:
                xls_log += _('Product %s not found!' % default_code)
                continue

            # Create line
            item_pool.create(cr, uid, {   
                #'base_pricelist_id': pricelist_id,
                'product_id': product_ids[0],
                #'product_tmpl_id': product_ids[0],
                'price_round': 0.01,
                'sequence': 100,
                #company_id
                'name': _('Rule: %s') % default_code,
                'base': 1,#'cost', # 
                'price_version_id': version_id,
                'min_quantity': 1,
                #'price_min_margin': 0.0,
                #'price_max_margin': 0.0,
                #'categ_id': False,
                'price_discount': -1.0,
                'price_surcharge': product_price,
                }, context=context)
        
        
        _logger.info('End import: %s' % xls_filename)
        return True
    
    def import_xls_pricelist(self, cr, uid, ids, context=None):
        ''' Import pricelist button event
        '''
        assert len(ids) == 1, 'Works only with one record a time'
        current_pricelist = self.browse(cr, uid, ids, context=context)[0]
        
        return True
        
    _columns = {
        'xls_filename': fields.char('XLS file', size=80),
        'xls_page': fields.char('XLS page', size=80),
        'xls_log': fields.text('XLS log'),        
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
