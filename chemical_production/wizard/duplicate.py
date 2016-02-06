# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2008-2013 Micronaet S.r.l.
#                  <http://www.micronaet.it>). All Rights Reserved
#    Thanks to:
#           OpenCode [Andrea Cometa Addons] for routine of send mail
#           integrated with OpenERP mail system
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
import logging, sys, os        
_logger = logging.getLogger(__name__)


# -----------------
# Utility function:
# -----------------
def get_view_id(self, cr, uid, view_name, view_type, context=None):
    ''' Search view and return ID (module.view_name format)
        @view_name: view name format: module.view_name
        @view_type: type of view (form, tree...)
        @return: (ID of view of False, type of view)
    '''
    
    view_element = view_name.split(".")
    view_id = False
    if len(view_element) == 2:
       model_id = self.pool.get('ir.model.data').search(cr, uid, [
           ('model', '=', 'ir.ui.view'),
           ('module', '=', view_element[0]),
           ('name', '=', view_element[1])], context=context)
       if model_id:
          view_id = self.pool.get('ir.model.data').read(cr, uid, model_id, context=context)[0]['res_id']
    return (view_id, view_type)
    
class mrp_production_coal_duplicate_wizard(osv.osv):
    ''' Duplicate prodution wizard:
    '''
    _name = "mrp.production.duplicate.wizard"
    _description= "Duplicate production wizard"
    
    # -------------
    # Button event:
    # -------------
    def button_duplicate_action(self, cr, uid, ids, context=None):
        ''' Duplicate current production order and go in new one
        '''
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]

        mrp_from_id = context.get('active_id', False)
        if not mrp_from_id:
            return False
        production_pool = self.pool.get("mrp.production")    
        production_proxy = production_pool.browse(cr, uid, mrp_from_id, context=context)
        new_id = production_pool.create(cr, uid, {
            'product_id': production_proxy.product_id.id,
            'bom_id': production_proxy.bom_id.id,
            'user_id': production_proxy.user_id.id,
            'product_qty': wiz_proxy.quantity,
            'product_uom': production_proxy.product_uom.id,
            'prodlot_id': production_proxy.prodlot_id.id,
            'date_planned': wiz_proxy.date_planned,
            'workcenter_id': wiz_proxy.workcenter_id and wiz_proxy.workcenter_id.id,
            'linked_to_coal': production_proxy.linked_to_coal,
            #'coal_production_id': production_proxy.coal_production_id and production_proxy.coal_production_id.id,           
        }, context=context)
        if wiz_proxy.from_bom:
            # Load material calling button event:
            production_pool.load_materials_from_bom(cr, uid, [new_id], context=context)
        else: # TODO from actual production
            material_pool = self.pool.get('mrp.production.material')
            rate = wiz_proxy.quantity / production_proxy.product_qty
            for element in production_proxy.bom_material_ids:
                # production_browse = self.browse(cr, uid, item_id, context=context)
                data = {
                    'product_id': element.product_id.id,
                    'quantity': element.quantity * rate,
                    'uom_id': element.product_id.uom_id.id,
                    'mrp_production_id': new_id,
                    'prodlot_id': element.prodlot_id.id if element.prodlot_id else False,
                }
                material_pool.create(cr, uid, data, context=context)
        
        # Return action for open new ID     
        #chemical_production.view_mrp_production_not_coal_form_view
        #search_id = get_view_id(self, cr, uid, 'chemical_production.view_mrp_production_search_no_coal_view', 'search', context=None)[0]
        views = [
            get_view_id(self, cr, uid, 'chemical_production.view_mrp_production_not_coal_form_view', 'form', context=None),
            #get_view_id(self, cr, uid, 'chemical_production.view_mrp_production_tree_no_coal_view', 'tree', context=None),
            #get_view_id(self, cr, uid, 'chemical_production.mrp_production_calendar_view_extra_coal', 'calendar', context=None),
        ]
        return {
            'view_type': 'form',
            'view_mode': 'tree,form,calendar',
            'res_model': 'mrp.production',
            #'domain': [('id', 'in', new_id)],
            'res_id': new_id, 
            'type': 'ir.actions.act_window',
            'target': 'new',
            'views': views,
            'view_id': views[0][0],
            #'search_view_id': search_id,
        }
        
    _columns = {
        'quantity': fields.float('Quantity', required=True, digits=(16, 2), help="Quantity fo new production"),
        'uom_id': fields.many2one('product.uom', 'UOM', required=False, help="Defaulf UOM"),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=False, ),
        'date_planned': fields.datetime('Date planned', required=True),
        'from_bom': fields.boolean('From BOM', required=False, help='Load from BOM (instead of load current elements, also lot informations)'),
        #'with_lot': fields.boolean('With lot', required=False, help='Load from BOM also lot informations'),
    }
    
    _defaults = {
        'date_planned': lambda *x: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
        'from_bom': True,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
