# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """IZI Dashboard with AI""",
    "summary": """
        Beautiful Analytic Dashboard by IZI.
        You can create a Sales Dashboard, Inventory Dashboard, Finance Dashboard, or Others dynamically with this module.
        You can explore data with AI too!
    """,
    "category": "Reporting",
    "version": "17.0.4.0.23",
    "development_status": "Production",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": True,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    "website": "https://www.iziapp.id",
    "license": "OPL-1",
    "images": [
        'static/description/banner.gif'
    ],

    "price": 475,
    "currency": "USD",

    "depends": [
        # odoo addons
        'base',
        'web',
        # third party addons

        # developed addons
        'izi_data',
    ],
    "data": [
        # group
        'security/res_groups.xml',

        # data
        'data/izi_visual_type.xml',
        'data/izi_visual_config.xml',
        'data/izi_visual_config_value.xml',
        'data/izi_dashboard_theme.xml',
        'data/izi_data_template.xml',

        # global action
        # 'views/action/action.xml',

        # view
        'views/common/izi_dashboard.xml',
        'views/common/izi_analysis.xml',
        'views/common/izi_lab_api_key_wizard.xml',
        'views/common/res_company.xml',

        # wizard
        'views/wizard/izi_dashboard_config_wizard.xml',

        # report paperformat
        # 'data/report_paperformat.xml',

        # report template
        # 'views/report/report_template_model_name.xml',

        # report action
        # 'views/action/action_report.xml',

        # assets
        # 'views/assets.xml',

        # onboarding action
        # 'views/action/action_onboarding.xml',

        # action menu
        'views/action/action_menu.xml',

        # action onboarding
        # 'views/action/action_onboarding.xml',

        # menu
        'views/menu.xml',

        # security
        'security/ir.model.access.csv',
        # 'security/ir.rule.csv',

        # template
        'views/template/izi_dashboard.xml',
    ],
    "demo": [
        # 'demo/demo.xml',
    ],
    "qweb": [

    ],

    "post_load": None,
    # "pre_init_hook": "pre_init_hook",
    # "post_init_hook": "post_init_hook",
    "uninstall_hook": None,

    "external_dependencies": {"python": [], "bin": []},
    "live_test_url": "https://demo.iziapp.id/web/login",
    # "demo_title": "{MODULE_NAME}",
    # "demo_addons": [
    # ],
    # "demo_addons_hidden": [
    # ],
    "demo_url": "https://demo.iziapp.id/web/login",
    # "demo_summary": "{SHORT_DESCRIPTION_OF_THE_MODULE}",
    # "demo_images": [
    #    "images/MAIN_IMAGE",
    # ]

    'assets': {
        'web.assets_backend': [
            # Odoo
            'web/static/src/legacy/js/core/class.js',
            'web/static/src/legacy/js/core/dialog.js',
            'web/static/src/legacy/xml/dialog.xml',
            # 'web/static/src/legacy/js/core/minimal_dom.js',
            'web/static/src/legacy/js/core/dom.js',
            'web/static/src/legacy/js/core/mixins.js',
            'web/static/src/legacy/js/core/service_mixins.js',
            'web/static/src/legacy/js/core/widget.js',
            # QWeb
            # Generic
            'izi_dashboard/static/src/xml/component/izi_dialog.xml',
            # Component
            'izi_dashboard/static/src/xml/component/izi_view_dashboard.xml',
            'izi_dashboard/static/src/xml/component/izi_view_dashboard_block.xml',
            'izi_dashboard/static/src/xml/component/izi_view_analysis.xml',
            'izi_dashboard/static/src/xml/component/izi_config_analysis.xml',
            'izi_dashboard/static/src/xml/component/izi_view_table.xml',
            'izi_dashboard/static/src/xml/component/izi_view_visual.xml',
            'izi_dashboard/static/src/xml/component/izi_config_dashboard.xml',
            'izi_dashboard/static/src/xml/component/izi_select_analysis.xml',
            'izi_dashboard/static/src/xml/component/izi_select_dashboard.xml',
            'izi_dashboard/static/src/xml/component/izi_select_metric.xml',
            'izi_dashboard/static/src/xml/component/izi_select_dimension.xml',
            'izi_dashboard/static/src/xml/component/izi_select_sort.xml',
            'izi_dashboard/static/src/xml/component/izi_select_filter_temp.xml',
            'izi_dashboard/static/src/xml/component/izi_select_filter.xml',
            # Component > QWeb
            'izi_dashboard/static/src/xml/component/qweb/izi_select_analysis_item.xml',
            'izi_dashboard/static/src/xml/component/qweb/izi_select_dashboard_item.xml',
            'izi_dashboard/static/src/xml/component/qweb/izi_select_metric_item.xml',
            'izi_dashboard/static/src/xml/component/qweb/izi_select_dimension_item.xml',
            'izi_dashboard/static/src/xml/component/qweb/izi_select_filter_item.xml',
            'izi_dashboard/static/src/xml/component/qweb/izi_select_sort_item.xml',
            # Base
            'izi_dashboard/static/src/xml/izi_dashboard.xml',
            'izi_dashboard/static/src/xml/izi_analysis.xml',
            'izi_dashboard/static/src/xml/izi_analysis_widget.xml',

            # CSS
            'izi_dashboard/static/lib/select2/select2.css',
            'izi_dashboard/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'izi_dashboard/static/lib/gridstack/gridstack.min.css',
            'izi_dashboard/static/lib/grid/mermaid.min.css',
            'izi_dashboard/static/lib/google/icon.css',
            'izi_dashboard/static/lib/jquery.ui/jquery-ui.css',
            'izi_dashboard/static/lib/bootstrap-datepicker/css/bootstrap-datepicker3.min.css',
            'izi_dashboard/static/lib/bootstrap-datepicker/css/bootstrap-datepicker.min.css',

            'izi_dashboard/static/src/css/font.css',
            'izi_dashboard/static/src/css/component/general/izi_bootstrap.min.css',
            'izi_dashboard/static/src/css/component/general/izi_layout.css',
            'izi_dashboard/static/src/css/component/general/izi_dialog.css',
            'izi_dashboard/static/src/css/component/general/izi_button.css',
            'izi_dashboard/static/src/css/component/general/izi_select.css',
            'izi_dashboard/static/src/css/component/general/izi_accordion.css',
            'izi_dashboard/static/src/css/component/general/izi_chart.css',
            'izi_dashboard/static/src/css/component/general/izi_replace.css',

            'izi_dashboard/static/src/css/component/main/izi_view.css',
            'izi_dashboard/static/src/css/component/main/izi_view_table.css',
            'izi_dashboard/static/src/css/component/main/izi_view_dashboard.css',
            'izi_dashboard/static/src/css/component/main/izi_config_analysis.css',
            'izi_dashboard/static/src/css/component/main/izi_config_dashboard.css',
            'izi_dashboard/static/src/css/component/main/izi_select_analysis.css',
            'izi_dashboard/static/src/css/component/main/izi_select_metric.css',
            'izi_dashboard/static/src/css/component/main/izi_select_dimension.css',
            'izi_dashboard/static/src/css/component/main/izi_select_sort.css',
            'izi_dashboard/static/src/css/component/main/izi_select_filter_temp.css',
            'izi_dashboard/static/src/css/component/main/izi_select_filter.css',
            'izi_dashboard/static/src/css/component/main/izi_description_page.css',

            'izi_dashboard/static/src/css/component/toggle-switchy.css',
            'izi_dashboard/static/src/js/nepaliDatePicker.js',
            'izi_dashboard/static/src/js/nepaliDatePicker.css',
            # JS
            'izi_dashboard/static/lib/select2/select2.js',
            'izi_dashboard/static/lib/moment/moment.js',
            'izi_dashboard/static/lib/ace-1.3.1/ace.js',
            'izi_dashboard/static/lib/ace-1.3.1/mode-javascript.js',
            'izi_dashboard/static/lib/ace-1.3.1/worker-javascript.js',
            'izi_dashboard/static/lib/ace-1.3.1/theme-chrome.js',
            'izi_dashboard/static/lib/amcharts/core.js',
            'izi_dashboard/static/lib/amcharts/charts.js',
            'izi_dashboard/static/lib/amcharts/maps.js',
            'izi_dashboard/static/lib/amcharts/regression.js',
            'izi_dashboard/static/lib/amcharts/geodata/indonesiaLow.js',
            'izi_dashboard/static/lib/amcharts/geodata/usaLow.js',
            'izi_dashboard/static/lib/amcharts/geodata/worldLow.js',
            'izi_dashboard/static/lib/amcharts/geodata/countries2.js',
            'izi_dashboard/static/lib/amcharts/themes/animated.js',
            'izi_dashboard/static/lib/amcharts/themes/frozen.js',
            'izi_dashboard/static/lib/gridstack/gridstack-h5.js',
            # 'izi_dashboard/static/lib/gridstack/gridstack-poly.js',
            # 'izi_dashboard/static/lib/gridstack/gridstack-all.js',
            'izi_dashboard/static/lib/sweetalert/sweetalert.min.js',
            'izi_dashboard/static/lib/grid/gridjs.umd.js',
            'izi_dashboard/static/lib/jspdf/html2canvas.min.js',
            'izi_dashboard/static/lib/jspdf/jspdf.umd.min.js',
            'izi_dashboard/static/lib/jquery.ui/jquery-ui.js',
            'izi_dashboard/static/lib/bootstrap-datepicker/js/bootstrap-datepicker.min.js',
            'izi_dashboard/static/lib/bootstrap-datepicker/js/bootstrap-datepicker-conflict.js',
            'izi_dashboard/static/lib/jscolor/jscolor.min.js',

            'izi_dashboard/static/src/js/component/chart/amcharts_theme.js',
            'izi_dashboard/static/src/js/component/chart/amcharts_component_old.js',
            'izi_dashboard/static/src/js/component/chart/amcharts_component.js',
            'izi_dashboard/static/src/js/component/general/izi_autocomplete.js',
            'izi_dashboard/static/src/js/component/general/izi_tags.js',
            'izi_dashboard/static/src/js/component/general/izi_dialog.js',
            'izi_dashboard/static/src/js/component/general/izi_field_icon.js',
            'izi_dashboard/static/src/js/component/general/izi_dropdown.js',
            'izi_dashboard/static/src/js/component/main/izi_view_dashboard.js',
            'izi_dashboard/static/src/js/component/main/izi_view_dashboard_block.js',
            'izi_dashboard/static/src/js/component/main/izi_view_analysis.js',
            'izi_dashboard/static/src/js/component/main/izi_view_table.js',
            'izi_dashboard/static/src/js/component/main/izi_view_visual.js',
            'izi_dashboard/static/src/js/component/main/izi_config_dashboard.js',
            'izi_dashboard/static/src/js/component/main/izi_config_analysis.js',
            'izi_dashboard/static/src/js/component/main/izi_select_analysis.js',
            'izi_dashboard/static/src/js/component/main/izi_select_dashboard.js',
            'izi_dashboard/static/src/js/component/main/izi_select_metric.js',
            'izi_dashboard/static/src/js/component/main/izi_select_dimension.js',
            'izi_dashboard/static/src/js/component/main/izi_select_sort.js',
            'izi_dashboard/static/src/js/component/main/izi_select_filter_temp.js',
            'izi_dashboard/static/src/js/component/main/izi_select_filter.js',
            'izi_dashboard/static/src/js/component/main/izi_add_analysis.js',
            'izi_dashboard/static/src/js/izi_analysis_controller.js',
            'izi_dashboard/static/src/js/izi_analysis_view.js',
            'izi_dashboard/static/src/js/izi_dashboard_controller.js',
            'izi_dashboard/static/src/js/izi_dashboard_view.js',
            'izi_dashboard/static/src/js/izi_analysis_widget.js',
        ]
    }
}
