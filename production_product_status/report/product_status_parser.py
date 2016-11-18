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


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
        })
    
    def get_objects(self, objects, data):
        ''' Load data for product status report
        '''
        res = []
        
        cr = self.cr
        uid = self.uid
        context = {}
        
        if data is None:
            data = {}            
        
        lavoration_pool = self.pool.get('mrp.production.workcenter.line')
        order_line_pool = self.pool.get('sale.order.line')
        
        range_date = 7 # TODO        
        # Cols for date:
        cols = []
        for i in range(0, range_date):
            cols.append(datetime.now() + timedelta(days=i))        
        start_date = cols[0]
        end_date = cols[-1]

        for o in objects: # product
            record = (o, dict.fromkeys(cols, 0))
            # Start q from account # TODO change
            record[1][0] = o.accounting_qty or 0.0

            # -----------------------------------------------------------------
            # Get product list from OC lines:
            # -----------------------------------------------------------------      
            # only active from accounting
            line_ids = order_line_pool.search(cr, uid, [
                ('date_deadline', '<=', end_date.strftime('%Y-%m-%d')),
                ('product_id', '=', o.id), # only this
                ])
                
            for line in order_line_pool.browse(cr, uid, line_ids):
                deadline = line.date_deadline
                deadline = start_date
                record[1][deadline] -= line.product_uom_qty or 0.0                    
                
            # -----------------------------------------------------------------
            #                   Get material list from Lavoration order
            # -----------------------------------------------------------------
            lavoration_ids = lavoration_pool.search(cr, uid, [
                ('real_date_planned', '<=', end_date.strftime(
                    '%Y-%m-%d 23:59:59')), # only < max date range
                ('state', 'not in', ('cancel','done')),
                ('production_id.product_id', '=', o.id),
                ]) # only open not canceled
            
            for lavoration in lavoration_pool.browse(
                    cr, uid, lavoration_ids): 
                record[1][lavoration.real_date_planned[:10]] +=\
                    lavoration.product_qty or 0.0
            res.append(record)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
