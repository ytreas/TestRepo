# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import datetime
from dateutil import relativedelta

from odoo import fields, models


class PayslipLinesContributionRegister(models.TransientModel):
    """Create new model Payslip Lines by Contribution Registers"""
    _name = 'payslip.lines.contribution.register'
    _description = 'Payslip Lines by Contribution Registers'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    date_from_bs = fields.Char(string="Date From (Nepali)", store=True)
    date_to_bs = fields.Char(string="Date To (Nepali)", store=True)

    def action_print_report(self):
        """Function for Print Report"""
        active_ids = secontribution_register_actionlf.env.context.get('active_ids', [])
        datas = {
            'ids': active_ids,
            'model': 'hr.contribution.register',
            'form': self.read()[0]
        }
        return (self.env.ref(
            'hr_payroll_community.contribution_register_action')
                .report_action([], data=datas))
