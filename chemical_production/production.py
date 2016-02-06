# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2008-2013 Micronaet S.r.l.
#                  <http://www.micronaet.it>). All Rights Reserved
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


_chemical_state = [
   ('draft','Draft'),
   ('confirmed','Confirmed'),
   ('validated','Validated'),
   ('cancel','Cancel'),
]

class mrp_production_material(osv.osv):
    ''' Create object mrp.production.material seems the bom explosed on product
        quantity used as a model for bom list
    '''
    _name = "mrp.production.material"
    _description= "Production used material"
    _rec_name = "product_id"
    
    
    _columns = {
        'product_id':fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity', digits=(16, 2)),
        'uom_id': fields.related('product_id', 'uom_id', type = 'many2one', relation='product.uom', string='UOM'),
        'mrp_production_id':fields.many2one('mrp.production', 'Production order', ondelete="cascade", required=False),        # Link if used mrp.production object
        'prodlot_id': fields.many2one('stock.production.lot', 'Material lot', domain="[('product_id', '=', product_id)]"),
        'product_package': fields.many2one('product.packaging', 'Package', domain="[('product_id', '=', product_id)]"),
        'material_note': fields.text('Note'),
        
        'chemical_state': fields.related('mrp_production_id', 'chemical_state', type='selection', selection=(_chemical_state), string="Chemical state", store=False),
        'date_planned': fields.related('mrp_production_id', 'date_planned', type='datetime', string="Date planned", store=False),
        #'accounting_qty': fields.related('product_id','accounting_qty', type='float',  digits=(16, 3), string='Accounting Q.ty', store=False),
        'coal_production': fields.related('mrp_production_id','coal_production', type='boolean', string='Coal production'),
    }

class mrp_production_coal(osv.osv):
    ''' Create extra fields in mrp.production obj
    '''
    _name = "mrp.production"
    _inherit = "mrp.production"
    
    # -----------------
    # Utility function:
    # -----------------
    def _action_load_materials_from_bom(self, cr, uid, item_id, context = None):
        ''' Generic function called from create elements or button for load
            sub material according to BOM selected and quantity
            item_id is the id of mrp.production (integer not list)
            This material is only for see store status, non used for lavorations
        '''
        production_browse = self.browse(cr, uid, item_id, context=context)
        if not production_browse.bom_id and not production_browse.product_qty:
            return True # TODO raise error

        # Delete all elements:
        material_pool = self.pool.get('mrp.production.material')
        material_ids = material_pool.search(cr, uid, [('mrp_production_id', '=', item_id)], context=context)
        material_pool.unlink(cr, uid, material_ids, context=context)

        # Create elements from bom:
        for element in production_browse.bom_id.bom_lines:
            material_pool.create(cr, uid, {
                'product_id': element.product_id.id,
                'quantity': element.product_qty * production_browse.product_qty / production_browse.bom_id.product_qty if production_browse.bom_id.product_qty else 0.0,
                'uom_id': element.product_id.uom_id.id,
                'mrp_production_id': item_id,
            }, context = context)
        return True

    # TODO create chemical_analysis for end product created
    # ----------   
    # On change:
    # ----------
    # TODO on change for set up coal production (for mask)
    def bom_id_change(self, cr, uid, ids, bom_id, context=None):
        """ Override original function for setup also coal values
        """    
        if bom_id:
            res = super(mrp_production_coal, self).bom_id_change(cr, uid, ids, bom_id, context=context)
            bom_proxy = self.pool.get("mrp.bom").browse(cr, uid, bom_id, context=context)
            
            res['value']['linked_to_coal'] = bom_proxy.coal_bom_id.id if bom_proxy.coal_bom_id else False            
            return res
        return False    
    
    def product_id_change_no_coal(self, cr, uid, ids, product_id, context=None):
        """ Onyl for no coal production:
        """
        res = {
            'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False,
                'coal_production': False,
        }}
        if not product_id:
            return res
            
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_ids = bom_obj.search(cr, uid, [
            ('product_id', '=', product_id), ('bom_id', '=', False), ('only_coal', '=', False)], context=context) #_bom_find(cr, uid, product.id, product.uom_id and product.uom_id.id, [('only_coal','=',coal)])
        routing_id = False
        if bom_ids:
            bom_id = bom_ids[0]
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        else:
            bom_id = bom_ids[0]

        product_uom_id = product.uom_id and product.uom_id.id or False
        res['value']['product_uom'] = product_uom_id,
        res['value']['bom_id'] = bom_id,
        res['value']['routing_id'] = routing_id,
        return res

        
    # ----------------   
    # Workflow action:
    # ----------------   
    def production_chemical_draft(self, cr, uid, ids, context = None):
        ''' Draft production
        '''
        self.write(cr, uid, ids, {'chemical_state': 'draft', }, context = context)
        return True

    def production_chemical_confirmed(self, cr, uid, ids, context = None):
        ''' Confirmed production 
        '''
        # Test if there's coal bom to create (NOTE: not updatable!):
        if self.browse(cr, uid, ids, context=context)[0].bom_id.coal_bom_id:
            self.create_bom_coal(cr, uid, ids[0], context=context)
            
        # Mark as confirmed:
        self.write(cr, uid, ids, {'chemical_state': 'confirmed', }, context = context)
        return True

    def production_chemical_validated(self, cr, uid, ids, context = None):
        ''' Validated production
        '''
        self.write(cr, uid, ids, {'chemical_state': 'validated', }, context = context)
        return True

    def production_chemical_cancel(self, cr, uid, ids, context = None):
        ''' Cancel production
        '''
        self.write(cr, uid, ids, {'chemical_state': 'cancel', }, context = context)
        return True

    # ----------------
    # Button function:
    # ----------------
    def load_materials_from_bom(self, cr, uid, ids, context = None):
        ''' Change list of element according to weight and bom
        '''
        return self._action_load_materials_from_bom(cr, uid, ids[0], context=context)
        
    _columns = {
        'bom_material_ids': fields.one2many('mrp.production.material', 'mrp_production_id', 'Material lines', required=False),
        'prodlot_id': fields.many2one('stock.production.lot', 'Product lot', domain = "[('product_id','=',product_id)]"),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', ondelete="set null"),
        'production_note': fields.text('Production Note'),
        'chemical_state': fields.selection(_chemical_state, 'Chemical state', select = True, readonly = True),
        'coal_production': fields.boolean('Coal production', required = False,),
        # bad: (better put in stock.move for producut created)
        'product_package': fields.many2one('product.packaging', 'Package', domain="[('product_id', '=', product_id)]"),
    }

    _defaults = {
        'chemical_state': lambda *a: 'draft',
        'coal_production': lambda *a: True, # as default, usually set false in new form
    }
    
