/** @odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard,CustomerCard } from "./kpi_card/kpi_card";
import { ChartRenderer} from "./chart_renderer/chart_renderer";


import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl;
/*import { rpc } from "@web/core/web"*/

export class OwlReportingDashboard extends Component {

    // async getTestData(){
    //     this.state.TestData = {
    //         data: {
    //             labels: ['Red', 'Blue', 'Yellow'],
    //             datasets: [
    //                 {
    //                     label: 'My First Dataset',
    //                     data: [300, 50, 500],
    //                     hoverOffset: 4
    //                 },
    //                 {
    //                     label: 'My Second Dataset',
    //                     data: [100, 70, 150],
    //                     hoverOffset: 4
    //                 }
    //             ]
    //         }
    //     };
    // }

// async getTopProducts(){
//     let domain = [['state', 'in', ['sale', 'done']]]
//     if (this.state.period > 0){
//         domain.push(['date','>', this.state.current_date])
//     }

//     const data = await this.orm.readGroup("sale.report", domain, 
//                  ['product_id', 'price_total'], ['product_id'], 
//                  { limit: 5, orderby: "price_total desc" })

//     this.state.topProducts = {
//         data: {
//             labels: data.map(d => d.product_id[1]),
//               datasets: [
//               {
//                 label: 'Total',
//                 data: data.map(d => d.price_total),
//                 hoverOffset: 4,
//                 backgroundColor: data.map((_, index) => getColor(index)),
//               },{
//                 label: 'Count',
//                 data: data.map(d => d.product_id_count),
//                 hoverOffset: 4,
//                 backgroundColor: data.map((_, index) => getColor(index)),
//             }]
//         },
//     }
// }


    setup() {
        this.state = owl.useState({
            fetchData: { // State for chart data
                labels: [''],
                datasets: [{
                    label: 'Arrivals',
                    data: [],
                    hoverOffset: 4,
                }]
            },
            TestData: null,
            names: [],
            // selectedCommodity: '',
            selectedCommodityName : '',
            startDate: '',
            endDate: '',
            filtersReady: false,
        });

        this.orm = useService("orm");
        this.chartRef = useRef(null);

        // this.chartData = {
        //     labels: this.state.fetchData.labels,  // Common labels
        //     datasets: [
        //         ...this.state.fetchData.datasets,  // First dataset (Arrivals)
        //         // ...this.state.fetchData2.datasets,  // Second dataset (Departures)
        //     ]
        // };


        onWillStart(async () => {
            await this.fetchNames();
            await this.fetchData();
            // await this.getTestData();
            
        });
        onMounted(() => {
            this.initNepaliDatePicker();
            // this.initializeCompanyId();
            
        });
    }
 
    initNepaliDatePicker() {
        const self=this;

        const nepaliDateInputs = document.getElementById('arrival_date_from');
        nepaliDateInputs.nepaliDatePicker({
            onChange:(ev)=>{  
                self.onDateRangeChangefrom($(ev));
            }
            
        });
        const nepaliDateInput = document.getElementById('arrival_date_to');
        nepaliDateInput.nepaliDatePicker({
            
            onChange:(ev)=>{    
                self.onDateRangeChangeto($(ev));
            }
            
        });

    }

    async fetchNames() {
        try {
            // Fetch all relevant entries in one call
            const result = await this.orm.searchRead("amp.daily.arrival.entry", [], ["commodity_id"]);
           
            
            // Extract all commodity IDs (including duplicates)
            const commodityIds = result.map(entry => entry.commodity_id).flat();
    
            // Fetch all commodities in a single batch call using the 'in' operator
            const commodityResults = await this.orm.searchRead(
                'amp.commodity',
                [['id', 'in', commodityIds]], // Fetch all commodities in one query
                ['id', 'name']
            );
            // console.log("Commodity Results:", commodityResults);
            // Use a Map to ensure uniqueness by commodity ID
            const uniqueCommodityMap = new Map();
            commodityResults.forEach(commodity => {
                if (!uniqueCommodityMap.has(commodity.name)) {
                    uniqueCommodityMap.set(commodity.name, {
                        id: commodity.id,
                        name: commodity.name
                    });
                }
            });
    
            // Convert the Map values to an array
            const uniqueCommodityNames = Array.from(uniqueCommodityMap.values());
            // console.log("uniqueCommodityNames",uniqueCommodityNames)
            // Assign the unique names to state.names
            this.state.names = uniqueCommodityNames;
    
        } catch (error) {
            console.error("Error fetching commodity names:", error);
        }
    }

