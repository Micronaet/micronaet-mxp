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
            'get_date': self.get_date, # get date

            'load_data': self.load_data,
            'get_filter_description': self.get_filter_description,            
            'get_data': self.get_data,
        })
        
    def load_data(self, data):
        ''' Load data for report
        '''
        # ---------------------------------------------------------------------
        #                           Get parameters:
        # ---------------------------------------------------------------------
        cr = self.cr
        uid = self.uid
        context = {}
        
        data = data or {}
        bom_ids = data.get('bom_ids', [])
        
        # ---------------------------------------------------------------------
        #                          Create structure:
        # ---------------------------------------------------------------------
        self.filter_description = ''
        self.extract_component = [] # row
        self.extract_bom = [] # col        
        self.extract_data = {} # cell
        
        # ---------------------------------------------------------------------
        #                           Populate data:
        # ---------------------------------------------------------------------
        # Pool used:
        bom_pool = self.pool.get('mrp.bom')
        for bom in bom_pool.browse(cr, uid, bom_ids, context=context):
            has_component = False
            for component in bom.bom_lines:
                has_component = True
                # Row part:
                if component not in self.extract_component:
                    self.extract_component.append(component)

                # Cell part:
                key = (bom.id, component.id)
                if key not in self.extract_data:
                    self.extract_data[key] = component.product_qty
                else: # append if double    
                    self.extract_data[key] += component.product_qty        
            if not has_component: # jump empty BOM
                continue
            # Col part:
            self.extract_bom.append(bom)
            #self.filter_description += '[%s] ' % (
            #    bom.product_id.default_code or bom.name or '???')
                    
        # Sort operations:            
        self.extract_component.sort(
            key=lambda x: x.product_id.default_code or '?')            

        self.extract_bom.sort(
            key=lambda x: x.product_id.default_code or x.name or '?')            
        return ''
   
    def get_filter_description(self):
        ''' Return text extract during load data
        '''
        return self.filter_description
    
    def get_data(self, mode, key=False):
        ''' Return 3 data type:
            1. component for row
            2. bom from columns
            3. key for cells key element (passed as key value)
        '''
        if mode == 'component':
            return self.extract_component
        elif mode == 'bom':
            return self.extract_bom
        elif mode == 'key':
            value = self.extract_data.get(key, '')
            if value:
                return '%10.6f' % value
            else:
                return value
        return '?'
        

    def get_date(self):
        ''' Return datetime obj
        '''
        return datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
