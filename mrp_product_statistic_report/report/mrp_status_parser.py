# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import openerp
import xlsxwriter # XLSX export
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
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

class MrpProduction(orm.Model):
    """ Model name: MrpProduction
    """    
    _inherit = 'mrp.production'
    
    _columns = {
        'stat_theoric': fields.float('Theoric Qty', digits=(16, 3)),
        'stat_real': fields.float('Real Qty', digits=(16, 3)),
        'stat_recycle': fields.float('Recycle Qty', digits=(16, 3)),
        'stat_wc_id': fields.many2one('mrp.workcenter', 'Line'),
        }
    

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
        })
    
    def get_objects(self, data, context=None):
        ''' Load data for product status report
        '''
        # Utility:
        def write_xls(WS, row, counter):
            ''' Write line in XLS file (used also for header)
            '''
            col = 0
            for item in row:
                WS.write(counter, col, item)
                col += 1
        
        cr = self.cr
        uid = self.uid
        if context is None:
            context = {}
        with_history = True # context.get('with_history') 

        # ---------------------------------------------------------------------
        #                           Work Book
        # ---------------------------------------------------------------------
        # Output XLS log file:
        xls = '~/smb/production.xlsx'
        xls = os.path.expanduser(xls)
        WB = xlsxwriter.Workbook(xls)
        
        # ---------------------------------------------------------------------
        #                           Work Sheet:
        # ---------------------------------------------------------------------
        # Rese:
        WS_mrp = WB.add_worksheet('Rese')
        write_xls(WS_mrp, [
            'Linea',
            'Produzione',
            'Anno',
            'Periodo',
            'Data',
            'Prodotto',
            'Teorica',
            'Effettiva',
            'Recupero',
            'Resa Teo. / Eff.)',
            'Recupero Rec. / Eff.)',
            'Anomalia',
            ], 0) # write header
        counter_mrp = 0 # Jump header line
        
        # Lavorazioni:
        WS = WB.add_worksheet('Lavorazioni')
        write_xls(WS, [
            'Linea',
            'Anno',
            'Periodo',
            'Data',
            'Prodotto',
            'Produzione',
            'Documento',
            'Teorica',
            'Effettiva',
            'Recupero',
            ], 0) # write header
        counter = 0 # Jump header line
        
        # ---------------------------------------------------------------------
        #                       Collect Statistic data:
        # ---------------------------------------------------------------------        
        mrp_pool = self.pool.get('mrp.production')

        # Get data wizard selection:        
        if data is None:
            data = {}    
        
        from_date = data.get('from_date', False)
        to_date = data.get('to_date', False)
        product_id = data.get('product_id', False)

        # Filter report:
        domain = [
         #('state', '!=', 'cancel'),
         ('accounting_state', '=', 'close'),
         ]
        if from_date:
            domain.append(('date_planned', '>=', from_date))
        if to_date:
            domain.append(('date_planned', '<=', to_date))
        if product_id:
            domain.append(('product_id', '=', product_id))

        res = {}        
        mrp_ids = mrp_pool.search(cr, uid, domain, context=context)
        for mrp in mrp_pool.browse(cr, uid, mrp_ids, context=context):  
            counter_mrp += 1              
            product = mrp.product_id

            # Check total:
            mrp_in = 0.0 # MP input
            mrp_out = 0.0 # PF output
            mrp_recycle = 0.0 # Recycle
            
            if product not in res:
                # theoric, real, recycle
                res[product] = [0.0, 0.0, 0.0] 

            # Lavoration Theoric:
            wc_line = '?'
            wc_id = False
            for wc in mrp.workcenter_lines: # Lavoration
                counter += 1
                wc_id = wc.workcenter_id.id or False
                wc_line = wc.workcenter_id.name
                
                # Total MP
                material_qty = sum([m.quantity for m in wc.bom_material_ids])
                res[product][0] += material_qty
                mrp_in += material_qty
                    
                # LOG XLS line:
                date_ref = wc.real_date_planned or ''
                write_xls(WS, [
                    wc_line, # Line
                    date_ref[:4], # Year
                    date_ref[:7], # Period
                    date_ref, # Date
                    product.default_code, # Product
                    mrp.name, # MRP
                    wc.name, # Document
                    material_qty, # 5. Q. theoric
                    0.0, # 6. Q. real
                    0.0, # 7. Recycle
                    ], counter)
            
            # CL Real: 
            for cl in mrp.load_ids:
                counter += 1
                res[product][1] += cl.product_qty
                mrp_out += cl.product_qty
                
                # Recycle error:
                if cl.recycle:
                    res[product][2] += cl.product_qty
                    mrp_recycle += cl.product_qty  

                # LOG XLS line:
                date_ref = cl.date or ''
                write_xls(WS, [
                    wc_line, # 0. XXX Last line found previous loop 
                    date_ref[:4], # Year
                    date_ref[:7], # Period
                    date_ref, # Date
                    product.default_code, # Product
                    mrp.name, # MRP
                    'CL%s'  % cl.accounting_cl_code, # Document
                    0.0, # Q. theoric
                    cl.product_qty, # Q. real
                    cl.product_qty if cl.recycle else 0.0, # Recycle
                    ], counter)
            
            # -----------------------------------------------------------------
            # Write Work book for mrp data        
            # -----------------------------------------------------------------
            date_ref = mrp.date_planned
            write_xls(WS_mrp, [
                wc_line,
                mrp.name, # 0. XXX Last line found previous loop 
                date_ref[:4], # Year
                date_ref[:7], # Period
                date_ref, # Date
                product.default_code, # Product
                mrp_in, # Q. theoric
                mrp_out, # Q. real
                mrp_recycle, # Recycle
                mrp_out / mrp_in * 100.0 if mrp_in else 0.0,
                mrp_recycle / mrp_in * 100.0 if mrp_in else 0.0, # TODO check!!
                'X' if mrp_in < mrp_out else '',
                ], counter_mrp)
                
            if with_history:
                mrp_pool.write(cr, uid, mrp.id, {
                    'stat_theoric': mrp_in,
                    'stat_real': mrp_out,
                    'stat_recycle': mrp_recycle,
                    'stat_wc_id': wc_id,
                    }, context=context)    
                
    
        # Sort order
        records = []
        for record in sorted(res, key=lambda x: x.default_code):
            records.append((record, res[record]))
        return records
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
