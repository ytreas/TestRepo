/** @odoo-module **/
const { Component } = owl;
import { _t } from "@web/core/l10n/translation";
const now = new Date();
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState,onMounted, useEffect } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class BalanceSheet extends owl.Component {
    async setup() {
        onMounted(this.ev_mounted);
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.posted = useRef('posted');
        this.period = useRef('periods');
        this.period_year = useRef('period_year');
        this.draft = useRef('draft');
        this.state = useState({
            data: null,
            filter_data: null,
            year : [now.getFullYear()],
            comparison: false,
            comparison_type: null,
            start_date_ad: '',
            start_date_bs: '',
            end_date_ad: '',
            end_date_bs: '',
            filter_range:'',
            filter_range_ad:'',

        });

        useEffect(
            ()=>{
                this.state.filter_range=`${this.state.start_date_bs?_t('Start Date:'):''} ${this.state.start_date_bs?this.state.start_date_bs:''}  ${this.state.end_date_bs?_t('End Date:'):''} ${this.state.end_date_bs?this.state.end_date_bs:''}`
                this.state.filter_range_ad=`${this.state.start_date_ad?_t('Start Date:'):''} ${this.state.start_date_ad?this.state.start_date_ad:''}  ${this.state.end_date_ad?_t('End Date:'):''} ${this.state.end_date_ad?this.state.end_date_ad:''}`
            },
            ()=>[this.state.start_date_bs,this.state.end_date_bs]
        );
        this.wizard_id = await this.orm.call("dynamic.balance.sheet.report", "create", [{}]) | null;
        this.load_data(self.initial_render = true);
    }

    toggle_menu(){
        filterMenu.classList.toggle('active-menu');
    }

    toggle_close(){
        filterMenu.classList.remove('active-menu');
    }

     init_filter(e){
        setTimeout(async() => {
            if(e.target.id=="start_date"){
                if (this.state.start_date_bs != e.target.value) {
                    this.state.start_date_bs = e.target.value;
                    this.state.start_date_ad = await this.orm.call('account.general.ledger', 'bs_to_ad', [[e.target.value]]);
                    e.target.value = this.state.start_date_ad[0].date;
                    this.state.start_date_ad = this.state.start_date_ad[0].date;
                    // this.state.filter_range=`${this.state.start_date_bs?_t('Start Date'):''}: ${this.state.start_date_bs?this.state.start_date_bs:''}  ${this.state.end_date_bs?_t('End Date'):''}: ${this.state.end_date_bs?this.state.end_date_bs:''}`

                    this.apply_date(e);
                }
            }
            else{
                if (this.state.end_date_bs != e.target.value) {
                    this.state.end_date_bs = e.target.value;
                    this.state.end_date_ad = await this.orm.call('account.general.ledger', 'bs_to_ad', [[e.target.value]]);
                    e.target.value = this.state.end_date_ad[0].date;
                    this.state.end_date_ad = this.state.end_date_ad[0].date;
                    // this.state.filter_range=`${this.state.start_date_bs?_t('Start Date'):''}: ${this.state.start_date_bs?this.state.start_date_bs:''}  ${this.state.end_date_bs?_t('End Date'):''}: ${this.state.end_date_bs?this.state.end_date_bs:''}`
    
                    this.apply_date(e);
    
                }
            }    
        }, 1000);
        
        
    }

    init_date(){
        var mainInput = document.getElementById("start_date");
        var mainInput_ad = document.getElementById("start_date_ad");
        var mainInput2 = document.getElementById("end_date");
        var mainInput2_ad = document.getElementById("end_date_ad");
        const self = this;
        mainInput.nepaliDatePicker({
            changeMonth: true,
            changeYear: true,
        });
        $('#start_date_ad').datepicker({
            changeMonth: true,
            changeYear: true,
            dateFormat: 'yy-mm-dd',
            onSelect: async function (dateText) {
                self.state.start_date_ad = await self.orm.call('account.general.ledger', 'ad_to_bs', [[dateText]]);
                self.state.start_date_bs = self.state.start_date_ad[0].date
                self.state.start_date_ad = dateText
                // self.state.filter_range=`${self.state.start_date_bs?_t('Start Date'):''}: ${self.state.start_date_bs?self.state.start_date_bs:''}  ${self.state.end_date_bs?_t('End Date'):''}: ${self.state.end_date_bs?self.state.end_date_bs:''}`

                var value = {
                    target: {
                        'name': 'start_date',
                        'value': mainInput_ad.value,
                    }
                }
                self.apply_date(value);

            }
        });
        $('#end_date_ad').datepicker({
            changeMonth: true,
            changeYear: true,
            dateFormat: 'yy-mm-dd',
            onSelect: async function (dateText) {
                self.state.end_date_ad = await self.orm.call('account.general.ledger', 'ad_to_bs', [[dateText]]);
                self.state.end_date_bs = self.state.end_date_ad[0].date
                self.state.end_date_ad = dateText
                // self.state.filter_range=`${self.state.start_date_bs?_t('Start Date'):''}: ${self.state.start_date_bs?self.state.start_date_bs:''}  ${self.state.end_date_bs?_t('End Date'):''}: ${self.state.end_date_bs?self.state.end_date_bs:''}`

                var value = {
                    target: {
                        'name': 'end_date',
                        'value': mainInput2_ad.value,
                    }
                }
                self.apply_date(value);

            }
        });

        mainInput2.nepaliDatePicker();
    }

    ev_mounted() {
        try{

            // var mainInput = document.getElementById("start_date");
            // var mainInput_ad = document.getElementById("start_date_ad");
            // var mainInput2 = document.getElementById("end_date");
            // var mainInput2_ad = document.getElementById("end_date_ad");
            var toggleBtn = document.getElementById('toggleBtn');
            var filterMenu = document.getElementById('filterMenu');
            var closeBtn = document.getElementById('closeBtn');
            const self = this;
            setTimeout(() => {
                this.init_date();
            }, 1000);
        }
        catch (e){
            console.log("Error",e);
            
        }
       

    }

    async load_data() {
    /**
     * Loads the data for the balance sheet report.
     */
        var self = this;
        var action_title = self.props.action.display_name;
        try {
            var self = this;
            let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
            self.state.data = data[0]
            self.state.datas = data[2]
            self.state.filter_data = data[1]
            self.state.title = action_title
        }
        catch (el) {
            window.location.href
        }
    }
    async show_gl(ev) {
    /**
        * Shows the General Ledger view by triggering an action.
        *
        * @param {Event} ev - The event object triggered by the action.
        * @returns {Promise} - A promise that resolves to the result of the action.
        */
        return this.action.doAction({
            type: 'ir.actions.client',
            name: 'General Ledger',
            tag: 'gen_l',
        });
    }
    async print_pdf(ev) {
        /**
        * Print PDF Method
        * This method is triggered when the "Print PDF" button is clicked.
        * It retrieves the report data and performs an action to generate and download a PDF report.
        */
        ev.preventDefault();
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0]
        self.state.datas = data[2]
        return self.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.balance_sheet',
            'report_file': 'dynamic_accounts_report.balance_sheet',
            'data': {
                'data': self.state,
                'date_range_bs':self.state.filter_range,
                'date_range_ad':self.state.filter_range_ad,
                'report_name': self.props.action.display_name
            },
            'display_name': self.props.action.display_name,
        });
    }
    async print_xlsx(ev) {
         /**
         * Generates and downloads an XLSX report based on the profit and loss data.
         *
         * @param {Event} ev - The event object triggered by the action.
         */
        var self = this;
        let data = await self.orm.call("dynamic.balance.sheet.report", "view_report", [this.wizard_id,this.state.comparison,this.state.comparison_type]);
        self.state.data = data[0]
        self.state.datas = data[2]
        var action = {
            'data': {
                'model': 'dynamic.balance.sheet.report',
                'data': JSON.stringify(self.state),
                'output_format': 'xlsx',
                'report_name': self.props.action.display_name,
                'report_action': self.props.action.xml_id,
            },
        };
        BlockUI;
        await download({
            url: '/xlsx_report',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
    }
    async apply_journal(ev) {
     /**
        * Applies journal filtering based on the selected option in an event target.
        *
        * @param {Event} ev - The event object triggered by the action.
        */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'journal_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.code').innerHTML = res[0].journal_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_account(ev) {
     /**
        * Applies account filtering based on the selected option in an event target.
        *
        * @param {Event} ev - The event object triggered by the action.
        */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'account_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.account').innerHTML = res[0].account_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_analytic_accounts(ev) {
    /**
     * Applies analytic accounts filtering based on the selected option in an event target.
     *
     * @param {Event} ev - The event object triggered by the action.
     */
        self = this
        if (ev.target.classList.contains("selected-filter")) {
            ev.target.classList.remove('selected-filter')
        }
        else {
            ev.target.classList.add('selected-filter')
        }
        this.filter = ({
            'analytic_ids': ev.target.querySelector('span').textContent,
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.analytic').innerHTML = res[0].analytic_ids;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async apply_entries(ev) {
    /**
     * Applies the selected entries filter and triggers data loading based on the selected filter class.
     * @param {Event} ev - The event object triggered by the entries filter selection.
     * @returns {Promise<void>} - A promise that resolves when the data is loaded.
     */
        self = this;
        ev.target.classList.add('selected-filter')
        if (ev.target.value == 'draft') {
            this.posted.el.classList.remove('selected-filter')
        } else {
            this.draft.el.classList.remove('selected-filter')
        }
        this.filter = ({
            'target': ev.target.value
        })
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter,]);
        ev.delegateTarget.querySelector('.target').innerHTML = res[0].target_move;
        self.initial_render = false;
        self.load_data(self.initial_render);
    }
    async unfoldAll(ev) {
    /**
     * Unfolds or collapses all table rows based on the selected filter class.
     * @param {Event} ev - The event object triggered by the unfolding action.
     * @returns {void}
     */
        if (!ev.target.classList.contains("selected-filter")) {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                $(this.tbody.el.children[length])[0].classList.add('show')
            }
            ev.target.classList.add("selected-filter");
        } else {
            for (var length = 0; length < this.tbody.el.children.length; length++) {
                $(this.tbody.el.children[length])[0].classList.remove('show')
            }
            ev.target.classList.remove("selected-filter");
        }
    }
    async apply_date(ev){
    /**
     * Applies the selected date filter and triggers data loading based on the selected filter value.
     * @param {Event} ev - The event object triggered by the date selection.
     * @returns {Promise<void>} - A promise that resolves when the data is loaded.
     */
        self = this
        if (ev.target.name === 'start_date') {
                this.filter = {
                    ...this.filter,
                    date_from: ev.target.value
                };
        } else if (ev.target.name === 'end_date') {
                this.filter = {
                    ...this.filter,
                    date_to: ev.target.value
                };
        } else if (ev.target.attributes["data-value"].value == 'month') {
                this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'year') {
                this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'quarter') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-month') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-year') {
            this.filter = ev.target.attributes["data-value"].value
        } else if (ev.target.attributes["data-value"].value == 'last-quarter') {
            this.filter = ev.target.attributes["data-value"].value
        }
        let res = await self.orm.call("dynamic.balance.sheet.report", "filter", [this.wizard_id, this.filter]);
        self.initial_render = false;
        self.load_data(self.initial_render);
        this.load_data(this.initial_render);

        document.getElementById('start_date').value = this.state.start_date_bs;
        document.getElementById('start_date_ad').value = this.state.start_date_ad;
        document.getElementById('end_date').value = this.state.end_date_bs;
        document.getElementById('end_date_ad').value = this.state.end_date_ad;
    }
    onPeriodChange(ev){
        this.period_year.el.value = ev.target.value
    }
    onPeriodYearChange(ev){
        this.period.el.value = ev.target.value
    }
    async applyComparisonPeriod(){
        this.state.comparison  = this.period.el.value
        this.state.comparison_type = "month"
        let monthNamesShort = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ]
        let res = await this.orm.call("dynamic.balance.sheet.report", "comparison_filter", [this.wizard_id, this.state.comparison]);
        this.state.year = [monthNamesShort[now.getMonth()]+'  ' + now.getFullYear()]
        for (var length = 0; length < res.length; length++) {
                const dateObject = new Date(res[length]['date_to']);
                this.state.year.push(monthNamesShort[dateObject.getMonth()]+'  ' + dateObject.getFullYear())
            }
        this.load_data(self.initial_render);
    }
    async applyComparisonYear(){
        this.state.comparison = this.period_year.el.value
        this.state.comparison_type = "year"
        let res = await this.orm.call("dynamic.balance.sheet.report", "comparison_filter_year", [this.wizard_id, this.state.comparison]);
        this.state.year = [now.getFullYear()]
        for (var length = 0; length < res.length; length++) {
                const dateObject = new Date(res[length]['date_to']);
                this.state.year.push(dateObject.getFullYear())
            }
        this.load_data(self.initial_render);
    }
    apply_comparison() {
        this.state.comparison = false
        this.state.comparison_type = null
        this.state.year = [now.getFullYear()]
    }

}
BalanceSheet.template = 'bls_template_new';
//BalanceSheet.components = {
//    FinancialReportControlPanel
//}
actionRegistry.add("bl_s", BalanceSheet);