class mrp_bom(osv.osv):
    ''' Extra field for import
    '''    
    _name = 'mrp.bom'
    _inherit = 'mrp.bom'
    
    # -----------------
    # Scheduled action:
    # -----------------
    def import_production_bom(self, cr, uid, path, csv_file, context = None):
        ''' Import BOM from accounting program for production
        '''
        try:
            bom_pool = self.pool.get("mrp.bom")
            file_name = os.path.join(os.path.expanduser(path), csv_file)
            f = open(file_name, "r")
            old_bom_parent = False
        except:
            _logger.error("Error searching file for bom import")
            return False
        for line in f:
            try:
                csv_line = line.split(";")
                product_code = csv_line[0]
                material_code = csv_line[1]
                quantity = csv_line[2]
                
                product_id = 0   # TODO
                material_id = 0  # TODO
                
                # parent block:
                if not old_bom_parent or old_bom_parent != product_code: # level break
                    old_bom_parent = product_code
                    bom_parent_ids = bom_pool.search(cr, uid, [('bom_id','=',False),('imported','=',True),('product_id','=',product_id)], context = context)
                    if bom_parent_ids:
                        bom_parent_id = bom_parent_ids[0]                    
                    else:
                        bom_parent_id = bom_pool.create(cr, uid, {
                            'bom_id': False,
                            'imported': True,
                            'product_id': product_id,
                            'quantity': 1.0,           # TODO verify if all product total is 1.0
                        }, context = context)
                    remove_line_ids = bom_pool.search(cr, uid, [('bom_id', '=', bom_parent_id)], context = context)
                    bom_pool.unlink(cr, uid, remove_line_ids) # remove all lined before create
            except:
                _logger.info('Jumped bom line!')
            # child block:
            bom_pool.create(cr, uid, {
                'bom_id': bom_parent_id,
                'product_id': product_id,
                'quantity': quantity,
            }, context = context)
        f.close()
        return True

    _columns = {
        'imported': fields.boolean('Imported'),        
    }
    _defaults = {
        'imported': lambda *x: False,        
    }

class stock_production_lot(osv.osv):
    """ Update lot with extra info (and totals)
    """
    _name = 'stock.production.lot'
    _inherit = 'stock.production.lot'

    def _stock_available_chemical_function(self, cr, uid, ids, field=None, args=False, context=None):
        ''' Total of availability stock in + stock out + production - material
        '''
        res = {}
        for lot in self.browse(cr, uid, ids, context=context):
            # from stock.move (load):            
            cr.execute("SELECT sum(sm.product_qty) FROM stock_move sm, stock_picking sp \
                        WHERE sm.picking_id=sp.id AND sp.type='in' AND sm.prodlot_id = %s AND sm.state='done'" % (lot.id,))
            res[lot.id] = cr.fetchone()[0] or 0.0

            # from stock.move (unload):
            cr.execute("SELECT -sum(sm.product_qty) FROM stock_move sm, stock_picking sp \
                        WHERE sm.picking_id=sp.id AND sp.type='out' AND sm.prodlot_id = %s AND sm.state='done'" % (lot.id,))
            res[lot.id] += cr.fetchone()[0] or 0.0

            # from mrp.production (load product):
            cr.execute("SELECT sum(product_qty) FROM mrp_production \
                        WHERE prodlot_id = %s AND coal_production='f' AND chemical_state in ('confirmed','validated')" % (lot.id,))
            res[lot.id] += cr.fetchone()[0] or 0.0

            # from mrp.production.material (unload material):
            cr.execute("SELECT -sum(mpm.quantity) FROM mrp_production_material mpm, mrp_production mp \
                        WHERE mpm.mrp_production_id = mp.id AND mp.coal_production='f' AND mpm.prodlot_id = %s AND mp.chemical_state in ('confirmed','validated')" % (lot.id,))
            res[lot.id] += cr.fetchone()[0] or 0.0
        return res

    _columns = {
        'production_end_product_ids': fields.one2many('mrp.production', 'prodlot_id', 'Production end product', required=False, domain=[('coal_production','=',True)]),
        'production_material_ids': fields.one2many('mrp.production.material', 'prodlot_id', 'Production material', required=False, domain=[('coal_production','=',True)]),
        # Function: 
        'stock_available_chemical': fields.function(_stock_available_chemical_function, method=True, type='float', string='Stock available', store=False),
    }

class product_product(osv.osv):
    """ Extra field for product
    """
    _name = 'product.product'
    _inherit = 'product.product'
    
    _columns = {
        'lot_ids':fields.one2many('stock.production.lot', 'product_id', 'Lots', required=False),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
