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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)


class BomCompareReportWizard(orm.TransientModel):
    """ Wizard for compare bom component
    """
    _name = 'bom.compare.report.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def reset_bom_filter(self, cr, uid, ids, context=None):
        """
        """
        self.write(cr, uid, ids, {
            'bom_ids': [(6, 0, ())],
            }, context=context)

        return {  # reload form:
            'type': 'ir.actions.act_window',
            # 'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'bom.compare.report.wizard',
            # 'view_id': view_id, # False
            'views': [(False, 'form')],
            # 'domain': [(')],
            'context': context,
            'target': 'new',  # 'new'
            'nodestroy': False,
            }

    def load_bom_filter(self, cr, uid, ids, context=None):
        """ Load elements depend on code filter
        """
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        bom_code = wiz_proxy.bom_code
        if not bom_code:
            raise osv.except_osv(
                _('Error'),
                _('Choose part of code before load BOMs!'),
                )
        bom_proxy = self.pool.get('mrp.bom')
        bom_ids = bom_proxy.search(cr, uid, [
            ('product_id.default_code', 'ilike', bom_code)], context=context)

        # Add record yet present:
        for item in wiz_proxy.bom_ids:
            if item.id not in bom_ids:
                bom_ids.append(item.id)

        # TODO merge with yet present!!!
        self.write(cr, uid, ids, {
            'bom_ids': [(6, 0, bom_ids)],
            }, context=context)

        return {  # reload form:
            'type': 'ir.actions.act_window',
            # 'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'bom.compare.report.wizard',
            # 'view_id': view_id, # False
            'views': [(False, 'form')],
            # 'domain': [(')],
            'context': context,
            'target': 'new', # 'new'
            'nodestroy': False,
            }

    def action_print(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        report_name = 'bom_compare_report'

        datas = {}
        datas['bom_ids'] = [item.id for item in wiz_browse.bom_ids]

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            }

    _columns = {
        'bom_code': fields.char('Part code', size=40),
        'bom_ids': fields.many2many(
            'mrp.bom', 'mrp_bom_wizard_rel',
            'bom_id', 'wizard_id', 'BOM'),  # required=True),
        }
