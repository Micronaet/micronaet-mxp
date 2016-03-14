# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) 
#    
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
from openerp.osv import osv, fields
from datetime import datetime
from openerp.tools.translate import _

version_list = [
    ('percentage_supplier', 'Supplier'), 
    ('percentage', 'Internal'),
    ('percentage_lab1', 'Laboratory 1'),
    ('percentage_lab2', 'Laboratory 2'),
    ('percentage_lab3', 'Laboratory 3'),
    ]

class SaleOrderLineAnalysisWizard(osv.osv_memory):
    ''' Analysis element for quotation (usually one for line)
    '''    
    _name = 'sale.order.line.analysis.wizard'
    _description = 'Chemical element wizard'
            
    separator = ': ' # for title to value (chemical elements)
                
    # Button event:
    def save_wizard_data(self, cr, uid, ids, context=None):
        ''' Save data on line
        '''
        sol_pool = self.pool.get('sale.order.line')
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        
        sol_id = wiz_proxy.line_id.id
        sol_pool.write(cr, uid, sol_id, {
            #'line_id': ids[0],
            'lot_id': wiz_proxy.lot_id.id or False,
            #'product_id': line_proxy.product_id.id or False,
            'price_telquel': wiz_proxy.price_telquel,
            'analysis_id': wiz_proxy.analysis_id.id or False,            

            'price_telquel': wiz_proxy.price_telquel or False,
            'price_percentage': wiz_proxy.price_percentage or False,
            'analysis_text': wiz_proxy.analysis_text or False,
            'specific_text': wiz_proxy.specific_text or False,
            'only_chemical': wiz_proxy.only_chemical or False,
            'standard_analysis': wiz_proxy.standard_analysis or False,
            'version': wiz_proxy.version or False,
            }, context=context)
        return True
        
    # onchange events:
    def onchange_lot(self, cr, uid, ids, lot_id, context=None):
        ''' Change lot element
            Reset analysis, versione text
        '''
        res = {'value': {}}

        res['value']['analysis_id'] = False    # reset analysis
        res['value']['version'] = 'percentage'   # reset version
        res['value']['analysis_text'] = False  # reset text

        if lot_id:
            chemical_pool = self.pool.get('chemical.analysis')
            chemical_ids = chemical_pool.search(cr, uid, [
                ('prodlot_id', '=', lot_id)], context = context)
            if len(chemical_ids) == 1:
                res['value']['analysis_id'] = chemical_ids[0]
        return res
        
    def onchange_analysis(self, cr, uid, ids, analysis_id, version, 
            only_chemical, lot_id, standard_analysis, context=None):
        ''' Search in analysis selected and generate a text for analysis 
            and for specific
        '''
        # on change results:
        res = {'value': {'analysis_text': '', 'specific_text': ''}}

        if not ids:
            return res
            
        # current record:
        chemical_line_proxy = self.browse(cr, uid, ids, context=context)[0] 
        
        product_id = chemical_line_proxy.product_id and \
            chemical_line_proxy.product_id.id
        if not product_id:
            return res

        try: # Change for get element from order:
            partner_id = chemical_line_proxy.line_id.order_id.partner_id.id 
            #context.get('partner_id', False)
        except:
            partner_id = False    
            
        if partner_id: 
            analysis_pool = self.pool.get('chemical.analysis.partner')
            analysis_ids = analysis_pool.search(cr, uid, [
                ('name','=',product_id), 
                ('partner_id', '=', partner_id), 
                ('is_active', '=', True)], order='date desc', context=context)
            partner_analysis_proxy = analysis_pool.browse(
                cr, uid, analysis_ids, context=context)
        else:
            partner_analysis_proxy = False # no test on customer specs

        # ----------------------------------------------------------------------
        #                           Model of chemical analysis
        # ----------------------------------------------------------------------
        if standard_analysis:  # take model elements        
            # ----------------------------
            # Load list of model elements:
            # ----------------------------
            model_id = chemical_line_proxy.product_id.model_id and \
                chemical_line_proxy.product_id.model_id.id
            if not model_id:
                return res
                
            model_line_pool = self.pool.get('product.product.analysis.line')
            model_line_ids = model_line_pool.search(cr, uid, [
                ('model_id', '=', model_id)], context=context)                
            text = ''
            test_element = {}            
            for line in model_line_pool.browse(
                    cr, uid, model_line_ids, context=context):
                test_element[line.name.id] = (
                    line.valutation, line.min, line.max)
                # TODO get max value!
                text += "%s%s %s\n" % (
                    line.name.symbol if only_chemical else line.name.name, 
                    self.separator,
                    "%s%s%s%s%s%s%s" % (   # 3 case: >5%   5% - 6%   <7%
                        line.valutation if line.valutation == '>' else "",
                        line.min if line.valutation in ('>','=') else "",
                        "%" if line.valutation in ('>','=') else "",
                        " - " if line.valutation == "=" else "",
                        line.valutation if line.valutation == '<' else "",
                        line.max if line.valutation in ('<','=') else "",                            
                        "%" if line.valutation in ('<','=') else "",
                    ))
            res['value']['analysis_text'] = text.strip()
            # reset other values:
            res['value']['lot_id'] = False
            res['value']['analysis_id'] = False
            res['value']['version'] = False

            # ------------------------------------
            # Load customer specs test with model:
            # ------------------------------------    
            if partner_analysis_proxy:
                for analysis in partner_analysis_proxy:
                    res['value']['specific_text'] += _(
                        'Analysis dated: %s (vers. %s)\n') % (
                            analysis.date,
                            analysis.version,
                        )
                    #actual_value = element.__getattr__(version) or 0.0
                    for line in analysis.analysis_line_ids:
                        from_value = line.__getattr__('from') or 0.0
                        to_value = line.to or 100

                        if line.name.id in test_element:
                            valutation_model, from_model, to_model = \
                                test_element[line.name.id]
                            
                            if valutation_model == "=":
                                if from_model >= from_value and \
                                        to_model <= to_value:
                                    error = ''
                                else:    
                                    error = _(' *** Out of range!')
                            elif valutation_model == ">":   # min 
                                if from_model >= from_value:
                                    error = ''
                                else:    
                                    error = _(' *** Out of range!')
                            else: # >   max 
                                if to_model <= to_value:
                                    error = ''
                                else:    
                                    error = _(' *** Out of range!')
                        else:
                            error = _(' *** Element not present!')
                            
                        res['value']['specific_text'] += \
                            '%s: [%s%s - %s%s] %s\n' % (
                                line.name.symbol if only_chemical else \
                                    line.name.name,
                                from_value, '%', to_value, '%', error,
                                )
                
        # ----------------------------------------------------------------------
        #                             Chemical analysis
        # ----------------------------------------------------------------------
        else: # take elements in analysis compiled
            if analysis_id and version: # else delete analysis_text
                # ----------------------
                # Load list of elements:
                # ----------------------
                analysis_proxy = self.pool.get('chemical.analysis').browse(
                    cr, uid, analysis_id, context=context)
                text = ''
                test_element = {}
                for element in analysis_proxy.line_ids:
                    test_element[element.name.id] = element.__getattr__(
                        version)
                    text += '%s%s%s%s\n' % (
                        element.name.symbol if only_chemical else \
                            element.name.name, 
                        self.separator,
                        element.__getattr__(version) or 0.0, 
                        '%',
                    )
                res['value']['analysis_text'] = text.strip()

                # --------------------
                # Load customer specs:
                # --------------------                    
                for analysis in partner_analysis_proxy:
                    res['value']['specific_text'] += _(
                        'Analysis dated: %s (vers. %s)\n') % (
                            analysis.date,
                            analysis.version,
                    )
                    actual_value = element.__getattr__(version) or 0.0
                    for line in analysis.analysis_line_ids:
                        from_value = line.__getattr__('from') or 0.0
                        to_value = line.to or 100
                        if line.name.id in test_element:
                            if actual_value >= from_value and actual_value <= \
                                    to_value:
                                error = ''
                            else:
                                error = _('*** Out of range')
                        else:
                            error = _('*** Element not present')
                        res['value']['specific_text'] += _(
                            '%s: from %s%s to %s%s %s\n') % (
                                line.name.symbol if only_chemical else \
                                    line.name.name,
                                from_value, '%', to_value, '%', error)
        return res

    _columns = {
        'price_telquel': fields.boolean('Price telquel', 
            help='Tel Quel price'),
        'price_perentage': fields.float('Based perc.', digits=(16, 3), 
            help='If not tel quel price this is based percentage'),     

        'only_chemical': fields.boolean(
            'Only chemical', help = 'Only chemical symbol in analysis text'),
        'standard_analysis': fields.boolean(
            'Standard analysis', 
            help='Don\'t take analysis values, only model element indication'),
        'line_id': fields.many2one(
            'sale.order.line','Order line', required = True, readonly = False, 
            help = "Quotation line linked to this analysys"),
        #'order_id': fields.many2one('sale.order', 'Order', required=True, 
        #    readonly = False), 
        'product_id': fields.related('line_id', 'product_id', type='many2one', 
            relation='product.product', string='Product', store = True),
        'lot_id': fields.many2one(
            'stock.production.lot', 'Lot', 
            help='Lot selected for this quotation'),
        #'xls_qty': fields.related('lot_id', 'xls_qty', type='float', 
        #string='Q. disp', digit=(16,3),store=False),
        
        'analysis_id': fields.many2one('chemical.analysis', 'Analysis sheet', 
            help='Analysis selected for print in quotation'),
        'version': fields.selection(version_list, 'Version', 
            help='Choose which one of the analysis use on quotation'),
        'analysis_text': fields.text('Analysis', 
            help='Text-values from analysis but let user changes'),
        'specific_text': fields.text('Specific', 
            help='Add specific text of product'),
        }
    
    _defaults = {
        # TODO extra defaults to load (tranform all): <<< from sale order line
        # analysis_text
        # specific_text
        #'only_chemical': 
        #'standard_analysis':
        #'version':
        }
    
