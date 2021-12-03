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
import pdb
import sys
import logging
import openerp
import xlsxwriter # XLSX export
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


class ProductProduct(orm.Model):
    """ Model name: MrpProduction
    """
    _inherit = 'product.product'

    _columns = {
        'mrp_medium_yield': fields.float('Rendimento medio', digits=(16, 3)),
        }


class MrpProduction(orm.Model):
    """ Model name: MrpProduction
    """
    _inherit = 'mrp.production'

    def scheduled_get_statistic_report_objects(
            self, cr, uid, data=None, context=None):
        """ Scheduled operation for upload data in production (used in stat.
            views)
        """
        _logger.warning('Simulation report: generate statistic data')
        self.get_statistic_report_objects(cr, uid, data=data, context=context)
        _logger.warning('End simulation report: generate statistic data')
        return True

    def get_statistic_report_objects(self, cr, uid, data=None, context=None):
        """ Load data for product status report
        """
        # Utility:
        def write_xls(WS, row, counter):
            """ Write line in XLS file (used also for header)
            """
            col = 0
            for item in row:
                WS.write(counter, col, item)
                col += 1

        if context is None:
            context = {}
        with_history = True  # context.get('with_history')
        product_pool = self.pool.get('product.product')

        # ---------------------------------------------------------------------
        #                           Work Book
        # ---------------------------------------------------------------------
        # Output XLS log file:
        xls = '~/smb/production.xlsx'
        xls = os.path.expanduser(xls)
        WB = xlsxwriter.Workbook(xls)

        # ---------------------------------------------------------------------
        #                           Work Sheet:
        # ---------------------------------------------------------------------
        # Rese:
        WS_mrp = WB.add_worksheet('Rese')
        write_xls(WS_mrp, [
            'Linea', 'Produzione', 'Anno', 'Periodo', 'Data', 'Prodotto',
            'Teorica', 'Effettiva', 'Recupero', 'Riutilizzo',
            'Resa Teo. / Eff.)', 'Recupero Rec. / Eff.)', 'Anomalia',
            ], 0)  # write header
        counter_mrp = 0  # Jump header line

        # Lavorazioni:
        WS = WB.add_worksheet('Lavorazioni')
        write_xls(WS, [
            'Linea', 'Anno', 'Periodo', 'Data', 'Prodotto', 'Produzione',
            'Documento', 'Teorica', 'Effettiva', 'Recupero', 'Riutilizzo',
            ], 0)  # write header
        counter = 0  # Jump header line

        # ---------------------------------------------------------------------
        #                       Collect Statistic data:
        # ---------------------------------------------------------------------
        # Get data wizard selection:
        if data is None:
            data = {}

        from_date = data.get('from_date', False)
        to_date = data.get('to_date', False)
        product_id = data.get('product_id', False)

        # Filter report:
        domain = [
             # ('state', '!=', 'cancel'),
             ('accounting_state', '=', 'close'),
             ]
        if from_date:
            domain.append(('date_planned', '>=', from_date))
        if to_date:
            domain.append(('date_planned', '<=', to_date))
        if product_id:
            domain.append(('product_id', '=', product_id))

        res = {}
        mrp_ids = self.search(cr, uid, domain, context=context)
        for mrp in self.browse(cr, uid, mrp_ids, context=context):
            counter_mrp += 1
            product = mrp.product_id

            # Check total:
            # Raw, final product, recycle, reused total:
            mrp_in = mrp_out = mrp_recycle = mrp_reused = 0.0

            if product not in res:
                # theoric, real, recycle, reused
                res[product] = [0.0, 0.0, 0.0, 0.0]

            # Job Theoric:
            wc_line = '?'
            wc_id = False
            for wc in mrp.workcenter_lines:  # Job
                if wc.state == 'cancel':
                    continue

                counter += 1
                wc_id = wc.workcenter_id.id or False
                wc_line = wc.workcenter_id.name

                # Total MP
                material_qty = reused_qty = 0.0
                for move in wc.bom_material_ids:
                    material_qty += move.quantity
                    first_char = (
                        move.product_id.default_code or '')[0].upper()
                    if first_char and first_char not in 'AB':
                        reused_qty += move.quantity

                # material_qty = sum([m.quantity for m in wc.bom_material_ids])
                # Partial:
                res[product][0] += material_qty
                res[product][3] += reused_qty

                # Total:
                mrp_in += material_qty
                mrp_reused += reused_qty

                # LOG XLS line:
                date_ref = wc.real_date_planned or ''
                write_xls(WS, [
                    wc_line,  # Line
                    date_ref[:4],  # Year
                    date_ref[:7],  # Period
                    date_ref,  # Date
                    product.default_code,  # Product
                    mrp.name,  # MRP
                    wc.name,  # Document
                    material_qty,  # 5. Q. theoric
                    0.0,  # 6. Q. real
                    0.0,  # 7. Recycle
                    0.0,  # 8. Reused
                    ], counter)

            # CL Real:
            for cl in mrp.load_ids:
                counter += 1
                res[product][1] += cl.product_qty
                mrp_out += cl.product_qty

                # Recycle error:
                if cl.recycle:
                    res[product][2] += cl.product_qty
                    mrp_recycle += cl.product_qty
                # todo mettere la real come else per non includere i ricicli?

                # LOG XLS line:
                date_ref = cl.date or ''
                write_xls(WS, [
                    wc_line,  # 0. XXX Last line found previous loop
                    date_ref[:4],  # Year
                    date_ref[:7],  # Period
                    date_ref,  # Date
                    product.default_code,  # Product
                    mrp.name,  # MRP
                    'CL%s' % cl.accounting_cl_code,  # Document
                    0.0,  # Q. theoric
                    cl.product_qty,  # Q. real
                    cl.product_qty if cl.recycle else 0.0,  # Recycle
                    0.0,  # todo Reused needed?
                    ], counter)

            # -----------------------------------------------------------------
            # Write Work book for mrp data
            # -----------------------------------------------------------------
            date_ref = mrp.date_planned
            write_xls(WS_mrp, [
                wc_line,
                mrp.name,  # 0. XXX Last line found previous loop
                date_ref[:4],  # Year
                date_ref[:7],  # Period
                date_ref,  # Date
                product.default_code,  # Product
                mrp_in,  # Q. theoric
                mrp_out,  # Q. real
                mrp_recycle,  # Recycle
                mrp_reused,  # Reused product
                mrp_out / mrp_in * 100.0 if mrp_in else 0.0,
                mrp_recycle / mrp_in * 100.0 if mrp_in else 0.0,  # todo check!
                'X' if mrp_in < mrp_out else '',
                ], counter_mrp)

            if with_history:
                self.write(cr, uid, mrp.id, {
                    'stat_theoric': mrp_in,
                    'stat_real': mrp_out,
                    'stat_recycle': mrp_recycle,
                    'stat_reused': mrp_reused,
                    'stat_wc_id': wc_id,
                    }, context=context)

        # Sort order
        records = []
        for record in sorted(res, key=lambda x: x.default_code):
            data = res[record]
            records.append((record, data))

            # Product:
            if with_history and data[0]:
                mrp_medium_yield = 100.0 * data[1] / data[0]
                product_pool.write(cr, uid, record.id, {
                    'mrp_medium_yield': mrp_medium_yield,
                    }, context=context)
        return records

    def _get_real_net(self, cr, uid, ids, fields, args, context=None):
        """ Fields function for calculate
        """
        res = {}
        for mrp in self.browse(cr, uid, ids, context=context):
            res[mrp.id] = mrp.stat_real - mrp.stat_reused - mrp.stat_recycle
        return res

    _columns = {
        'stat_theoric': fields.float(
            'Q. nominale', digits=(16, 3),
            help='Q. indicata sulla distinta di produzione, è il totale'
                 'teorico per il quale si sta facendo la produzione (può'
                 'capitare che nel processo produttivo vengano aggiunte poi '
                 'dei recuperi extra che portano a produrre più di quello '
                 'pianificato. Se è minore è richiesto una correzione sulla'
                 'testata della produzione.',
        ),
        'stat_real': fields.float(
            'Q. reale', digits=(16, 3),
            help='E\' la quantità effettivamente uscita dalla produzione'
                 'comprendente anceh il calo di lavorazione, di solito'
                 'è minore uguale al valore nominale e dipende da quanta'
                 'acqua si perde nel processo.'),
        'stat_reused': fields.float(
            'Q. riusata', digits=(16, 3),
            help='Indica quanti prodotti sono stati reintrodotto nel processo'
                 'produttivo come semilavorati quindi la produzione effettiva'
                 'dovrà tenere conto che questi materiali non sono stati'
                 'venduti ma riutilizzati'),
        'stat_recycle': fields.float(
            'Q. fallata', digits=(16, 3),
            help='E\' la quantità di prodotto che è uscita non corretta quindi'
                 'non è vendibile, sarà riutilizzata nel processo produttivo'
                 'e non venduta direttamente. Il totale reale la comprende'
                 'quindi va tolta per avere il netto effettivo prodotto '
                 'per la vendita.',
        ),
        'stat_real_net': fields.function(
            '_get_real_net', method=True,
            type='float', string='Reale netto',
            help='Totale produzione netta usabile quindi togliendo il '
                 'materiale uscito fallato e i recuperi / semilavorati '
                 'riutilizzati nel processo produttivio '
                 'Q. reale - Q. riusata - Q. fallata',
            store=False),

        'stat_wc_id': fields.many2one(
            'mrp.workcenter', 'Linea'),
        }


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_objects': self.get_objects,
            })

    def get_objects(self, data=None, context=None):
        """ Load data for product status report
        """
        return self.pool.get('mrp.production').get_statistic_report_objects(
            self.cr, self.uid, data=data, context=context)
