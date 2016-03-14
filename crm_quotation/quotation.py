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
import datetime
from openerp.osv import osv, fields


class sale_order(osv.osv):
    ''' Extra fields for offer
    '''
    _name = 'sale.order'
    _inherit = 'sale.order'
    
    _columns = {
        'only_not_sold':fields.boolean('If not sold', required = False, help = 'Extra clause to print in quotation', ),
        'with_default_code':fields.boolean('Print product code', required = False, help = 'In quotation print product code', ),
        'transport': fields.text('Transport', help = 'Transport information'),
        'package': fields.text('Package', help = 'Package information'),
        'delivery_note': fields.text('Delivery note', help = 'Note for delivery'),
    }
    
    _defaults = {
        'only_not_sold': lambda *a: True,
        'with_default_code': lambda *a: False,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
