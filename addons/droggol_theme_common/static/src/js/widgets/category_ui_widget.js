odoo.define('droggol_theme_common.widgets.category_ui_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var FilterRegistry = require('droggol_theme_common.category_filter_registry');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');

var qweb = core.qweb;
var _t = core._t;

var CategoryUIWidget = AbstractWidget.extend({
    template: 'droggol_theme_common.category_ui_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/category_ui_widget.xml',
        '/droggol_theme_common/static/src/xml/category_filters.xml'
    ]),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'change #d_filter_style_select': '_onChangeFilterStyle',
    }),

    d_tab_info: {
        icon: 'fa fa-paint-brush',
        label: _t('Category UI'),
        name: 'CategoryUIWidget',
    },
    d_attr: 'data-category-filter',

    /**
     * @override
     */
    start: function () {
        this._refreshPreview();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    setValue: function (options) {
        this.allFliters = FilterRegistry.keys();
        this.categoryFilterStyle = options.categoryFilterStyle || 'd_category_filter_style_1';
        this.demoData = this._getDemoData();
    },
    /**
     * @override
     */
    getValues: function () {
        return {
            value: {
                categoryFilterStyle: this.$('#d_filter_style_select').val(),
            },
            d_attr: this.d_attr,
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getDemoData: function () {
        return [{
            id: 1,
            name: _t("All"),
        }, {
            id: 2,
            name: _t("Men"),
        }, {
            id: 3,
            name: _t("Women"),
        }, {
            id: 4,
            name: _t("Kids"),
        }, {
            id: 5,
            name: _t("Accessories"),
        }];
    },
    /**
     * Refresh preview
     *
     * @private
     */
    _refreshPreview: function () {
        this.$('.d_category_filter_preview').empty().append(qweb.render('d_category_filter_preview', {
            widget: this
        }));
    },
    _onChangeFilterStyle: function (ev) {
        this.categoryFilterStyle = $(ev.currentTarget).val();
        this._refreshPreview();
    },
});

DialogWidgetRegistry.add('CategoryUIWidget', CategoryUIWidget);

return CategoryUIWidget;
});
