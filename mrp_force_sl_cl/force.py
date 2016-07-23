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

class MrpProductionWorkcenterLine(orm.Model):
    """ Model name: MrpProductionWorkcenterLine
    """    
    
    _inherit = 'mrp.production.workcenter.line'

    # --------------    
    # Button events:
    # --------------    
    def button_re_send_SL_document(self, cr, uid, ids, context=None):
        ''' Button for re sent SL document (save file and launch XMLRPC
            procedure)
        '''
        # Pool used:
        mrp_pool = self.pool.get('mrp.production')
        
        # Read parameters:
        parameter = mrp_pool.get_sl_cl_parameter(cr, uid, context=context)
        lavoration_browse = self.browse(cr, uid, ids, context=context)[0]
        file_cl, file_cl_upd, file_sl = mrp_pool.get_interchange_files(
            cr, uid, parameter, context=context)

        # Exrport SL files (without correct stock status)
        mrp_pool.create_unload_file(
            cr, uid, file_sl, lavoration_browse, force_stock=False, 
            context=context)

        # XMLRPC server:
        mx_server = mrp_pool.get_xmlrpc_sl_cl_server(
            cr, uid, parameter, context=context)

        if parameter.production_demo:
            raise osv.except_osv(
            _('Import SL error!'),
            _('XMLRPC not launched: DEMO Mode!'), 
            )
        else:
            # ---------------------------------------------------------
            #               SL for material and package
            # ---------------------------------------------------------
            try:
                accounting_sl_code = mx_server.sprix('SL')
                if lavoration_browse.accounting_sl_code != accounting_sl_code:
                    raise osv.except_osv(
                        _('Different SL document!'),
                        _('Current SL: %s Accounting: %s') % (
                            lavoration_browse.accounting_sl_code,
                            accounting_sl_code,                            
                            ),
                        )                    
                _logger.warning('SL creation esit: %s' % accounting_sl_code)                
            except:    
                raise osv.except_osv(
                    _('Import SL error!'),
                    _('XMLRPC error calling import SL procedure'), )                

            # TODO in future used for resend normally with recreation SL code:
            #lavoration_pool.write(
            #    cr, uid, [current_lavoration_id], {
            #        'accounting_sl_code': accounting_sl_code,
            #        'unload_confirmed': True, 
            #        # TODO non dovrebbe più servire 
            #        # Next 'confirm' is for prod.
            #        },
            #    context=context)
        return True
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
