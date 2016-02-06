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
from openerp import SUPERUSER_ID#, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class StockProductionLot(orm.Model):
    """ Model name: Lot
    """    
    _inherit = 'stock.production.lot'
    
    # -------------------------------------------------------------------------
    # SCHEDULE PROCEDURE:
    # -------------------------------------------------------------------------
    def schedule_update_product_lot_status(self, cr, uid, filename, filepath, 
            context=None):
        ''' Import inventory from scheduled
            file name in context:
                filepath: home param compliant
                filename: xls filename
        '''
        def log_error(log_pool, log_id, error):
            ''' Write error in log element:
            '''
            return log_pool.write(cr, uid, log_id, {
                'error': error
                }, context=context)
            
        context = context or {}

        # Pool used:
        product_pool = self.pool.get('product.product')
        lot_pool = self.pool.get('stock.production.lot')
        log_pool = self.pool.get('log.importation')
        
        # ---------------------------------------------------------------------
        #                Open XLS document (first WS):
        # ---------------------------------------------------------------------

        # Create import log for this import:
        log_id = log_pool.create(cr, uid, {
            'name': 'Import Inventory: %s' % datetime.now(),
            'error': '',
            # Extra info write at the end
            }, context=context)

        #filename = context.get('filename', False)
        #filepath = context.get('filepath', False)
        if not (filepath and filename):
            return log_error(log_pool, log_id, 
                'No filename or filepath set up un context!!')
        
        fullname = os.path.join(os.path.expanduser(filepath), filename)
        _logger.info('Start import from path: %s' % fullname)        

        try:
            # from xlrd.sheet import ctype_text   
            wb = xlrd.open_workbook(fullname)
            ws = wb.sheet_by_index(0)
        except:
            return log_error(log_pool, log_id, 
                'Error opening XLS file!')

        annotation = ''
        min_line = 0 # Start from 0 (different from line number)
        max_line = 30000
        # Parameter for import (written in row before data:
        header_row = '****'
        code_col = 'code'
        lot_col = 'lot'
        qty_col = 'qty'

        code_id = False
        lot_id = False
        qty_id = False
        
        parameters = 3 # code, lot, qty
        start = False
        
        error = ''
        for i in range(min_line, max_line):
            try:
                row = ws.row(i)                
            except:
                annotation += _('Import end at line: %s\n') % i
                break
            
            try:
                if not start and row[0].value == header_row:                    
                    start = True
                    parameter = 0
                    for col in range(1, 50):
                        try:
                            if row[col].value == code_col:
                                code_id = col
                                parameter += 1
                                continue
                            elif row[col].value == lot_col:
                                lot_id = col
                                parameter += 1
                                continue
                            elif row[col].value == qty_col:
                                qty_id = col
                                parameter += 1
                                continue
                        except:
                            break # out of range        
                    if parameter != parameters:
                        return log_error(log_pool, log_id, 
                            '''Write a line before data with: 
                               First col: ****
                               Code col: 'code'
                               Lot col: 'lot'
                               Quantity col: 'qty'
                               (you could also hide it!<br/>
                            ''')
                    continue # next line
                if not start: # Jump all line till start
                    continue
                
                # TODO manage error?
                if not (
                        row[code_id].value and row[lot_id].value):
                    _logger.warning('%s. Jump line' % i)    
                    error += _('%s. Warning Line without all element<br/>' % i)
                    continue
                        
                code = '%08d' % row[code_id].value
                lot = '%d' % row[lot_id].value
                qty = row[qty_id].value                
                #        if type(f) not in (float, int) :
                #            f = float(f.replace(',', '.'))
                
                # Search product code:
                product_ids = product_pool.search(cr, uid, [
                    ('default_code', '=', code)], context=context)
                if not product_ids:
                    error += '%s. Product code not found: <b>%s</b><br/>' % (
                        i, code)
                    continue
                if len(product_ids) > 1:
                    error += '%s. Double product: <b>%s</b><br/>' % (i, code)                        
                    
                # Search product lot:
                lot_ids = lot_pool.search(cr, uid, [
                    ('name', '=', lot)], context=context)
                if not lot_ids:
                    error += '%s. Product lot code not found:<b>%s</b><br/>' % (
                        i, lot)
                    continue
                # TODO check also product-lot compliant!!!    

                lot_pool.write(cr, uid, lot_ids[0], {
                    'xls_qty': qty,
                    }, context=context)
                _logger.info('%s. Update product %s - lot %s with %s' % (
                    i, code, lot, qty))
            except:
                error += _('%s. Error import: <b>%s [%s]</b>[%s]</br><br/>') % (
                    i, code, lot, sys.exc_info())

        # Update lof with extra information:    
        log_pool.write(cr, uid, log_id, {
            'error': error,
            'note': '''
                File: <b>%s</b></br>
                Import note: <i>%s</i></br>
                ''' % (
                    fullname,
                    annotation),
            }, context=context)

        _logger.info('End import XLS product file: %s' % fullname)
        return True
        
    
    _columns = {
        'xls_qty': fields.float('Lot qty', digits=(16, 3)), 
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
