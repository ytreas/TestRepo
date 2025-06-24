
from odoo import models, fields, api, _ 
from odoo.exceptions import UserError

class RouteSearchWizard(models.TransientModel):
    _name = 'route.search.wizard'
    _description = 'Fleet Route Search Wizard'
    
    source = fields.Char("Source")
    destination = fields.Char("Destination")
    pickup_date = fields.Date("Pickup Date")
    delivery_date = fields.Date("Delivery Date")
    weight = fields.Float("Weight")
    route_ids = fields.One2many('route.search.line', 'wizard_id')
    main_id = fields.Many2one('transport.order', string="Main Order")  

    def populate_routes(self):
        source_parts = self.source.split(',')
        destination_parts = self.destination.split(',')
        
        source_province = source_parts[0] if len(source_parts) > 0 else False
        source_district = source_parts[1] if len(source_parts) > 1 else False
        source_palika = source_parts[2] if len(source_parts) > 2 else False
        
        destination_province = destination_parts[0] if len(destination_parts) > 0 else False
        destination_district = destination_parts[1] if len(destination_parts) > 1 else False
        destination_palika = destination_parts[2] if len(destination_parts) > 2 else False
        print("Location",source_province,source_district,source_palika,self.pickup_date)
        domain = []
        if self.pickup_date:
            domain.append(('route_date', '<=', self.pickup_date))
        matching_routes = []
        
        routes = self.env['fleet.route'].search(domain)
        for route in routes:
            checkpoints = route.checkpoints.sorted(key=lambda x: x.sequence)
   
            for i ,source_cp in enumerate(checkpoints):
                print("###############",source_cp.name)
                # print("###############",source_cp.checkpoint_district.district_name)
                # print("###############",source_cp.checkpoint_palika.palika_name)
                if(
                    (not source_province or source_cp.checkpoint_province.name == source_province) and
                    (not source_district or source_cp.checkpoint_district.district_name == source_district) and
                    (not source_palika or source_cp.checkpoint_palika.palika_name == source_palika)
                ):
                    print("FIrst Search succesdss",source_cp.planned_date)
                    for dest_cp in checkpoints[i+1:]:
                        if(
                            (not destination_province or dest_cp.checkpoint_province.name == destination_province) and
                            (not destination_district or dest_cp.checkpoint_district.district_name == destination_district) and
                            (not destination_palika or dest_cp.checkpoint_palika.palika_name == destination_palika)
              
                        ):
                            matching_routes.append({
                                'route': route,
                                'source_checkpoint_name': source_cp.name,
                                'date_on_source':source_cp.planned_date_bs,
                                'date_on_destination':dest_cp.planned_date_bs,
                                'destination_checkpoint_name': dest_cp.name,
                                'space_at_checkpoint':source_cp.space_available,
                            })
                            break
        
        print("Matching Routes:", matching_routes)
        # final = self.env['fleet.route'].browse(matching_routes)
        for entry in matching_routes:
            self.route_ids = [(0, 0, {
                'route_id': entry['route'].id,
                'source_checkpoint':entry['source_checkpoint_name'],
                's_date':entry['date_on_source'],
                'd_date':entry['date_on_destination'],
                'destination_checkpoint':entry['destination_checkpoint_name'],
                'space_available': entry['space_at_checkpoint'],
            })]
class RouteSearchLine(models.TransientModel):
    _name = 'route.search.line'
    _description = 'Route Line'

    wizard_id = fields.Many2one('route.search.wizard')
    route_id = fields.Many2one('fleet.route')
    driver_name = fields.Many2one('driver.details', related='route_id.driver_id',string="Driver")
    s_date = fields.Char(string="Date in Start Checkpoint")
    d_date = fields.Char(string="Date in Next Checkpoint")
    source_checkpoint = fields.Char(string="Start Checkpoint")
    destination_checkpoint = fields.Char(string="Next Checkpoint")
    space_available = fields.Char(string="Space At Start")
    def action_select_route(self):
        if self.route_id and self.wizard_id.main_id:
            existing = self.env['existing.assignment'].search([
                ('order_id', '=', self.wizard_id.main_id.id),
                ('route', '=', self.route_id.id)
                ], limit=1)

            if existing:
                # Optional: Raise a warning to inform the user
                raise UserError("This route has already been assigned to this order.")

            self.env['existing.assignment'].sudo().create({
                'order_id': self.wizard_id.main_id.id,
                'route': self.route_id.id,
                'date': self.s_date,
                'vehicle_id': self.route_id.vehicle_number.id,
                'driver': self.route_id.driver_id.id,
                'check_points': self.source_checkpoint,
            })
        # return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transport.order',
            'view_mode': 'form',
            'res_id': self.wizard_id.main_id.id,
            'target': 'current',  # opens in the same window
        }