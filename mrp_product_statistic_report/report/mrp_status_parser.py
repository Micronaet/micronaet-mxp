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


class ResCompany(orm.Model):
    """ Model name: MrpProduction
    """
    _inherit = 'res.company'

    _columns = {
        'setup_stat_medium_period': fields.integer(
            'GG. m(x) MRP prod.',
            help='Giorni da considerare per fare il calcolo medio delle '
                 'produzioni per prodotto (partendo dalle CL del periodo)'
                 'Utilizzato anche per vedere le medie di vendita da DDT')
    }

    _defaults = {
        'setup_stat_medium_period': lambda *x: 180,
    }


class ProductProduct(orm.Model):
    """ Model name: MrpProduction
    """
    _inherit = 'product.product'

    _columns = {
        'stat_medium_ddt_period': fields.float(
            'M(x) DDT del periodo', digits=(16, 3),
            help='E\' la quantità media del periodo selezionato nei parametri'
                 '(abitualmente 180 gg) calcolata prendendo tutti gli scarichi'
                 ' per DDT e facendo la media giornaliera.',
        ),
        'stat_medium_period': fields.float(
            'M(x) MRP del periodo', digits=(16, 3),
            help='E\' la quantità media del periodo selezionato nei parametri'
                 '(abitualmente 180 gg) calcolata prendendo tutti i carichi'
                 'di produzione per prodotto e facendo la media giornaliera. ',
        ),

        'mrp_medium_yield': fields.float('Rendimento medio', digits=(16, 3)),
        'semi_product': fields.boolean(
            'Semilavorato',
            help='Indica che il prodotto è spesso utlizzato o creato per '
                 'essere reimmesso nel processo produttivo. Questa indicazione'
                 'serve solamente ai fini statistici per avere due totali'
                 'differenti tra semilavorati e prodotti non venduti')
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
        user_pool = self.pool.get('res.users')

        # Setup range for product medium:
        user = user_pool.browse(cr, uid, uid, context=context)
        company = user.company_id
        setup_stat_medium_period = company.setup_stat_medium_period or 180
        now = datetime.now()
        from_dt = now - timedelta(days=setup_stat_medium_period)
        from_date = from_dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
        _logger.warning('Medium MRP product periodo from %s' % from_date)

        # ---------------------------------------------------------------------
        # Update DDT sell statistics:
        # ---------------------------------------------------------------------
        ddt_pool = self.pool.get('stock.ddt')
        ddt_ids = ddt_pool.search(cr, uid, [
            ('state', '=', 'done'),
            ('date', '>=', from_date),
        ], context=context)
        ddt_data = {}
        for ddt in ddt_pool.browse(cr, uid, ddt_ids, context=context):
            for line in ddt.line_ids:
                product_id = line.product_id.id
                quantity = line.product_uom_qty
                if product_id not in ddt_data:
                    ddt_data[product_id] = 0.0
                ddt_data[product_id] += quantity
        pdb.set_trace()
        for product_id in ddt_data:
            stat_medium_ddt_period = \
                ddt_data[product_id] / setup_stat_medium_period
            product_pool.write(cr, uid, [product_id], {
                'stat_medium_ddt_period': stat_medium_ddt_period,
            }, context=context)

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
            'Documento', 'Teorica', 'Effettiva', 'Recupero',
            'Riuso recuperi', 'Riuso pulizia', 'Riuso inutilizzati',
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

        detail_move = {
            'reused': [],
        }
        res = {}
        mrp_ids = self.search(cr, uid, domain, context=context)
        for mrp in self.browse(cr, uid, mrp_ids, context=context):
            # Old way:
            # mrp_for_clean = mrp.load_ids and all(
            #    [l.recycle for l in mrp.load_ids])
            mrp_for_clean = mrp.mrp_for_clean

            counter_mrp += 1
            product = mrp.product_id
            product_code = product.default_code or ''
            mrp_name = mrp.name

            # Check total:
            # Raw, final product, recycle, reused total:
            mrp_in = mrp_out = mrp_recycle = 0.0
            mrp_w_reused = mrp_c_reused = mrp_p_reused = mrp_s_reused = 0

            if product not in res:
                res[product] = [
                    # theoric, real, recycle,
                    0.0, 0.0, 0.0,
                    # reused: waste, clean, unsold, semiproduct
                    0.0, 0.0, 0.0, 0.0,

                    # Medium MRP for product,
                    0.0,  # Total KG produced (after calc medium)
                ]

            # Job Theoric:
            wc_line = '?'
            wc_id = False
            for wc in mrp.workcenter_lines:  # Job
                if wc.state == 'cancel':
                    continue

                counter += 1
                date_ref = wc.real_date_planned or ''
                wc_id = wc.workcenter_id.id or False
                wc_name = wc.name
                wc_line = wc.workcenter_id.name

                # Total material prime (MP)
                material_qty = reused_w_qty = reused_c_qty = reused_p_qty = \
                    reused_s_qty = 0.0
                for move in wc.bom_material_ids:
                    move_qty = move.quantity
                    material_qty += move_qty  # all used goes in total material

                    # ---------------------------------------------------------
                    # Reused parse:
                    # ---------------------------------------------------------
                    material = move.product_id
                    semi_product = material.semi_product

                    material_code = material.default_code or ''
                    first_char = material_code[0].upper()
                    reused_mode = ''
                    if material_code == 'ORIC':
                        _logger.warning('ORIC not used')

                    elif mrp_for_clean:  # all job goes in reused clean!
                        reused_mode = 'pulizia'
                        reused_c_qty += move_qty
                        # mrp_reused['clean'] += reused_c_qty

                    elif first_char == 'R':  # reused waste product:
                        reused_mode = 'recupero'
                        reused_w_qty += move_qty
                        # mrp_reused['waste'] += reused_w_qty

                    elif semi_product:
                        reused_mode = 'semilavorato'
                        reused_s_qty += move_qty

                    elif first_char and first_char not in 'ABVR':
                        reused_mode = 'invenduti'
                        reused_p_qty += move_qty

                    if reused_mode:  # for log:
                        detail_move['reused'].append((
                            date_ref,
                            mrp_name,
                            product_code,
                            wc_name,
                            wc_line,
                            material_code,
                            move_qty,
                            reused_mode,
                        ))

                # -------------------------------------------------------------
                # Total for product statistics:
                # -------------------------------------------------------------
                res[product][0] += material_qty
                res[product][3] += reused_w_qty
                res[product][4] += reused_c_qty
                res[product][5] += reused_p_qty
                res[product][6] += reused_s_qty

                # -------------------------------------------------------------
                # Total for MRP (once ad the end o WC loop):
                # -------------------------------------------------------------
                mrp_in += material_qty
                mrp_w_reused += reused_w_qty
                mrp_c_reused += reused_c_qty
                mrp_p_reused += reused_p_qty
                mrp_s_reused += reused_s_qty

                # -------------------------------------------------------------
                # LOG XLS line:
                # -------------------------------------------------------------
                write_xls(WS, [
                    wc_line,  # Line
                    date_ref[:4],  # Year
                    date_ref[:7],  # Period
                    date_ref,  # Date
                    product.default_code,  # Product
                    mrp.name,  # MRP
                    wc.name,  # Document
                    material_qty,  # Q. theoric
                    0.0,  # Q. real
                    0.0,  # Recycle
                    0.0,  # Reused waste
                    0.0,  # Reused clean
                    0.0,  # Reused product
                    0.0,  # Reused semiproduct
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

                # >> MRP Product total CL for m(x):
                if date_ref and date_ref >= from_date:  # Only in range period
                    res[product][7] += cl.product_qty

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

                    # Reused:
                    0.0,  # Reused waste
                    0.0,  # Reused clean
                    0.0,  # Reused product
                    0.0,  # Reused semiproduct
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
                mrp_w_reused,  # Reused waste
                mrp_c_reused,  # Reused clean
                mrp_p_reused,  # Reused product
                mrp_s_reused,  # Reused semiproduct

                mrp_out / mrp_in * 100.0 if mrp_in else 0.0,
                mrp_recycle / mrp_in * 100.0 if mrp_in else 0.0,  # todo check!
                'X' if mrp_in < mrp_out else '',
                ], counter_mrp)

            if with_history:
                self.write(cr, uid, mrp.id, {
                    'stat_theoric': mrp_in,
                    'stat_real': mrp_out,
                    'stat_recycle': mrp_recycle,
                    'stat_reused_waste': mrp_w_reused,
                    'stat_reused_clean': mrp_c_reused,
                    'stat_reused_unused': mrp_p_reused,
                    'stat_reused_semiproduct': mrp_s_reused,
                    'stat_wc_id': wc_id,
                    'stat_real_net': (  # todo all removed?
                        mrp_out - mrp_w_reused - mrp_c_reused -
                        mrp_p_reused - mrp_s_reused - mrp_recycle),
                }, context=context)

        # Close WB:
        try:
            WB.close()
        except:
            _logger.error('Error closing WB: %s' % (sys.exc_info(), ))

        # Write statistic for check:
        reused_f = open('/tmp/reused.csv', 'w')
        _logger.warning('Write log file')
        for line in detail_move['reused']:
            reused_f.write(
                '%s|%s|%s|%s|%s|%s|%s|%s\n' % line
            )
            # mrp_name, product_code, wc_name, wc_line, material_code,
            # move.quantity
        reused_f.close()

        # Sort order
        records = []
        _logger.warning('Write medium in product')
        for record in sorted(res, key=lambda x: x.default_code):
            data = res[record]
            records.append((record, data))

            # Product:
            if with_history and data[0]:
                mrp_medium_yield = 100.0 * data[1] / data[0]
                stat_medium_period = data[7] / setup_stat_medium_period

                product_pool.write(cr, uid, record.id, {
                    'mrp_medium_yield': mrp_medium_yield,
                    'stat_medium_period': stat_medium_period,
                    }, context=context)
        return records

    _columns = {
        'stat_theoric': fields.float(
            'Q. nominale', digits=(16, 3),
            help='Q. indicata sulla distinta di produzione, è il totale'
                 ' teorico per il quale si sta facendo la produzione (può'
                 ' capitare che nel processo produttivo vengano aggiunte poi'
                 ' dei recuperi extra che portano a produrre più di quello'
                 ' pianificato. Se è minore è richiesto una correzione sulla'
                 ' testata della produzione.',
        ),
        'stat_real': fields.float(
            'Q. reale', digits=(16, 3),
            help='E\' la quantità effettivamente uscita dalla produzione'
                 ' comprendente anceh il calo di lavorazione, di solito'
                 ' è minore uguale al valore nominale e dipende da quanta'
                 ' acqua si perde nel processo.'),
        'stat_reused_waste': fields.float(
            'Riuso (recupero)', digits=(16, 3),
            help='Indica quanti prodotti di recupero (generati da lavorazioni'
                 ' margate come fallate) sono stati reintrodotti nel processo'
                 ' produttivo come semilavorati quindi la produzione effettiva'
                 ' dovrà tenere conto che questi materiali non sono stati'
                 ' venduti ma riutilizzati'),
        'stat_reused_clean': fields.float(
            'Riuso (pulizia)', digits=(16, 3),
            help='Indica quanti prodotti scaturidi da lavorazioni di pulizia'
                 ' sono stati reintrodotti nel processo'
                 ' produttivo come semilavorati quindi la produzione effettiva'
                 ' dovrà tenere conto che questi materiali sono stati'
                 ' riutilizzati'),
        'stat_reused_unused': fields.float(
            'Riuso (invenduti)', digits=(16, 3),
            help='Indica quanti prodotti invenduti (prodotto buono) '
                 'sono stati reintrodotti nel processo produttivo come '
                 'semilavorati quindi la produzione effettiva '
                 'dovrà tenere conto che questi materiali non sono stati '
                 'venduti ma riutilizzati.'),
        'stat_reused_semiproduct': fields.float(
            'Riuso (semilavorato)', digits=(16, 3),
            help='Indica quanti prodotti semilavorati prodotto fatto per '
                 'riuso) sono stati reintrodotti nel processo produttivo come '
                 'semilavorati quindi la produzione effettiva '
                 'dovrà tenere conto che questi materiali non sono stati '
                 'venduti ma riutilizzati.'),
        'stat_recycle': fields.float(
            'Q. fallata', digits=(16, 3),
            help='E\' la quantità di prodotto che è uscita non corretta quindi'
                 ' non è vendibile, sarà riutilizzata nel processo produttivo'
                 ' e non venduta direttamente. Il totale reale la comprende'
                 ' quindi va tolta per avere il netto effettivo prodotto'
                 ' per la vendita.',
        ),
        'stat_real_net': fields.float(
            'Q. reale netta', digits=(16, 3),
            help='Totale produzione netta usabile quindi togliendo il'
                 ' materiale uscito fallato e i recuperi / semilavorati'
                 ' riutilizzati nel processo produttivio'
                 ' Q. reale - Q. riusata - Q. fallata',
            ),

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
