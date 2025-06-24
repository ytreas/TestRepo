/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted, useEffect, onWillUnmount } = owl

export class PieChart extends Component {
    static props = {
        config: Object,
        type: String,
        title: String,
    };

    setup() {
        this.chartRef = useRef("chart")
        
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })
        
        useEffect(() => {
            this.renderChart()
        }, () => [this.props.config])
        
        onWillUnmount(() => {
            this.chart?.destroy()
        })
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy()
        }

        const chartData = this.props.config?.data;
        if (!chartData?.labels || !chartData?.datasets?.[0]?.data) {
            return;
        }

        const [mainDataset] = chartData.datasets;
        const typeColors = {
            'WEATHER': '#FF6384',
            'TRAFFIC': '#36A2EB',
            'ADDRESS': '#FFCE56',
            'SYSTEM': '#4BC0C0',
            'OTHERS': '#9966FF',
            'DEFAULT': '#999999'
        };

        this.chart = new Chart(this.chartRef.el, {
            type: 'pie',
            data: {
                labels: chartData.labels,
                datasets: [{
                    ...mainDataset,
                    // backgroundColor: chartData.labels.map(label => typeColors[label] || typeColors['default']),
                    backgroundColor : mainDataset.backgroundColor ||
                    chartData.labels.map(label =>
                        typeColors[label.toUpperCase()] || typeColors['DEFAULT']
                    ),
                    borderColor: '#fff',
                    borderWidth: 2,
                    // hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                // maintainAspectRatio: false,
                layout: {
                    padding: 10
                },
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value} delays`;
                        }
                    }
                },
                elements: {
                    arc: {
                        hoverOffset: 5,  
                        borderWidth: 2
                    }
                },
                animation: {
                    animateScale: true, 
                    animateRotate: true 
                }
            }
        });
    }
}

PieChart.template = "owl.TransportChartRenderer"