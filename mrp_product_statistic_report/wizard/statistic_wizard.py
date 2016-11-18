# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) and the
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#    ########################################################################
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
from openerp.osv import fields, osv
from datetime import datetime, timedelta
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


class MrpStatisticProductWizard(osv.osv_memory):
    ''' Wizard that assign lavoration to the selected order line
    '''
    _name = 'mrp.statistic.product.wizard'
    _description = 'MRP statistic report'

    # Wizard button:
    def action_open_report(self, cr, uid, ids, context=None):
        ''' Open report
        '''
        if context is None: context={}        
        data = {}
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        data['from_date'] = wiz_proxy.from_date
        data['to_date'] = wiz_proxy.to_date
        data['product_id'] = wiz_proxy.product_id.id or False

        return {
            'type': 'ir.actions.report.xml', 
            'report_name': 'mrp_order_product_statistic_report',        
            'datas': data,
            }

    _columns = {
        'from_date': fields.date('From'),
        'to_date': fields.date('To'),
        'product_id': fields.many2one(
            'product.product', 'Product'), 
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
