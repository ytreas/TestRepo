/** @odoo-module */

import { registry } from "@web/core/registry"
import { TransportKpiCard } from "./kpi_card/kpi_card"
import { TransportChartRenderer } from "./chart_renderer/chart_renderer"
import { useService } from "@web/core/utils/hooks"
import { PieChart } from "./chart_renderer/pie_chart"
const { Component, useState, onWillStart , onMounted ,useEffect } = owl


export class OwlTransportDashboard extends Component {
    setup(){
        this.user = useService("user");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.setSelectionMode = this.setSelectionMode.bind(this);
        this.viewStateOrder = this.viewStateOrder.bind(this); 
        // this.company = this.env.session.user_context.company_id 
        //               || this.env.session.user_context.allowed_company_ids[0];
        this.state = useState({
            selection_mode: 'quick',
            period: 7,  // default period in days
            companyId: null,
            latestOrder :[],
            currentPage: 1,   
            totalPages: 1,  
            pageSize: 2,


            ShipMentCount:[
                { status: "Dispatched", count: 0 },
                { status: "In Transit", count: 0 },
                { status: "Delivered", count: 0 },
                { status: "Delayed", count: 0 },
                { status: "Cancelled", count: 0 }
            ],
            total_orders: {
                value:0,
                percentage:0,
            },
            delivered_orders: {
                value:0,
                percentage:0,
            },
            transit: {
                value:0,
                percentage:0,
            },
            delayed_orders: {
                value:0,
                percentage:0,
            },
            vehicle_use: {
                value:0,
                percentage:0,
            },
            average_delivered: {
                value:0,
                percentage:0,
            },
            shipmentData: { 
                datasets: [{
                    label: 'Shipments',
                    backgroundColor: '#42A5F5',
                    data: [],
                }]
            },
            // shipmentData: { 
            //     // labels: [''],
            //     datasets: [],
            //     data:[]
            // },
            delayData:{
                  datasets: [{
                    label: 'Delay Reason',
                    backgroundColor: '#42A5F5',
                    data: [],
                    hoverOffset: 4,
                  }]
            },
            startDate: '',
            endDate: '',
            filtersReady: false,
        })
      

        onWillStart(async ()=>{
            if (this.state.selection_mode === 'quick') {
                this.getDates()
            }
            this.state.companyId = this.user.context.company_id || 
                           (this.user.context.allowed_company_ids && this.user.context.allowed_company_ids[0]) || 
                           null;

            if (!this.state.companyId) {
                console.warn("No company ID found in user context");
                // You might want to add fallback logic here
            }
            await this.getLatestRecord(1);
            await this.getShipmentCount();
        })
        onMounted(() => {
            if (this.state.selection_mode === 'custom') {
                this.initNepaliDatePicker();
            }   
        });
        useEffect(() => {
            if (this.state.selection_mode === 'custom') {
                this.initNepaliDatePicker();
            }
        }, () => [this.state.selection_mode]);
    }
    setSelectionMode(mode) {
        console.log("Setting selection mode to:", mode);
        this.state.selection_mode = mode;
        if (mode === "custom") {
            this.state.period = 0;
        } else {
            this.state.startDate = "";
            this.state.endDate = "";
        }
    }
    initNepaliDatePicker() {
        const self=this;
        const nepaliStartdate = document.getElementById('custom_start_date');
        nepaliStartdate.nepaliDatePicker({
            onChange:(ev)=>{  
                self.onDateRangeChangefrom($(ev));
            } 
        });
        const nepaliEnddate = document.getElementById('custom_end_date');
        nepaliEnddate.nepaliDatePicker({
            onChange:(ev)=>{    
                self.onDateRangeChangeto($(ev));
            }
            
        });
    }
    async onChangePeriod(){
        this.getDates();
        // await this.getTotalOrders();
        // await this.getDoneOrders();
        // await this.getTransitOrders();
        // await this.getDelayedOrders();
        // await this.getTotalVehicle();
        // await this.getAvgDeliveryTime();

        await this.getShipmentData();
        await this.getLatestRecord(1);
        await this.getShipmentCount();

        
    }
    async viewStateOrder(state){
        let domain = []
        if (state == 'delayed'){
            domain = [['has_delayed_pods', '=', true]]
        }else{
            domain = [['state', '=', state]]
        }
        let list_view = await this.orm.searchRead(
            "ir.model.data",
            [
                ['module', '=', 'transport_management'],
                ['name', '=', 'view_transport_order_tree']
            ],
            ['res_id']
        );
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: state.toUpperCase() +" " + "Order",
            res_model: "transport.order",
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"], // use list_view id or false
                [false, "form"],
            ]
        })
      
    }
   
    getDates(){ 
        this.state.current_date = moment().subtract(this.state.period, 'days').format('L')
        this.state.previous_date = moment().subtract(this.state.period * 2, 'days').format('L')
        this.getTotalOrders();
        this.getDoneOrders()
        this.getTransitOrders();
        this.getDelayedOrders();
        this.getTotalVehicle();
        this.getAvgDeliveryTime();

        this.getShipmentData()
        console.log("CUrrent and Previous Date",this.state.current_date,this.state.previous_date)
    }
   

    async FetchOrders(startdate, enddate, stateFilter = null) {
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;
        result = await this.orm.searchCount("transport.order", filters);

        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevResult = 0;
        if (prevStartDate && prevEndDate) {
            const prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
            prevResult = await this.orm.searchCount("transport.order", prevFilters);
        }
        // console.log("Current Period:", startdate, "to", enddate);
        // console.log("Previous Period:", prevStartDate, "to", prevEndDate);
        // console.log("Current Result:", result, "Previous Result:", prevResult);
        // Calculate the increase rate
        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.total_orders.value =  result ?? 0;
        this.state.total_orders.percentage = increaseRate ?? 0;
    }

    async FetchTransitOrders(startdate, enddate, stateFilter = null) {
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;
        result = await this.orm.searchCount("transport.order",filters);
        console.log("Final filters:", JSON.stringify(filters));
        
        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevResult = 0;
        if (prevStartDate && prevEndDate) {
            const prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
            prevResult = await this.orm.searchCount("transport.order", prevFilters);
        }
        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.transit.value =  result ?? 0;
        this.state.transit.percentage = increaseRate ?? 0;
    }

    async FetchDelayedOrders(startdate, enddate, stateFilter = null) {
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;
        result = await this.orm.searchCount("transport.order", filters);

        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevResult = 0;
        if (prevStartDate && prevEndDate) {
            const prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
            prevResult = await this.orm.searchCount("transport.order", prevFilters);
        }
        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.delayed_orders.value =  result ?? 0;
        this.state.delayed_orders.percentage = increaseRate ?? 0;
    }
    async FetchDoneOrders(startdate, enddate, stateFilter = null) {
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;
        result = await this.orm.searchCount("transport.order", filters);

        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevResult = 0;
        if (prevStartDate && prevEndDate) {
            const prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
            prevResult = await this.orm.searchCount("transport.order", prevFilters);
        }
        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.delivered_orders.value =  result ?? 0;
        this.state.delivered_orders.percentage = increaseRate ?? 0;
    }
    async FetchTotalVehicle(startdate, enddate, stateFilter = null) {
        console.log("FetchTotalVehicleFetchTotalVehicleFetchTotalVehicleFetchTotalVehicle")
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;

        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevFilters = [];
        if (prevStartDate && prevEndDate) {
            prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
        }

        const orders = await this.orm.searchRead("transport.order", filters, ['assignment_ids']);
     
        const total_vehicle = await this.orm.searchCount("vehicle.number", [['company_id', '=', this.state.companyId]]);
        // Flatten all assignment IDs from all orders
        const assignmentIds = orders.flatMap(order => order.assignment_ids).filter(Boolean);

        let vehicles = [];
        if (assignmentIds.length > 0) {
            const assignments = await this.orm.searchRead(
                'transport.assignment',
                [['id', 'in', assignmentIds]],
                ['vehicle_id']
            );

            // Extract vehicle IDs
            vehicles = assignments
                .map(a => a.vehicle_id?.[0])
                .filter(Boolean);
        }
        const uniqueVehicleIds = [...new Set(vehicles)];
        const totalVehiclesInUse = uniqueVehicleIds.length;

        // previous vehicle used numbers
        const prevOrders = await this.orm.searchRead("transport.order", prevFilters, ['assignment_ids']);
        const prev_assignmentIds = prevOrders.flatMap(order => order.assignment_ids).filter(Boolean);
        let prev_vehicles = [];
        if (prev_assignmentIds.length > 0) {
            const assignments = await this.orm.searchRead(
                'transport.assignment',
                [['id', 'in', prev_assignmentIds]],
                ['vehicle_id']
            );
            prev_vehicles = assignments
                .map(a => a.vehicle_id?.[0])
                .filter(Boolean);
        }

        const prev_uniqueVehicleIds = [...new Set(prev_vehicles)];
        const prev_totalVehiclesInUse = prev_uniqueVehicleIds.length;
        result = totalVehiclesInUse;
        let prevResult = prev_totalVehiclesInUse;

        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.vehicle_use.value =  result ?? 0;
        this.state.vehicle_use.percentage = increaseRate ?? 0;

    }
    async FetchAvgDeliveryTime(startdate, enddate, stateFilter = null) {
        const filters = buildStateFilters(startdate, enddate, stateFilter,this.state.companyId);
        let result = 0;
        let startdateAD = NepaliFunctions.BS2AD(startdate); 
        let startdateObj = new Date(startdateAD) 
        let enddateAD = NepaliFunctions.BS2AD(enddate);
        let enddateObj = new Date(enddateAD)
        const durationDays = Math.floor((enddateObj - startdateObj) / (1000 * 60 * 60 * 24)) + 1;

        const { prevStartDate, prevEndDate } = calculatePreviousPeriod(startdateAD, durationDays);
        console.log("Previous Start Date in BS:", prevStartDate, "Previous End Date in BS:", prevEndDate, calculatePreviousPeriod(startdateAD, durationDays));
        let prevFilters = [];
        if (prevStartDate && prevEndDate) {
            prevFilters = buildStateFilters(prevStartDate, prevEndDate, stateFilter,this.state.companyId);
        }

        const orders = await this.orm.searchRead("transport.order", filters, ['scheduled_date_to', 'actual_delivery_date']);
        let totalDays = 0;
        let count = 0;
        for (const order of orders) {
            const expected = new Date(order.scheduled_date_to);
            const actual = new Date(order.actual_delivery_date);

            if (!isNaN(expected) && !isNaN(actual)) {
                const diffDays = (actual - expected) / (1000 * 60 * 60 * 24);
                totalDays += diffDays;
                count += 1;
            }
        }
        result = count > 0 ? Number((totalDays / count).toFixed(2)) : 0;

        const prevorders = await this.orm.searchRead("transport.order", prevFilters, ['scheduled_date_to', 'actual_delivery_date']);
        let prevtotalDays = 0;
        let prevcount = 0;
        for (const order of prevorders) {
            const expected = new Date(order.scheduled_date_to);
            const actual = new Date(order.actual_delivery_date);

            if (!isNaN(expected) && !isNaN(actual)) {
                const diffDays = (actual - expected) / (1000 * 60 * 60 * 24);
                prevtotalDays += diffDays;
                prevcount += 1;
            }
        }
        let prevResult = prevcount > 0 ? Number((prevtotalDays / prevcount).toFixed(2)) : 0;
        const increaseRate = calculateIncreaseRate(result, prevResult);
        this.state.average_delivered.value =  result ?? 0;
        this.state.average_delivered.percentage = increaseRate ?? 0;
    }

    async getOrders(startDate, endDate, stateFilter = null) {
        const startdateBS = convertToNepaliDate(startDate);
        const prevstartBS = convertToNepaliDate(endDate);

        const today_date = NepaliFunctions.AD2BS(new Date().toISOString().split('T')[0]);
        const filters = buildStateFilters(startdateBS, today_date, stateFilter, this.state.companyId);
        let prevFilters = [];
        if (startdateBS && prevstartBS) {
            prevFilters = buildStateFilters(prevstartBS, startdateBS, stateFilter, this.state.companyId);
        }
        let result = 0;
        let prevResult = 0;

        if ( stateFilter.includes("average_delivery_time")){
            const orders = await this.orm.searchRead("transport.order", filters, ['scheduled_date_to', 'actual_delivery_date']);

            let totalDays = 0;
            let count = 0;

            for (const order of orders) {
                const expected = new Date(order.scheduled_date_to);
                const actual = new Date(order.actual_delivery_date);

                if (!isNaN(expected) && !isNaN(actual)) {
                    const diffDays = (actual - expected) / (1000 * 60 * 60 * 24);
                    totalDays += diffDays;
                    count += 1;
                }
            }
            result = count > 0 ? Number((totalDays / count).toFixed(2)) : 0;

            const prevorders = await this.orm.searchRead("transport.order", prevFilters, ['scheduled_date_to', 'actual_delivery_date']);
            let prevtotalDays = 0;
            let prevcount = 0;

            for (const order of prevorders) {
                const expected = new Date(order.scheduled_date_to);
                const actual = new Date(order.actual_delivery_date);

                if (!isNaN(expected) && !isNaN(actual)) {
                    const diffDays = (actual - expected) / (1000 * 60 * 60 * 24);
                    prevtotalDays += diffDays;
                    prevcount += 1;
                }
            }
            prevResult = prevcount > 0 ? Number((prevtotalDays / prevcount).toFixed(2)) : 0;
        }else if(stateFilter.includes('vehicle')){
            const orders = await this.orm.searchRead("transport.order", filters, ['assignment_ids']);
            const total_vehicle = await this.orm.searchCount("vehicle.number", [['company_id', '=', this.state.companyId]]);
            // Flatten all assignment IDs from all orders
            const assignmentIds = orders.flatMap(order => order.assignment_ids).filter(Boolean);

            let vehicles = [];
            if (assignmentIds.length > 0) {
                const assignments = await this.orm.searchRead(
                    'transport.assignment',
                    [['id', 'in', assignmentIds]],
                    ['vehicle_id']
                );

                // Extract vehicle IDs
                vehicles = assignments
                    .map(a => a.vehicle_id?.[0])
                    .filter(Boolean);
            }
            const uniqueVehicleIds = [...new Set(vehicles)];
            const totalVehiclesInUse = uniqueVehicleIds.length;

            // previous vehicle used numbers
            const prevOrders = await this.orm.searchRead("transport.order", prevFilters, ['assignment_ids']);
            const prev_assignmentIds = prevOrders.flatMap(order => order.assignment_ids).filter(Boolean);
            let prev_vehicles = [];
            if (prev_assignmentIds.length > 0) {
                const assignments = await this.orm.searchRead(
                    'transport.assignment',
                    [['id', 'in', prev_assignmentIds]],
                    ['vehicle_id']
                );
                prev_vehicles = assignments
                    .map(a => a.vehicle_id?.[0])
                    .filter(Boolean);
            }

            const prev_uniqueVehicleIds = [...new Set(prev_vehicles)];
            const prev_totalVehiclesInUse = prev_uniqueVehicleIds.length;

            result = totalVehiclesInUse;
            prevResult = prev_totalVehiclesInUse; 
        }else{
            result = await this.orm.searchCount("transport.order", filters);
            prevResult = await this.orm.searchCount("transport.order", prevFilters);
        } 
        return {
            result: result ?? 0,                     // Use 0 if result is undefined or null
            prevResult: prevResult ?? 0,  
            increaseRate: calculateIncreaseRate(result, prevResult)
        };
    }

    async getTotalOrders() {
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date,["all"]);
        // return { result, prevResult, increaseRate };
        this.state.total_orders.value = result;
        this.state.total_orders.percentage = increaseRate;
        // console.log("Company _id", this.companyId);
    }
    async getDoneOrders() {
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date, ["delivered"]);
        console.log(`Done Orders: ${result}, Previous Done Orders: ${prevResult}, Increase Rate: ${increaseRate}`);
        // return { result, prevResult, increaseRate };
        this.state.delivered_orders.value = result;
        this.state.delivered_orders.percentage = increaseRate;
        console.log("Company _id", this.state.companyId);
    }
    async getTransitOrders() {
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date, ["in_transit"]);
        this.state.transit.value = result;
        this.state.transit.percentage = increaseRate;
    }
    async getDelayedOrders() {
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date, ["delayed"]);
        this.state.delayed_orders.value = result;
        this.state.delayed_orders.percentage = increaseRate;
    }
    async getTotalVehicle() {
        console.log("THis is called getTotalVehiclegetTotalVehiclegetTotalVehiclegetTotalVehiclegetTotalVehicle")
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date, ["vehicle"]);
        this.state.vehicle_use.value = result;
        this.state.vehicle_use.percentage = increaseRate;
    }
    async getAvgDeliveryTime() {
        const { result, prevResult, increaseRate } = await this.getOrders(this.state.current_date, this.state.previous_date, ["average_delivery_time"]);
        this.state.average_delivered.value = result;
        this.state.average_delivered.percentage = increaseRate;
    }
    async fetchShipmentData(startDate, endDate) {
        console.log("Fetching shipment data for:", startDate, endDate);
        const filters =  [
            ['order_date_bs', '>=', startDate],
            ['order_date_bs', '<=', endDate],
            ['company_id','=', this.state.companyId],
        ];
        try {
            const orders = await this.orm.searchRead("transport.order", filters);
            console.log("Fetched shipment data:", orders);
            const ordersPerDay = orders.reduce((acc, order) => {
                const date = order.order_date_bs;
                acc[date] = (acc[date] || 0) + 1;
                return acc;
            }, {});
            const sortedOrders = Object.entries(ordersPerDay)
                .sort(([dateA], [dateB]) => dateA.localeCompare(dateB))
                .map(([date, count]) => ({ date, count }));



            //$$$$$$$$$$$$$
            // const grouped = {
            //     confirm: {},
            //     delivered: {}
            // };

            // for (const order of orders) {
            //     const date = order.order_date_bs;
            //     const state = order.state;

            //     if (state === "confirmed") {
            //         grouped.confirm[date] = (grouped.confirm[date] || 0) + 1;
            //     }
            //     if (state === "delivered") {
            //         grouped.delivered[date] = (grouped.delivered[date] || 0) + 1;
            //     }
            // }

            // const allDates = Array.from(
            //     new Set([...Object.keys(grouped.confirm), ...Object.keys(grouped.delivered)])
            // ).sort((a, b) => a.localeCompare(b));

            // const confirmedData = allDates.map(date => ({
            //     x: date,
            //     y: grouped.confirm[date] || 0
            // }));

            // const deliveredData = allDates.map(date => ({
            //     x: date,
            //     y: grouped.delivered[date] || 0
            // }));
            // console.log("!!!!!!!!!!!!!!!!!!!!!!!!!!",allDates)
            // this.state.shipmentData = {
            //     data: {
            //         labels: allDates,
            //         datasets: [
            //             {
            //                 label: 'Confirmed Orders',
            //                 data: confirmedData,
            //                 backgroundColor: 'rgba(0, 123, 255, 0.2)',
            //                 borderColor: '#007bff',
            //                 fill: false,
            //                 tension: 0.3,
            //             },
            //             {
            //                 label: 'Delivered Orders',
            //                 data: deliveredData,
            //                 backgroundColor: 'rgba(40, 167, 69, 0.2)',
            //                 borderColor: '#28a745',
            //                 fill: false,
            //                 tension: 0.3,
            //             }
            //         ]
            //     }
            // };

            //###################

            this.state.shipmentData = {
                data: {
                    labels: sortedOrders.map(item => item.date), 
                    datasets: [
                        {
                            data: sortedOrders.map(item => ({
                                x: item.date,
                                y: item.count,
                                
                            })),
                            hoverOffset: 4,
                        }
                    ]
                },
            };
            // this.state.shipmentData.labels = sortedOrders.map(order => order.date);
            // this.state.shipmentData.datasets[0].data = sortedOrders.map(item => item.count);
            console.log("Shipment Data :", this.state.shipmentData);

            // this.state.shipmentData.labels = orders.map(order => order.name);
            // this.state.shipmentData.datasets[0].data = orders.map(order => order.amount);
        } catch (error) {
            console.error("Error fetching shipment data:", error);
            this.state.shipmentData = {
                data: {
                    labels: [],
                    datasets: [{ data: [] }],
                }
            };
        }
    }
    async getShipmentData() {
        const startdateBS = convertToNepaliDate(this.state.current_date);
        const today_date = NepaliFunctions.AD2BS(new Date().toISOString().split('T')[0]);
        await this.fetchShipmentData(startdateBS, today_date);
        await this.fetchDelayReasonData(startdateBS,today_date);
    }

    async fetchDelayReasonData(startDate, endDate) {
        console.log("INside the fetchDelay Data")
        const filters = [
            ['pod_date_bs', '>=', startDate],
            ['pod_date_bs', '<=', endDate],
            ['company_id', '=', this.state.companyId],
        ];
        
        try {
            const delayReasons = await this.orm.searchRead("transport.pod", filters, ['late_type']);
            console.log("REsult",delayReasons)
            // Group by delay_type and count occurrences
            const delaysByType = delayReasons.reduce((acc, reason) => {
                const type = reason.late_type;
                if (type && type !== 'none') {  
                    acc[type] = (acc[type] || 0) + 1;
                }
                return acc;
            }, {});

            // Convert to array format
            const delayData = Object.entries(delaysByType)
                .map(([type, count]) => ({ type, count }));
            console.log("delayData",delayData)
            const typeColors = {
                'WEATHER': '#FF6384',
                'TRAFFIC': '#36A2EB',
                'ADDRESS': '#FFCE56',
                'SYSTEM': '#4BC0C0',
                'OTHERS': '#9966FF',
                'default': '#999999'
            };

            const labels = delayData.map(item => item.type.toUpperCase());
            // Prepare pie chart data
            this.state.delayData = {
                data: {
                    labels: labels,
                    datasets: [{
                        data: delayData.map(item => item.count),
                        backgroundColor: labels.map(label => typeColors[label] || typeColors.default),
                        borderColor: '#fff',
                        borderWidth: 1,
                    }]
                }
            };
            
        } catch (error) {
            console.error("Error fetching delay reasons:", error);
            this.state.delayData = {
                data: {
                    labels: [],
                    datasets: [{ data: [] }],
                }
            };
        }
    }
    getStatusMapping(state) {
        const mapping = {
            'draft': 'Draft',
            'confirmed': 'Dispatched',  // Map 'confirmed' to 'Dispatched'
            'process': 'Process',       // If 'process' is required, keep it as 'Process'
            'in_transit': 'In Transit',
            'delivered': 'Delivered',
            'cancel': 'Cancelled',
        };
        return mapping[state] || 'Unknown';  // Default to 'Unknown' if not found
    }
    async getShipmentCount(){
        const filter = [
            ['company_id','=', this.state.companyId],
        ]
        const orders = await this.orm.searchRead("transport.order", filter);
        // Group orders by the status mapping and count them
        const groupedByState = orders.reduce((acc, order) => {
            const state = order.state;  // 'state' is the backend value
            const status = this.getStatusMapping(state); 
            
            if (!acc[status]) {
                acc[status] = 0; 
            }
            acc[status] += 1;  // Increment the count for this status
            return acc;
        }, {});

        // Now update the `ShipMentCount` state based on the grouped data
        this.state.ShipMentCount = this.state.ShipMentCount.map((item,index )=> {
            const stateKey = item.status;  // Get the user-friendly status name
            item.count = groupedByState[stateKey] || 0;  // If state doesn't exist in grouped data, default to 0
            item.id = index;
            return item;
        });
        // console.log(" this.state.ShipMentCount",this.state.ShipMentCount)
    }
    async getLatestRecord(page=1) {
        
        const today = new Date();
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(today.getDate() - 7);
        const formattedDate = today.toISOString().split('T')[0];
        const SevenformattedDate =sevenDaysAgo.toISOString().split('T')[0];
        const nepaliToday = NepaliFunctions.AD2BS(formattedDate); 
        const sevenDays = NepaliFunctions.AD2BS(SevenformattedDate);

        const filters = [
            ['update_date_bs', '>=',sevenDays ],
            ['update_date_bs', '<=',nepaliToday ],
            ['company_id','=', this.state.companyId],
        ]
        const { pageSize } = this.state;
        const limit = pageSize;
        const offset = (page - 1) * pageSize;

        const orders = await this.orm.searchRead("transport.order", filters, 
            ['id','tracking_number','customer_name','pickup_location','delivery_location','state','update_period'],{
            limit: limit,
            offset: offset,});

        const totalRecords = await this.orm.searchCount("transport.order", filters);
        const totalPages = Math.ceil(totalRecords / pageSize);

        console.log("TTTTTTTTTTTTTTTT",orders)
        this.state.latestOrder = orders;
        this.state.currentPage = page;
        this.state.totalPages = totalPages;
    }
    // Navigate to the next page
    async nextPage() {
        if (this.state.currentPage < this.state.totalPages) {
            await this.getLatestRecord(this.state.currentPage + 1);
        }
    }

    // Navigate to the previous page
    async prevPage() {
        if (this.state.currentPage > 1) {
            await this.getLatestRecord(this.state.currentPage - 1);
        }
    }

    onDateRangeChangefrom(event=null) {
        this.state.startDate = event[0].bs
        this.checkFiltersReady();
    }
    onDateRangeChangeto(event=null) {
        this.state.endDate = event[0].bs
        this.checkFiltersReady();
    }
    checkFiltersReady() {
        if (this.state.startDate && this.state.endDate) {
            this.state.filtersReady = true;  
            // this.fetchData();  
            this.FetchOrders(this.state.startDate, this.state.endDate,["all"]);
            this.FetchTransitOrders(this.state.startDate, this.state.endDate,"['in_transit']");
            this.FetchDelayedOrders(this.state.startDate, this.state.endDate,"['delayed']");
            this.FetchDoneOrders(this.state.startDate, this.state.endDate,"['delivered']");
            this.FetchTotalVehicle(this.state.startDate, this.state.endDate,"['vehicle']");
            this.FetchAvgDeliveryTime(this.state.startDate, this.state.endDate,"['average_delivery_time']");


            this.fetchShipmentData(this.state.startDate, this.state.endDate);
            this.fetchDelayReasonData(this.state.startDate, this.state.endDate);
        } else {
            this.state.filtersReady = false;  
        }
    }
    }

