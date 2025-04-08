
from odoo import models, fields, api
from datetime import datetime
from datetime import time, datetime, timedelta
from pytz import timezone
from odoo.exceptions import ValidationError
import nepali_datetime
from collections import defaultdict
import json
import urllib.parse

class VehicleNumberWizard(models.TransientModel):
    _name = 'vehicle.number.wizard'
    _description = 'Vehicle Number Wizard'

    vehicle_company = fields.Many2one('custom.vehicle.company', string='Vehicle Company')
    # new_number = fields.Char(string='New Vehicle Number', required=True)
    date = fields.Date(string="Date",default=fields.Date.today)

    def print_report(self):
        # print("Full context in wizard:", self.env.context)
        selected_ids = self.env.context.get('default_selected_ids', [])
      
        date_bs = nepali_datetime.date.from_datetime_date(self.date).strftime('%Y-%m-%d')
        company_name = self.env.user.company_id.name
        vehicle_company_name = self.vehicle_company.company_name

        # print("#########################",company_name)
        prepared_data = {
            'two_wheeler': {},
            'four_wheeler': {},
            'heavy':{},
            'old':{},
            'electric':{},
            'pradesh':{},
        }
        # records = self.env['vehicle.number'].search([])
        if selected_ids:
            records = self.env['vehicle.number'].search([('id', 'in', selected_ids)])
        else:
           records = self.env['vehicle.number'].search([]) 
        for record in records:
            if record.two_wheeler:
                self._process_vehicle(record,prepared_data, 'two_wheeler')
            elif record.four_wheeler:
                self._process_vehicle(record, prepared_data, 'four_wheeler')
            elif record.heavy:
                self._process_vehicle(record, prepared_data, 'heavy')
            elif record.vehicle_system =='old':
                self._process_vehicle(record, prepared_data, 'old')
            elif record.vehicle_system == 'pradesh' :
                self._process_vehicle(record, prepared_data, 'pradesh')
            elif record.electric_vehicle_num :
                self._process_vehicle(record, prepared_data, 'electric')
            
        # print("$$$$$$$$$$$$$$$$$$$$$$$",prepared_data)
        
        # return prepared_data
        return {
                'type': 'ir.actions.report',
                'report_name': 'vehicle_management.vehicle_number_template',
                'report_type': 'qweb-html',
                'data': {
                    'company_name': vehicle_company_name,
                    'date': date_bs,
                    # 'date_from': self.date_from_bs,
                    # 'date_to': self.date_to_bs,
                    'prepared_data': prepared_data, 
                },
            }

        # context_json = json.dumps({
        #     'company_name': vehicle_company_name,
        #     'date': date_bs,
        #     'prepared_data': prepared_data,
        # })

        # return {
        #     'type': 'ir.actions.report',
        #     'report_name': 'vehicle_management.vehicle_number_template',
        #     'report_type': 'qweb-pdf',
        #     'data': {
        #         'context': context_json,  # Pass the context as a JSON string
        #     },
        #     'context': {
        #         'preview': True,  # Enable preview mode
        
        #     },
        # }
      

     
        # context_url_params = urllib.parse.urlencode(context)
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": '/report/html/vehicle_management.vehicle_number_template/%s?%s' % (self.id, context_url_params),
        #     "target": "new",  # Open in a new tab/window
        # }

    def _process_vehicle(self,record, prepared_data, vehicle_type_key):
        vehicle_type = None
        if vehicle_type_key == 'old':
         
            vehicle_type = 'Old Vehicle System'
            if vehicle_type_key not in prepared_data:
                prepared_data[vehicle_type_key] = {}

            if vehicle_type not in prepared_data[vehicle_type_key]:
                prepared_data[vehicle_type_key][vehicle_type] = []

        elif vehicle_type_key == 'electric':
            vehicle_type = 'Electric Vehicle System'
    
            if vehicle_type_key not in prepared_data:
                prepared_data[vehicle_type_key] = {}

            if vehicle_type not in prepared_data[vehicle_type_key]:
                prepared_data[vehicle_type_key][vehicle_type] = []
        elif vehicle_type_key == 'pradesh':
            vehicle_type = 'Pradesh Vehicle System'
    
            if vehicle_type_key not in prepared_data:
                prepared_data[vehicle_type_key] = {}

            if vehicle_type not in prepared_data[vehicle_type_key]:
                prepared_data[vehicle_type_key][vehicle_type] = []
        else:
            vehicle_type = getattr(record,vehicle_type_key)
            if not vehicle_type:
                return

            if vehicle_type_key not in prepared_data:
                prepared_data[vehicle_type_key] = {}

            if vehicle_type not in prepared_data[vehicle_type_key]:
                prepared_data[vehicle_type_key][vehicle_type] = []


        if record.bluebook_id:
            latest_bluebook_id = sorted(record.bluebook_id, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        else:
            latest_bluebook_id = None
        

        if record.vehicle_insurance_id:
            latest_insurance_id = sorted(record.vehicle_insurance_id, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        else:
            latest_insurance_id = None  


        if record.vehicle_permit_id:
            latest_permit_id= sorted(record.vehicle_permit_id, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        else:
            latest_permit_id = None 
    
        if record.vehicle_pollution_id:
            latest_pollution_id = sorted(record.vehicle_pollution_id, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        else:
            latest_pollution_id = None


        # Get the latest records for bluebook, pollution, insurance, and permit 
        latest_bluebook = self._get_latest_record(latest_bluebook_id) 
        latest_insurance = self._get_latest_record(latest_insurance_id)
        latest_permit =self._get_latest_record(latest_permit_id) 
        latest_pollution = self._get_latest_record(latest_pollution_id)
  
       
        # Append the processed data for the vehicle type
        prepared_data[vehicle_type_key][vehicle_type].append({
            'final_number': record.final_number,
            'bluebook_date_bs': latest_bluebook['expiry_date_bs'],
            'bluebook_renewed_status': 'बिल आएको' if latest_bluebook['renewed'] else 'बिल नआएको',
            'pollution_date_bs': latest_pollution['expiry_date_bs'],
            'pollution_renewed_status': 'बिल आएको' if latest_pollution['renewed'] else 'बिल नआएको',
            'insurance_date_bs': latest_insurance['expiry_date_bs'],
            'insurance_renewed_status': 'बिल आएको' if latest_insurance['renewed'] else 'बिल नआएको',
            'permit_date_bs': latest_permit['expiry_date_bs'],
            'permit_renewed_status': 'बिल आएको' if latest_permit['renewed'] else 'बिल नआएको',
            'insurance_company_name': latest_insurance['insurance_company'],
            'seat_number': record.seat_no,
            'remarks': ''
        })
        

    @api.model
    def _get_latest_record(self, record):
        """
        Retrieve the latest record based on expiry date.

        :param record: A single record to process.
        :return: Dictionary with expiry date and renewal status
        """
        if record:
            return {
                'expiry_date_bs': record.expiry_date_bs,
                'renewed': record.renewed,
                'insurance_company': record.insurance_company if hasattr(record, 'insurance_company') else None
            }
        return {'expiry_date_bs': None, 'renewed': False, 'insurance_company': None}





        # prepared_data = []
        # date_bs = nepali_datetime.date.from_datetime_date(self.date).strftime('%Y-%m-%d')

        # records = self.env['vehicle.number'].search([])
        # vehicle_company_name = self.vehicle_company.name


        # for record in records:
            
        #     bluebooks = record.bluebook_id
        #     insurance = record.vehicle_insurance_id
        #     permit = record.vehicle_permit_id
        #     pollution = record.vehicle_pollution_id


        #     if bluebooks:
        #         latest_bluebook = sorted(bluebooks, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        #         latest_expiry_date_bs = latest_bluebook.expiry_date_bs
        #         bluebook_renewed_status = latest_bluebook.renewed
        #     else:
        #         latest_expiry_date_bs = None  
        #         bluebook_renewed_status  = False

        #     if insurance:
        #         latest_insurance = sorted(insurance, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        #         insurance_expiry_date_bs = latest_insurance.expiry_date_bs
        #         insurance_renewed_status = latest_insurance.renewed
        #         insurance_company_name = latest_insurance.insurance_company
        #     else:
        #         insurance_expiry_date_bs = None  
        #         insurance_renewed_status  = False
        #         insurance_company_name = None

        #     if permit:
        #         latest_permit= sorted(permit, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        #         permit_expiry_date_bs = latest_permit.expiry_date_bs
        #         permit_renewed_status = latest_permit.renewed
        #     else:
        #         permit_expiry_date_bs = None 
        #         permit_renewed_status  = False

        #     if pollution:
        #         latest_pollution = sorted(pollution, key=lambda x: x.expiry_date_bs, reverse=True)[0]
        #         pollution_expiry_date_bs = latest_pollution.expiry_date_bs
        #         pollution_renewed_status = latest_pollution.renewed
        #     else:
        #         pollution_expiry_date_bs = None
        #         pollution_renewed_status  = False

        #     prepared_data.append({
        #         'final_number': record.final_number,
        #         'bluebook_date_bs':latest_expiry_date_bs,
        #         'bluebook_renewed_status':'बिल आएको' if bluebook_renewed_status == True else 'बिल नआएको',
        #         # 'bluebook_date_bs': record.bluebook_id.expiry_date_bs,
        #         'pollution_date_bs': pollution_expiry_date_bs,
        #         'pollution_renewed_status':'बिल आएको' if pollution_renewed_status == True else 'बिल नआएको',
        #         'insurance_date_bs': insurance_expiry_date_bs,
        #         'insurance_renewed_status':'बिल आएको' if insurance_renewed_status == True else 'बिल नआएको',
        #         'permit_date_bs': permit_expiry_date_bs,
        #         'permit_renewed_status':'बिल आएको' if permit_renewed_status == True else 'बिल नआएको',
        #         'insurance_company_name': insurance_company_name,
        #         'seat_number': record.seat_no,
        #         'remarks': '',
        #     })

        # print("Prepared data",prepared_data)
        # print("Company _name" , vehicle_company_name)
        # return {
        #         'type': 'ir.actions.report',
        #         'report_name': 'vehicle_management.vehicle_number_template',
        #         'report_type': 'qweb-pdf',
        #         'context': {
        #             'company_name': vehicle_company_name,
        #             'date': date_bs,
        #             # 'date_from': self.date_from_bs,
        #             # 'date_to': self.date_to_bs,
        #             'prepared_data': prepared_data, 
        #         },
        #     }



        # prepared_data = {
        #     'two_wheeler': defaultdict(list),
        #     'four_wheeler': defaultdict(list),
        #     'heavy': defaultdict(list)
        # }

        # # Search for vehicle records related to the selected vehicle company
        # records = self.env['vehicle.number'].search([('vehicle_company', '=', self.vehicle_company.id)])
        
        # # Loop through the records and classify them into categories based on the actual values
        # for record in records:
        
        #     if record.two_wheeler:
        #         vehicle_type = dict(record._fields['two_wheeler'].selection).get(record.two_wheeler)
        #         prepared_data['two_wheeler'][vehicle_type].append({
        #             'final_number': record.final_number,
        #             'last_renewal_date_bs': record.bluebook_id.last_renewal_date_bs or 'N/A'
        #         })
        #     elif record.four_wheeler:
        #         vehicle_type = dict(record._fields['four_wheeler'].selection).get(record.four_wheeler)
        #         prepared_data['four_wheeler'][vehicle_type].append({
        #             'final_number': record.final_number,
        #             'last_renewal_date_bs': record.bluebook_id.last_renewal_date_bs or 'N/A'
        #         })
        #     elif record.heavy:
        #         vehicle_type = dict(record._fields['heavy'].selection).get(record.heavy)
        #         prepared_data['heavy'][vehicle_type].append({
        #             'final_number': record.final_number,
        #             'last_renewal_date_bs': record.bluebook_id.last_renewal_date_bs or 'N/A'
        #         })
        
        # # Printing prepared data (for debugging purposes)
        # print("Prepared data:", prepared_data)
        
        # # # Return the report action with the prepared data in context
        # return {
        #     'type': 'ir.actions.report',
        #     'report_name': 'vehicle_management.vehicle_number_template',
        #     'report_type': 'qweb-pdf',
        #     'context': {
        #         'company_name': self.vehicle_company.name,
        #         'prepared_data': prepared_data,  # Pass the prepared data as context
        #     },
        # }
