##############################################################################
#
# Copyright (c) 2008-2010 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            # TODO no more used
            'get_analysis_from_move': self.get_analysis_from_move, 
            'separator': self.get_separator,
        })
    def get_separator(self, ):
        ''' Get separator used for chemical elements
        '''
        return self.pool.get('sale.order.line.analysis.wizard').separator or ":"

    def get_analysis_from_move(self, move_id):
        ''' Return a browse object linked to move_id element with analysis
        '''
        analysis_pool = self.pool.get('sale.order.line.analysis')
        analysis_ids = analysis_pool.search(self.cr, self.uid, [('line_id', '=', move_id)])
        if analysis_ids and len(analysis_ids) == 1:
            try:
                return analysis_pool.browse(self.cr, self.uid, analysis_ids)[0].analysis_text.split('\n')
            except:
                return ""
        else:
            return ""
