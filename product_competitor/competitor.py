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


class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'competitor': fields.boolean('Competitor', 
            help='Mark partner as competitor for manage his products'),
    }

class ProductProductCompetitor(orm.Model):
    """ Model name: ProductProducCopetitors
    """    
    _name = 'product.product.competitor'
    _description = 'Competitor product' 
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'default_code': fields.char('Name', size=64),
        'note': fields.text('Note'),
        'partner_id': fields.many2one('res.partner', 'Competitor', 
            domain=[('competitor', '=', True)]), 
        }

class ProductProductCompetitorRel(orm.Model):
    """ Model name: ProductProducCopetitorsRel
    """    
    _name = 'product.product.competitor.rel'
    _description = 'Competitors product relation' 
    _rec_name = 'competitor_id'
    
    _columns = {
        'competitor_id': fields.many2one('product.product.competitor', 
            'Competitor product'),
        'product_id': fields.many2one('product.product', 'Competitor'), 
        'note': fields.text('Note'),
        }

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """
    
    _inherit = 'product.product'
    
    _columns = {
        'competitor_ids': fields.one2many(
            'product.product.competitor.rel', 'product_id', 
            'Competitor product'), 
        }
    
class ProductProductCompetitor(orm.Model):
    """ Model name: ProductProducCopetitors
    """    
    _inherit = 'product.product.competitor'
    
    _columns = {
        'product_ids': fields.one2many(
            'product.product.competitor.rel', 'competitor_id', 
            'Company product'), 
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