class sale_order_line(osv.osv):
    ''' Add relation fields to parent sale.order
    '''
    _inherit = 'sale.order.line'

    #button events:
    def need_analysis(self, cr, uid, ids, context=None):
        '''        
        '''
        self.write(cr, uid, ids, {
            'analysis_required': False,
            }, context=context)
            
        line_proxy = self.browse(cr, uid, ids, context=context)[0]    

        # Open wizard:
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(cr, uid,             
            'chemical_analysis_quotation', 
            'view_sale_order_line_analysis_wizard_form')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Analysis detail:'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line.analysis.wizard',
            'view_id': view_id, # False
            #'views': [(False, 'tree'), (False, 'form')],
            #'domain': [],
            'context': {
                'default_line_id': ids[0],
                'default_lot_id': line_proxy.lot_id.id or False,
                'default_product_id': line_proxy.product_id.id or False,
                'default_price_telquel': line_proxy.price_telquel,
                'default_analysis_id': line_proxy.analysis_id.id or False,

                'default_price_telquel': line_proxy.price_telquel or False,
                'default_price_percentage': line_proxy.price_percentage or False,
                'default_analysis_text': line_proxy.analysis_text or False,
                'default_specific_text': line_proxy.specific_text or False,
                'default_only_chemical': line_proxy.only_chemical or False,
                'default_standard_analysis': line_proxy.standard_analysis or False,
                'default_version': line_proxy.version or False,
                },
            'target': 'new',
            'nodestroy': False,
            }
        
        return True
    def remove_analysis(self, cr, uid, ids, context=None):
        ''' 
        '''
        self.write(cr, uid, ids, {
            'analysis_required': False,
            }, context=context)
        return True
        
    _columns = {
        'analysis_required': fields.boolean('Anal. req.', 
            help='If checked the analysis is printed in the quotation'),

        # From wizard:        
        'price_telquel': fields.boolean('Price telquel', 
            help='Tel Quel price'),
        'price_percentage': fields.float('Based perc.', digits=(16, 3), 
            help='If not tel quel price this is based percentage'),     

        'only_chemical': fields.boolean(
            'Only chemical', help = 'Only chemical symbol in analysis text'),
        'standard_analysis': fields.boolean(
            'Standard analysis', 
            help='Don\'t take analysis values, only model element indication'),
        'lot_id': fields.many2one(
            'stock.production.lot', 'Lot', 
            help='Lot selected for this quotation'),
        'analysis_id': fields.many2one('chemical.analysis', 'Analysis sheet', 
            help='Analysis selected for print in quotation',),
        'version': fields.selection(version_list, 'Version', 
            help='Choose which one of the analysis use on quotation'),
        'analysis_text': fields.text('Analysis', 
            help='Text and values from analysis, let user changes'),
        'specific_text': fields.text('Specific', 
            help="Add specific text of product"),
        }

    _defaults = {
        'analysis_required': lambda *x: False,

        # Wizard defaults:
        'only_chemical': lambda *x: True,
        'standard_analysis': lambda *x: False,
        'version': lambda *x: 'percentage',
        }

class res_users(osv.osv):
    ''' Add extra field
    '''
    _inherit = 'res.users'

    _columns = {
        'offer_ccn_id': fields.many2one('res.users', 'Offer CCN user'),
        }    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
