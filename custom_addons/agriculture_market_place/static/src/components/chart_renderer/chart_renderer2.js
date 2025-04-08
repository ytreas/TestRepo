/** @odoo-module */

import { Component, useRef, onMounted, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
const { useState } = owl;

export class ChartRenderer2 extends Component {
    setup() {
        this.chartRef = useRef("chart");

        // Load the Chart.js library
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js");
        });
        
        useEffect(() => {
            this.renderChart()
        }, () => [this.props.config])

        onMounted(() => {
            this.renderChart();
                
            // Prevent right-click to disable chart saving
            this.chartRef.el.addEventListener("contextmenu", (event) => {
                event.preventDefault();
            });
        });

        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy()
            }
        })
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy()
        }
        // Ensure the chart data exists before rendering
        if (!this.props.config || !this.props.config.data || !this.chartRef.el) {
            console.error("Missing chart data or chart reference.");
            return; // Exit if no data or chart reference
        }

        const chartData = this.props.config.data;

        // Check that chartData contains the necessary parts
        if (!chartData.labels || !chartData.datasets) {
            console.error("Chart data is incomplete.");
            return; // Exit if chart data is incomplete
        }

        console.log("Rendering chart with data:", chartData);

        // Create the chart
        this.chart = new Chart(this.chartRef.el, {
            type: this.props.type || 'line',
            data: chartData,
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
                            text: `Price (RS)`
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 1,
                            drawBorder: true,
                        },
                    }
                },
                elements: {  
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
                },
            },
        });                
    }
}

ChartRenderer2.template = "owl.ChartRenderer2";