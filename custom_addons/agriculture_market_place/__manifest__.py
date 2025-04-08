{
    "name": "Market Place",
    "author": "Bisesh Koirala, Aaditya Singh, Robin Gurung and Asim Ghimire",
    "description": """
        This module is used to manage the agriculture market place.
    """,
    "version": "17.0",
    "category": "",
    "application": True,
    "sequence": 1,
    "depends": ["base", "product", "account", "base_accounting_kit","web","vehicle_management"],
    "data": [
        "security/group_user_access.xml",
        "security/ir.model.access.csv",

        "wizard/register_payment_views.xml",
        "views/commodity.xml",
        "views/uom.xml",
        "views/trader.xml",

        "views/daily_price.xml",
        "views/daily_arrival_entry_views.xml",

        "views/arrived_vehicles.xml",
        "views/commodity_price_history_views.xml",
        "views/commodity_entry_views.xml",
        "views/commodity_arrival_view.xml",
        "views/vehicle_sample.xml",
        "data/commodity_price_history_data.xml",
        "data/commodity_arrival_data.xml",
        "data/vehicle_info.xml",
        "data/commodity_entry_data.xml",
        "report/report_template.xml",
        "report/daily_price_report.xml",
        "report/vehicle_duration.xml",
        "report/temp_report.xml",
        "wizard/daily_arrival_entry_wizard.xml",
        "wizard/daily_price_report_wizard.xml",
        "views/collection_center_view.xml",


 
    
    ],
    "assets": {
        "web.assets_backend": [
            "agriculture_market_place/static/src/js/buttonController.js",
            "agriculture_market_place/static/src/xml/button.xml",
            "agriculture_market_place/static/src/scss/style.scss",
            "agriculture_market_place/static/src/components/**/*.js",
            "agriculture_market_place/static/src/components/**/*.xml",
            "agriculture_market_place/static/src/js/commodity_list_controller.js",
            "agriculture_market_place/static/src/xml/commodity_button.xml",
            "agriculture_market_place/static/src/js/commodity_arrival_controller.js",
            "agriculture_market_place/static/src/xml/commodity_arrival_button.xml",
            "agriculture_market_place/static/src/js/commodity_entry_list_button.js",
            "agriculture_market_place/static/src/xml/commodity_entry_button.xml",
            "agriculture_market_place/static/src/js/vehicle_info_button.js",
            "agriculture_market_place/static/src/xml/vehicle_button.xml",
        ],
    },
}
