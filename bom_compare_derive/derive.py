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


class MrpBomDerived(osv.osv):
    """ Add extra field to manage mrp.bom
    """
    _inherit = 'mrp.bom'

    # --------------
    # Button events:
    # --------------
    def load_from_parent(self, cr, uid, ids, context=None):
        """ Load from parent
        """
        assert len(ids), 'Run only with one BOM!'

        # ---------------------
        # Remove current lines:
        # ---------------------
        bom_proxy = self.browse(cr, uid, ids, context=context)[0]
        unlink_ids = [item.id for item in bom_proxy.bom_lines]
        self.unlink(cr, uid, unlink_ids, context=context)

        # ---------------------------------
        # Create line from parent elements:
        # ---------------------------------
        for line in bom_proxy.from_bom_id.bom_lines:
            self.create(cr, uid, {
                'bom_id': ids[0],
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_qty': line.product_qty,
                'date_start': line.date_start,
                'date_stop': line.date_stop,
                }, context=context)
        return True

    _columns = {
        'from_bom_id': fields.many2one(
            'mrp.bom', 'From BOM', domain=[('bom_id', '=', False)]),
        }


class MrpBomDerived(osv.osv):
    """ Add extra field to manage mrp.bom
    """
    _inherit = 'mrp.bom'

    _columns = {
        'derived_ids': fields.one2many(
            'mrp.bom', 'from_bom_id', 'Derived BOM'),
        }
