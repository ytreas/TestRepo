from odoo import http
from odoo.http import request
import json

class HrPayrollStructureController(http.Controller):

    @http.route('/api/payroll/salary_structures', type='http', auth='public', cors="*", methods=['GET'], csrf=False)
    def get_payroll_structures(self, **kwargs):
        # Fetch payroll structures
        structures = request.env['hr.payroll.structure'].sudo().search([])
        
        # Prepare payroll structure data
        structure_data = []
        for structure in structures:
            structure_data.append({
                'id': structure.id,
                'name': structure.name,
                'code': structure.code,
                'company_id': structure.company_id.name if structure.company_id else None,
                'note': structure.note,
                'parent_id': structure.parent_id.name if structure.parent_id else None,
                'children_ids': [child.name for child in structure.children_ids] if structure.children_ids else [],
                'rule_ids': [rule.id for rule in structure.rule_ids] if structure.rule_ids else []
            })

        # Fetch salary rules
        rules = request.env['hr.salary.rule'].sudo().search([])

        # Prepare salary rule data
        rule_data = []
        for rule in rules:
            rule_data.append({
                'id': rule.id,
                'name': rule.name,
                'code': rule.code,
                'category_id': rule.category_id.name if rule.category_id else None,
                'sequence': rule.sequence,
                'register_id': rule.register_id.name if rule.register_id else None
            })

        # Return combined data as a JSON response with structures on top
        return request.make_response(
            json.dumps({
                'structures': structure_data,
                'rules': rule_data
            }, indent=4),
            headers={'Content-Type': 'application/json'}
        )
# testing