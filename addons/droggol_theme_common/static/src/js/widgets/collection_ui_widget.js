odoo.define('droggol_theme_common.widgets.collection_ui_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var CollectionStyleRegistry = require('droggol_theme_common.collection_style_registry');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');

var qweb = core.qweb;
var _t = core._t;

var CollectionUIWidget = AbstractWidget.extend({

    template: 'collection_ui_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/collection_ui_widget.xml',
            'droggol_theme_common/static/src/xml/cards_collection.xml']
    ),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'change #d_collection_style_select': '_onChangeStyle',
    }),

    d_tab_info: {
        icon: 'fa fa-paint-brush',
        label: _t('Collections UI'),
        name: 'CollectionUIWidget',
    },
    d_attr: 'data-collection-style',

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
    getValues: function () {
        return {
            value: {
                SelectedStyle: this.$('#d_collection_style_select').val(),
            },
            d_attr: this.d_attr,
        };
    },
    /**
     * @override
     */
    setValue: function (options) {
        this.allStyles = CollectionStyleRegistry.keys();
        this.SelectedStyle = options.SelectedStyle || 'd_card_collection_style_1';
        this.demoData = this._getDemoData();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getDemoData: function () {
        return {
            title: _t("New Arrivals"),
            products: [{
                website_url: '#',
                img_medium: '/droggol_theme_common/static/src/img/s_config_data.png',
                name: 'Product Name',
                price: '$ 13.00',
                // rating: qweb.render('rating_demo_tmpl'),
                has_discounted_price: true,
                list_price: '$ 22.10'
            }, {
                website_url: '#',
                img_medium: '/droggol_theme_common/static/src/img/s_config_data.png',
                name: 'Product Name',
                price: '$ 13.00',
                // rating: qweb.render('rating_demo_tmpl'),
                has_discounted_price: true,
                list_price: '$ 22.10'
            }, {
                website_url: '#',
                img_medium: '/droggol_theme_common/static/src/img/s_config_data.png',
                name: 'Product Name',
                price: '$ 13.00',
                // rating: qweb.render('rating_demo_tmpl'),
                has_discounted_price: true,
                list_price: '$ 22.10'
            }]
        };
    },
    /**
     * Refresh preview
     *
     * @private
     */
    _refreshPreview: function () {
        this.$('.d_collection_style_preview').empty().append(qweb.render('d_collection_style_preview', {
            widget: this
        }));
    },
    _onChangeStyle: function (ev) {
        this.SelectedStyle = $(ev.currentTarget).val();
        this._refreshPreview();
    },
});

DialogWidgetRegistry.add('CollectionUIWidget', CollectionUIWidget);

return CollectionUIWidget;
});