    async fetchData() {
        try {
            if (this.env.company) {
                this.companyId = this.env.company.id;
                console.log("Company ID:", this.companyId);
            } else {
                console.error("Company info is not available.");
            }
            if (!this.state.filtersReady) return; 
    
            let startdate = this.state.startDate;
            let enddate = this.state.endDate;
            let productName = this.state.selectedCommodityName;
    
            const filters = [
                ['arrival_date_bs', '>=', startdate], 
                ['arrival_date_bs', '<=', enddate],   
                ['name', '=', productName]           
            ];
            const result = await this.orm.searchRead("amp.commodity",filters, ["name", "arrival_date_bs", "total", "unit"]);
            
            const groupedData = {};
    
            result.forEach(record => {
                const { name, arrival_date_bs, total ,unit } = record;
                // console.log(`Processing record: commodity = ${name}, arrival_date_bs = ${arrival_date_bs}, volume = ${total}, unit = ${unit}`);
                const key = `${name}-${arrival_date_bs}`; 
                if (!groupedData[key]) {
                    groupedData[key] = {
                        name,
                        arrival_date_bs,
                        unit,
                        total: 0, 
                    };
                }
                groupedData[key].total += total;
            });
    
            // Sort the grouped data by arrival_date_bs in ascending order
            const sortedData = Object.values(groupedData).sort((a, b) => {
                // Compare date strings, assuming 'arrival_date_bs' is in a consistent format
                return new Date(a.arrival_date_bs) - new Date(b.arrival_date_bs);
            });
    
            // Update the state with the sorted chart data
            this.state.fetchData = {
                data: {
                    labels: sortedData.map(item => item.arrival_date_bs), // Labels sorted by date
                    datasets: [
                        {
                            label: productName,
                            // data: Object.values(groupedData).map(item => item.total), // Map total volumes
                            data: sortedData.map(item => ({
                                x: item.arrival_date_bs,
                                y: item.total,
                                unit: item.unit[1] // Assuming unit is an array and the second element is the unit string
                            })),
                            hoverOffset: 4,
                            backgroundColor: sortedData.map((_, index) => getColor(index)),
                        }
                    ]
                },
            };
    
        } catch (error) {
            console.error("Error fetching chart data:", error);
        }
    }
    
     
    onDateRangeChangefrom(event=null) {
        this.state.startDate = event[0].bs
    
        // console.log("Vaslue",event[0].ad)
        // console.log("Vaslue",this.startDate)

        this.checkFiltersReady();
    }
    onDateRangeChangeto(event=null) {
        this.state.endDate = event[0].bs
        // console.log("Vaslue tooooooo",event[0].ad)
        // console.log("Vaslue tooooooooo",this.endDate)
        this.checkFiltersReady();
    }

    onPrint() {
         const defaultReportName = "Arrival Report - Chart"; // Customize this name
    document.title = defaultReportName;
        setTimeout(() => {
            window.print();
        }, 500);
    }

    
    

    onCommodityChange(event) {
        const commodityId = event.target.value; 
        // console.log('onCommodityChange method triggered with ID:', commodityId);
        
        // Find the selected commodity by its ID
        const selectedCommodity = this.state.names.find(commodity => commodity.id === parseInt(commodityId));
        
        if (selectedCommodity) {
            // console.log('Selected Commodity Name:', selectedCommodity.name);
            this.state.selectedCommodityName = selectedCommodity.name;  // Store the name in the state
        } else {
            console.log('Commodity not found');
        }
        this.checkFiltersReady();
    }

    onCommodityChangePrices(event) {
       
        const Commodityid = event.target.value; 
        // console.log('onDateRangeChange method triggered $$$$$$$$$$$$$$$$$$$$$$$ ID',Commodityid);
        const selectCommodity = this.stateChart2.namesprice.find(name => name.id === parseInt(Commodityid));

        if (selectCommodity) {
            // console.log('Selected Commodity Name:', selectCommodity.name);
            this.stateChart2.selectedCommodityNameP= selectCommodity.name;  
        } else {
            console.log('Commodity not found');
        }
        this.checkFiltersReady();
    }

    
    checkFiltersReady() {
        // console.log("dthis.state.filtersReady ",this.state.filtersReady);
        // console.log("this.state.startDate ",this.state.startDate);
        // console.log("this.state.endDate ",this.state.endDate);
        // console.log("this.state.selectedCommodityName ",this.state.selectedCommodityName);
        if (this.state.startDate && this.state.endDate && this.state.selectedCommodityName) {
            this.state.filtersReady = true;  
            this.fetchData();  
        } else {
            this.state.filtersReady = false;  
        }
    }
}







function getColor(index) {
    const colors = [
        '#242120', '#36A2EB', '#FFCE56', '#FF5733', '#9B59B6', '#1ABC9C'
    ];
    return colors[index % colors.length]; // Cycle through a predefined set of colors
}


OwlReportingDashboard.template = "owl.OwlReportingDashboard";
OwlReportingDashboard.components = { KpiCard, ChartRenderer,CustomerCard};

registry.category('actions').add('dashboard.owl.new.registry', OwlReportingDashboard);
