/** @odoo-module */
const {Component} = owl;
import {loadJS} from "@web/core/assets";

export class TransportKpiCard extends Component {
        static props = {
        name: String,
        value: Number,
        percentage: Number,
    };
}

TransportKpiCard.template = "owl.TransportKpiCard"
