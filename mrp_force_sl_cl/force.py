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

class MrpProductionWorkcenterLoad(orm.Model):
    """ Model name: MrpProductionWorkcenterLoad
    """    
    
    _inherit = 'mrp.production.workcenter.load'

    # --------------    
    # Button events:
    # --------------    
    def button_re_send_CL_document(self, cr, uid, ids, context=None):
        ''' Button for re sent CL document (save file and launch XMLRPC
            procedure)
        '''
        # Pool used:
        mrp_pool = self.pool.get('mrp.production')
        
        # Read parameters:
        import pdb; pdb.set_trace()
        parameter = mrp_pool.get_sl_cl_parameter(cr, uid, context=context)
        load_browse = self.browse(cr, uid, ids, context=context)[0]
        file_cl, file_cl_upd, file_sl = mrp_pool.get_interchange_files(
            cr, uid, parameter, context=context)

        # XMLRPC server:
        mx_server = mrp_pool.get_xmlrpc_sl_cl_server(
            cr, uid, parameter, context=context)

        # ---------------------------------------------------------------------
        #                            Export CL file:
        # ---------------------------------------------------------------------        
        # Read data from saved lavoration
        product_qty = load_browse.product_qty
        #line_id = load_browse.line_id.id
        partial = load_browse.partial
        package = load_browse.package_id # browse
        lavoration = load_browse.line_id #workcenter_line_id
        ul_qty = load_browse.ul_qty
        pallet = load_browse.pallet_product_id#.id
        pallet_qty = load_browse.pallet_qty
        recycle = load_browse.recycle
        recycle_product_id  = load_browse.recycle_product_id.id
        wrong = load_browse.wrong
        #wrong_comment = load_browse.wrong_comment
        sequence = load_browse.sequence
        product_code = load_browse.product_code
        accounting_cost = load_browse.accounting_cost # price calculated!
        price = accounting_cost / product_qty        
                
        if not price:
            raise osv.except_osv(
                _('Price error!'),
                _('Price is empty, problem with lavoration non closed!'),
                )
        
        # Open transit file:
        try:
            f_cl = open(file_cl, 'w')
        except:
            raise osv.except_osv(
                _('Transit file problem accessing!'),
                _('%s (maybe open in accounting program)!') % file_cl,
                )
                
        if wrong:
            f_cl.write('%-35s%10.2f%10.2f\r\n' % (
                '%sR%s' % (
                    product_code[:7],
                    product_code[8:],
                    ),
                product_qty,
                price,
                ))
        else:
            f_cl.write('%-35s%10.2f%10.2f\r\n' % (
                product_code, product_qty, price))

        if package.id and ul_qty:
            f_cl.write(
                '%-10s%-25s%10.2f%-10s\r\n' % ( # TODO 10 extra space
                    package.linked_product_id.default_code,
                    ' ' * 25, #lavoration_browse.name[4:],
                    - ul_qty,
                    lavoration.accounting_sl_code,
                ))
        else:
            pass # TODO raise error if no package? (no if wrong!)
        if pallet and pallet_qty: # XXX after was pallet
            f_cl.write(
                '%-10s%-25s%10.2f%-10s\r\n' % ( # TODO 10 extra space
                    pallet.default_code,
                    ' ' * 25, #lavoration_browse.name[4:],
                    - pallet_qty,
                    lavoration.accounting_sl_code,
                ))
        else:
            pass                
        f_cl.close()
        
        if parameter.production_demo:
            raise osv.except_osv(
            _('Import CL error!'),
            _('XMLRPC not launched: DEMO Mode!'), 
            )
            return 

        # ---------------------------------------------------------------------
        #               CL for material and package
        # ---------------------------------------------------------------------
        try:
            accounting_cl_code = mx_server.sprix('CL')
            if load_browse.accounting_cl_code != accounting_cl_code:
                raise osv.except_osv(
                    _('Different CL document!'),
                    _('Current CL: %s Accounting: %s') % (
                        load_browse.accounting_cl_code,
                        accounting_cl_code,                            
                        ),
                    )                    
            _logger.warning('CL creation esit: %s' % accounting_cl_code)
        except:    
            raise osv.except_osv(
                _('Import CL error!'),
                _('XMLRPC error calling import CL procedure'), )                
        return True
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
