/** @odoo-module **/

import { SearchBar } from "@web/search/search_bar/search_bar";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks"; 
import { useState, onMounted } from "@odoo/owl";

export class CustomDateFilter extends SearchBar {
    setup() {
        super.setup();
        console.log("Custom Date Filter setup")
        console.log("this:", this); 
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            fromDate: '',
            toDate: '',
            searchTerm: ''
        });
        this.applyCustomFilters = this.applyCustomFilters.bind(this);

        mounted( () => {
            super.mounted();
            this.initNepaliDatePicker();
            // this.initializeCompanyId();
            
        });
    }
    initNepaliDatePicker() {
        const self=this;
        console.log("initNepaliDatePicker called");
        const nepaliDateInputs = document.getElementById('from_date');
        nepaliDateInputs.nepaliDatePicker({
            onChange:(ev)=>{  
                self.onFromDateChange($(ev));
            }
            
        });
        const nepaliDateInput = document.getElementById('to_date');
        nepaliDateInput.nepaliDatePicker({
            
            onChange:(ev)=>{    
                self.onToDateChange($(ev));
            }
            
        });

    }
    onFromDateChange(event=null) {
        this.state.fromDate = event[0].bs
    }
    onToDateChange(event=null) {
        this.state.toDate = event[0].bs
    }
    OnPrintClick() {
        console.log('OnPrintClick called88888'); 
    }
    applyCustomFilters = () => {
        console.log("Applying custom filters...");
       
    }
    //     const domain = [];
        
    //     if (this.state.fromDate) {
    //         domain.push(['check_in_date', '>=', this.state.fromDate]);
    //     }
        
    //     if (this.state.toDate) {
    //         domain.push(['check_out_date', '<=', this.state.toDate]);
    //     }
        
    //     this.props.searchModel.setDomain(domain);
    // }
}

console.log("Berfore Registry");

registry.category("search_views").add("custom_search_bar", {
    ...SearchBar,
    Controller: CustomDateFilter,
    CustomDateFilter_template : "CustomSearchBar",
});
console.log("After Register");