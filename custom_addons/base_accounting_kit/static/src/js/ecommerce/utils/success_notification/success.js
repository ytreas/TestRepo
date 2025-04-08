/** @odoo-module **/

import { Component } from "@odoo/owl";

export class SuccessNotification extends Component {
    static template = "base_accounting_kit.success_notification";
    static props = {
        success: [String, { toString: Function }],
    }
}
