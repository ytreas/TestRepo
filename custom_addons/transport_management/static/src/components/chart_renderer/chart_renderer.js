/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted, useEffect, onWillUnmount } = owl

export class TransportChartRenderer extends Component {
    static props = {
        config: Object,
        type: String,
        title: String,
    };

    setup() {
        this.chartRef = useRef("chart")
        console.log("ChartRenderer setup called", this.props.config);
        
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })
        
        useEffect(() => {
            this.renderChart()
        }, () => [this.props.config])
        
        onMounted(() => {
            console.log("ChartRenderer onMounted props:", this.props.config);
        });
        
        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy()
            }
        })
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        
        const chartData = this.props.config;
        console.log("Chart data:", chartData);
        
        // Check if chartData exists and has the required structure
        if (!chartData || !chartData.data || !chartData.data.labels || !chartData.data.datasets) {
            console.warn("ChartRenderer: config is missing or invalid", this.props.config);
            return;
        }
        console.log("After Data available")
        // Extract the actual data from the nested structure
        const { labels, datasets } = chartData.data;
      
        console.log("Labels",labels)
        this.chart = new Chart(this.chartRef.el, {
          
            type: this.props.type || 'line', 
            data: {
                labels: labels,  
                datasets: datasets.map(dataset => ({  
                    ...dataset,  
                    backgroundColor: 'rgba(75, 192, 192, 0.2)', 
                    borderColor: dataset.borderColor || 'green', 
                    tension: 0.4,
                    label: 'Order Over Time',
                    data: dataset.data.map(item => item.y) 
                }))
            }, 
            options: { 
                responsive: true, 
                plugins: { 
                    legend: { 
                        position: 'bottom',
                    }, 
                    title: { 
                        display: true,
                        text: this.props.title || 'Chart Title',    
                        position: 'bottom',
                    } 
                }, 
                scales: {
                    x: {  
                        title: {
                            display: true,
                            text: 'DATE' 
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 1,
                            drawBorder: true, 
                        },
                    },
                    y: { 
                        title: {
                            display: true,  
                            text: 'Number of Orders'
                        }, 
                        grid: { 
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 1, 
                            drawBorder: true,
                        },
                    } 
                },
                elements: { 
                    backgroundColor: 'white',
                    line: { 
                        borderColor: 'green', 
                        borderWidth: 2,
                        tension: 0.4,
                    },
                    point: { 
                        radius: 5,
                        backgroundColor: 'black',
                        borderWidth: 2, 
                        borderColor: 'white',
                    } 
                }
            },
        });
    }
    // renderChart() {
    //     if (this.chart) {
    //         this.chart.destroy();
    //     }

    //     const chartData = this.props.config;
    //     console.log("Chart data:", chartData);

    //     // Validate structure
    //     if (!chartData || !chartData.data || !chartData.data.labels || !chartData.data.datasets) {
    //         console.warn("ChartRenderer: config is missing or invalid", this.props.config);
    //         return;
    //     }

    //     const { labels, datasets } = chartData.data;
    //     console.log("$$$$$$$$$$$$$$$$$$$$",chartData.d)
    //     this.chart = new Chart(this.chartRef.el, {
    //     type: this.props.type || 'line',
    //         data: chartData.data,
    //         options: {
    //             responsive: true,
    //             parsing: false, // Tell Chart.js to use x/y objects directly
    //             plugins: {
    //                 legend: {
    //                     position: 'bottom',
    //                 },
    //                 title: {
    //                     display: true,
    //                     text: this.props.title || 'Chart Title',
    //                     position: 'bottom',
    //                 }
    //             },
    //             scales: {
    //                 x: {
    //                     type: 'category',
    //                     title: {
    //                         display: true,
    //                         text: 'DATE',
    //                     },
    //                     grid: {
    //                         color: 'rgba(0, 0, 0, 0.1)',
    //                         lineWidth: 1,
    //                         drawBorder: true,
    //                     },
    //                 },
    //                 y: {
    //                     title: {
    //                         display: true,
    //                         text: 'Number of Orders'
    //                     },
    //                     grid: {
    //                         color: 'rgba(0, 0, 0, 0.1)',
    //                         lineWidth: 1,
    //                         drawBorder: true,
    //                     },
    //                 }
    //             },
    //             elements: {
    //                 line: {
    //                     borderWidth: 2,
    //                     tension: 0.4,
    //                 },
    //                 point: {
    //                     radius: 5,
    //                     backgroundColor: 'black',
    //                     borderWidth: 2,
    //                     borderColor: 'white',
    //                 }
    //             }
    //         },
    //     });
    // }

}

TransportChartRenderer.template = "owl.TransportChartRenderer"