// Utility function to convert the date into the required format
function convertToDateFormat(date) {
    if (!date) {
        console.error("Invalid date passed to convertToDateFormat:", date);
        return null;  
    }
    const parts = date.split('/'); 
    return `${parts[2]}-${parts[0]}-${parts[1]}`;
}

function convertToNepaliDate(date) {
    if (!date) {
        console.error("Invalid date passed to convertToNepaliDate:", date);
        return null; 
    }
    const formattedDate = convertToDateFormat(date);
    if (!formattedDate) {
        console.error("Date format conversion failed:", date);
        return null;
    }
    return NepaliFunctions.AD2BS(formattedDate); 
}

function buildDateFilters(startDateBS, endDateBS,companyId = null) {
    return [
        ['order_date_bs', '>=', startDateBS],
        ['order_date_bs', '<=', endDateBS],
        ['company_id','=', companyId],
    ];
}


// Utility function to build filters with optional state filter (e.g., state == "done")
function buildStateFilters(startDateBS, endDateBS, stateFilter = null, companyId = null) {
   const custom_filter = buildDateFilters(startDateBS, endDateBS, companyId);
    console.log("INside Build Filters",stateFilter,typeof(stateFilter),custom_filter,typeof(custom_filter));
    // if(stateFilter.includes('average_delivery_time')){
    //     console.log(`$$$$$$$$$$$$$$$$$$$$$$$$$$`);
    // }
    if (typeof stateFilter === 'string') {
        try {
            // Replace single quotes with double quotes and parse
            stateFilter = JSON.parse(stateFilter.replace(/'/g, '"'));
        } catch (e) {
            // If parsing fails, just wrap the string into an array
            stateFilter = [stateFilter];
        }
    }
    if (stateFilter.includes('delayed')) {
        custom_filter.push(['pod_id.delayed', '=', true]);
    } else if (stateFilter.includes('vehicle')) {
        custom_filter.push(['assignment_ids.vehicle_id', '!=', false]);
        // filters.push(['state', 'in', ['confirmed', 'in_transit']]);  // adjust state values to your case
    }else if (stateFilter.includes('average_delivery_time')) {
        custom_filter.push(['scheduled_date_to', '!=', false]);
        custom_filter.push(['pod_id.pod_date', '!=', false]);
    }else if(stateFilter.includes('all')){
        custom_filter.push(['state', 'in', ['confirmed', 'process', 'in_transit', 'delivered']]);
    } else {
        custom_filter.push(['state', 'in', stateFilter]);
    }
    // console.log("Filters built:", filters);
    return custom_filter;

}

// Utility function to calculate increase rate
function calculateIncreaseRate(result, prevResult) {
    let increaseRate = 0;
    if (prevResult > 0) {
        increaseRate = ((result - prevResult) / prevResult) * 100;
    } else if (result > 0) {
        increaseRate = 100;
    }
    return increaseRate;
}


function calculatePreviousPeriod(startDate, durationDays) {
    console.log("Calculating previous period for startDate:", startDate, "and durationDays:", durationDays);
    let prevEndDate = new Date(startDate);
    prevEndDate.setDate(prevEndDate.getDate() - 1);

    let prevStartDate = new Date(prevEndDate);
    prevStartDate.setDate(prevStartDate.getDate() - durationDays + 1);

    let formatted_prevStartDate = formatDateToYMD(prevStartDate);
    let formatted_prevEndDate = formatDateToYMD(prevEndDate);
    let prevstartBs = NepaliFunctions.AD2BS(formatted_prevStartDate);
    let prevendBs = NepaliFunctions.AD2BS(formatted_prevEndDate);
    console.log("Previous Start Date in BS:", prevstartBs, "Previous End Date in BS:", prevendBs);
    return {
        prevStartDate: prevstartBs,
        prevEndDate: prevendBs,
    };
}
function formatDateToYMD(dateObj) {
    const yyyy = dateObj.getFullYear();
    const mm = String(dateObj.getMonth() + 1).padStart(2, '0'); // JS months are 0-based
    const dd = String(dateObj.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

OwlTransportDashboard.template = "owl.OwlTransportDashboard"
OwlTransportDashboard.components = { TransportKpiCard, TransportChartRenderer ,PieChart }

registry.category("actions").add("owl.transport_dashboard", OwlTransportDashboard)





// async fetchData() {
//         try {
//             if (this.env.company) {
//                 this.companyId = this.env.company.id;
//                 console.log("Company ID:", this.companyId);
//             } else {
//                 console.error("Company info is not available.");
//             }
//             if (!this.state.filtersReady) return; 
    
//             let startdate = this.state.startDate;
//             let enddate = this.state.endDate;
//             let result = 0;
//             let prevresult = 0;


//             if (startdate && enddate) {
//                 const filters = [
//                     ['order_date_bs', '>=', startdate], 
//                     ['order_date_bs', '<=', enddate],            
//                 ];
//                 result = await this.orm.searchCount("transport.order",filters);
//             }else{
//                 alert("Please select a valid date range.");
//                 return;
//             }

//             let startdateAD = NepaliFunctions.BS2AD(startdate); 
//             let startdateObj = new Date(startdateAD) 
//             let enddateAD = NepaliFunctions.BS2AD(enddate);
//             let enddateObj = new Date(enddateAD)


//             // console.log("Start Date (AD):", startdateAD, "Start Date (Obj):", startdateObj);
//             // Calculate duration in days (inclusive)
//             const durationDays = Math.floor((enddateObj - startdateObj) / (1000*60*60*24)) + 1;
//             console.log("Duration Days:", durationDays);

//             // Calculate previous period end date (day before current start)
//             let prevEndDate = new Date(startdateAD);
//             prevEndDate.setDate(prevEndDate.getDate() - 1);

//             // Calculate previous period start date (prevEndDate minus durationDays minus 1)
//             let prevStartDate = new Date(prevEndDate);
//             prevStartDate.setDate(prevStartDate.getDate() - durationDays + 1);

//             function formatDateToYMD(dateObj) {
//                 const yyyy = dateObj.getFullYear();
//                 const mm = String(dateObj.getMonth() + 1).padStart(2, '0'); // JS months are 0-based
//                 const dd = String(dateObj.getDate()).padStart(2, '0');
//                 return `${yyyy}-${mm}-${dd}`;
//             }
    
//             console.log("Previous prevStartDate:", prevStartDate,typeof(prevEndDate));
//             console.log("Previous prevEndDate:", prevEndDate,typeof(prevEndDate));
//             // console.log("Current startdate:", Math.floor((prevEndDate - prevStartDate) / (1000*60*60*24)) + 1);
//             let formatted_prevStartDate = formatDateToYMD(prevStartDate);
//             let formatted_prevEndDate = formatDateToYMD(prevEndDate);
//             // console.log("Formatted Previous Start Date:", formatted_prevStartDate);
//             let prevstartBs = NepaliFunctions.AD2BS(formatted_prevStartDate);
//             let prevendBs = NepaliFunctions.AD2BS(formatted_prevEndDate);
    
//             console.log("Previous Start Date in BS:", prevstartBs,"Previous End Date in BS:", prevendBs);

//             // console.log("Current Period:", startdate.toISOString(), "to", enddate.toISOString());
//             // console.log("Previous Period:", prevStartDate.toISOString(), "to", prevEndDate.toISOString());
//             let increase_rate = 0;
//             if (prevstartBs && prevendBs) {
//                 const filters = [
//                 ['order_date_bs', '>=', prevstartBs], 
//                 ['order_date_bs', '<=', prevendBs],            
//                 ];
//                 prevresult = await this.orm.searchCount("transport.order",filters);
//                 if (prevresult > 0) {
//                     increase_rate = ((result - prevresult) / prevresult) * 100;
//                 } else if (result > 0) {
//                     increase_rate = 100; // or some custom logic when there were 0 in the previous period
//                 } else {
//                     increase_rate = 0;
//                 }
//             }else{
//                 alert("Please select a valid date range.");
//             }
//             console.log("Current ResultOne:", result, "Previous Resultpme:", prevresult, "Increase Rate:", increase_rate);
//             this.state.total_orders.value = result;
//             this.state.total_orders.percentage = increase_rate;
//         } catch (error) {
//             console.error("Error fetching data:", error);
//         }
//     }



 // async getTotalOrders(){
    //     const formatCurrDate= convertToDateFormat(this.state.current_date)
    //     const formatPrevDate = convertToDateFormat(this.state.previous_date)
    //     const startdateBS = NepaliFunctions.AD2BS(formatCurrDate);
    //     // console.log("Current Date in BS:", startdateBS)
    //     const prevstartBS = NepaliFunctions.AD2BS(formatPrevDate);
    //     // console.log("Previous Date in BS:", typeof(prevstartBS))
    
    //     const today_date = NepaliFunctions.AD2BS(new Date().toISOString().split('T')[0]);
    //     // console.log("Today's Date in BS:", today_date)

    //     let result = 0;
    //     let prevresult = 0;
    //     let increase_rate = 0;
    //     if (startdateBS && prevstartBS) {
    //         const filters = [
    //             ['order_date_bs', '>=', startdateBS], 
    //             ['order_date_bs', '<=', today_date],            
    //         ];
    //         result = await this.orm.searchCount("transport.order",filters);
    //     }
    //     if (startdateBS && prevstartBS) {
    //         const filters = [
    //             ['order_date_bs', '>=', prevstartBS], 
    //             ['order_date_bs', '<=', startdateBS],            
    //         ];
    //         prevresult = await this.orm.searchCount("transport.order",filters);
    //     }
    //     if (prevresult > 0) {
    //         increase_rate = ((result - prevresult) / prevresult) * 100;
    //     } else if (result > 0) {
    //         increase_rate = 100; 
    //     } else {
    //         increase_rate = 0;
    //     }
    // }