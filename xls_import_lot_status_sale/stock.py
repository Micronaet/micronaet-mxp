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

class StockProductionLot(orm.Model):
    """ Model name: Lot
    """    
    _inherit = 'stock.production.lot'
    
    def name_get(self, cr, uid, ids, context=None):
        """ Return a list of tupples contains id, name.
            result format : {[(id, name), (id, name), ...]}
            
            @param cr: cursor to database
            @param uid: id of current user
            @param ids: list of ids for which name should be read
            @param context: context arguments, like lang, time zone
            
            @return: returns a list of tupples contains id, name
        """
        context = context or {}
        
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]            
            
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            if context.get('show_lot_status', False) == True:
                res.append((record.id, '%s [%s]' % (
                    record.name,
                    record.xls_qty or 0.0,
                    )))
            else:
                res.append((record.id, record.name))
        return res
        
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
