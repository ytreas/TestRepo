
/** @odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard,CustomerCard } from "./kpi_card/kpi_card";
import { ChartRenderer2} from "./chart_renderer/chart_renderer2";

import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl;
export class OwlReportingDashboard2 extends Component {

    setup() {
        this.stateChart2  = owl.useState({
            fetchPriceData: { // State for chart data 2
                labels: [''],
                datasets: [{
                    label: ' Prices Arrivals',
                    data: [],
                    hoverOffset: 4,
                }]
            },
            TestData: null,
            namesprice: [],
            // selectedCommodity: '',
            selectedCommodityNameP : '',
            dateStartPrice: '',
            dateEndPrice: '',
            filtersReadyprice: false,
        });

        this.orm = useService("orm");
        this.chartRef = useRef(null);

        onWillStart(async () => {
            await this.fetchNames();
            await this.fetchData2();

        });
        onMounted(() => {
            this.initNepaliDatePicker();
            
        });
    }

    initNepaliDatePicker() {
        const self=this;
        const nepaliDateInputsPrices = document.getElementById('date_from_price');
        nepaliDateInputsPrices.nepaliDatePicker({
            onChange: (ev) => {  
                // console.log("Price - from date changed:", ev);
                self.onDateRangeChangefromPrices($(ev));  // Change dateStart (From Date)
            }
        });
    
        const nepaliDateInputsPrice = document.getElementById('date_to_price');
        nepaliDateInputsPrice.nepaliDatePicker({
            onChange: (ev) => {  
                // console.log("Price - to date changed:", ev);
                self.onDateRangeChangetoPrices($(ev));  // Change dateEnd (To Date)
            }
        });
    }

    async fetchNames() {
        try {
            // Fetching all commodity records from amp.commodity.master with id and name (product_id)
            const commodityMasterResult = await this.orm.searchRead("amp.commodity.master", [], ["id", "product_id"]);
            console.log("Fetched commodity master names:", commodityMasterResult);
       
            // Create a mapping of commodity ID to commodity name for fast lookup
            const commodityNameMap = {};
            commodityMasterResult.forEach(commodity => {
                commodityNameMap[commodity.id] = commodity.product_id[1]; // Assuming product_id[1] is the commodity name
            });
            console.log("Commodity name map:", commodityNameMap);
    
            const commodityNames = [];
    
         
            const priceResult = await this.orm.searchRead('amp.daily.price', [], ['commodity']);
            // console.log("Fetched daily price records:", priceResult);
    
            for (const priceEntry of priceResult) {
                const commodity = priceEntry.commodity;
                const commodityId = commodity[0]; 
    
                // console.log("Processing commodity ID:", commodityId);
                if (commodityNameMap[commodityId]) {
                    const commodityName = commodityNameMap[commodityId];
                    // console.log("Found commodity name:", commodityName);
    
                    commodityNames.push({
                        id: commodityId, 
                        name: commodityName 
                    });
                } else {
                    console.log("No name found for commodity ID:", commodityId);
                }
            }
    
            const uniqueNames = commodityNames.filter((value, index, self) =>
                index === self.findIndex((t) => t.id === value.id)
            );
            // console.log("Unique commodity names:", uniqueNames);

            this.stateChart2.namesprice = uniqueNames;
    
        } catch (error) {
            console.error("Error fetching commodity names:", error);
        }
    }
     

    async fetchData2() {
        try {
            if (!this.stateChart2.filtersReadyprice) return; 
    
            // console.log("this.state.filtersReady fetchData2", this.stateChart2.filtersReadyprice);
            let startdate = this.stateChart2.dateStartPrice;
            let enddate = this.stateChart2.dateEndPrice;
            let productName = this.stateChart2.selectedCommodityNameP;
    
            // console.log("date from fetchData2 ", startdate);
            // console.log("To date fetchData2", enddate);
            // console.log("Product Name fetchData2", productName);
            
            const filters = [
                ['current_date_bs', '>=', startdate], 
                ['current_date_bs', '<=', enddate],   
                ['commodity', '=', productName]
            ];
            
            const result = await this.orm.searchRead("amp.daily.price", filters, ["commodity", "current_date_bs", "avg_price"]);
            // console.log("Results", result);
    
            const groupedData = {};
            let commodityname = '';
    
            result.forEach(record => {
                const { commodity, current_date_bs, avg_price } = record;
                // console.log(`Processing record: commodity = ${commodity}, current_date_bs = ${current_date_bs}, avg_price = ${avg_price}`);
                const key = `${commodity}-${current_date_bs}`; 
                commodityname = commodity;
                if (!groupedData[key]) {
                    groupedData[key] = {
                        commodityname,
                        current_date_bs,
                        prices: [], 
                    };
                }
                groupedData[key].prices.push(avg_price);
            });
    
            // console.log("Grouped Data", groupedData);
    
            // Sort the grouped data based on date (current_date_bs)
            const sortedData = Object.values(groupedData).sort((a, b) => {
                return new Date(a.current_date_bs) - new Date(b.current_date_bs); // Ensure the dates are in ascending order
            });
    
            sortedData.forEach(data => {
                const { prices } = data;
                // Calculate the average of avg_price values
                const avgOfAvgPrice = prices.reduce((sum, price) => sum + price, 0) / prices.length;
                data.avg_price = avgOfAvgPrice;  // Set the calculated average of average prices
                // console.log(`Average of avg_price for ${data.commodityname} on ${data.current_date_bs}: ${avgOfAvgPrice}`);
            });
    
            // Prepare chart data with sorted labels
            this.stateChart2.fetchPriceData = {
                data: {
                    labels: sortedData.map(item => item.current_date_bs), // Sorted dates as labels
                    datasets: [
                        {
                            label: productName,
                            data: sortedData.map(item => item.avg_price), // Average prices
                            hoverOffset: 4,
                            backgroundColor: sortedData.map((_, index) => getColor(index)), // Color based on index
                        }
                    ]
                },
            };
    
            // console.log("Updated state with fetchPriceData:", this.stateChart2.fetchPriceData);
    
        } catch (error) {
            console.error("Error fetching chart data:", error);
        }
    }
    onPrint() {
        const defaultReportName = "Arrival Price - Chart"; // Customize this name
        document.title = defaultReportName;
        setTimeout(() => {
            window.print();
        }, 500);
    }

    onDateRangeChangetoPrices(event = null) {
        // console.log("Date to price selected", event);
        if (event) {
            // Set the `dateEnd` only from the "to date" field (date_to_price)
            this.stateChart2.dateEndPrice = event[0].bs;  // Set the "end date"
        }
        this.checkFiltersReady();
    }
    
    onDateRangeChangefromPrices(event = null) {
        // console.log("Date from price selected", event);
        if (event) {
            // Set the `dateStart` only from the "from date" field (date_from_price)
            this.stateChart2.dateStartPrice = event[0].bs;  // Set the "start date"
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
        if (this.stateChart2.dateStartPrice && this.stateChart2.dateEndPrice && this.stateChart2.selectedCommodityNameP) {
            this.stateChart2.filtersReadyprice = true;  
            this.fetchData2();  
        } else {
            this.stateChart2.filtersReadyprice = false;  
        }
    }
}

function getColor(index) {
    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#FF5733', '#9B59B6', '#1ABC9C'
    ];
    return colors[index % colors.length]; // Cycle through a predefined set of colors
}

OwlReportingDashboard2.template = "owl.OwlReportingDashboard2";
OwlReportingDashboard2.components = { KpiCard,ChartRenderer2,CustomerCard};
registry.category('actions').add('dashboard2.owl.new.registry', OwlReportingDashboard2);








