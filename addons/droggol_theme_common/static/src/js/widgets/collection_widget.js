odoo.define('droggol_theme_common.widgets.collection_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');
var SnippetConfigurator = require('droggol_theme_common.dialog.snippet_configurator_dialog');
var Mixins = require('droggol_theme_common.mixins');

var SortableMixins = Mixins.SortableMixins;

var qweb = core.qweb;
var _t = core._t;

var CollectionWidget = AbstractWidget.extend(SortableMixins, {

    template: 'collection_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/collection_widget.xml']
    ),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'click .d_add_collection': '_onClickAddCollection',
        'click .d_open_configrator': '_onClickOpenConfigurator',
        'click .d_remove_item': '_onRemoveCollectionClick',
    }),

    d_tab_info: {
        icon: 'fa fa-list',
        label: _t('Collections'),
        name: 'CollectionWidget',
    },
    d_attr: 'data-collection-params',

    start: function () {
        this._makeListSortable();
        this._togglePlaceHolder();
        return this._super.apply(this, arguments);
    },
    setValue: function (data) {
        this.collections = data;
    },
    getValues: function () {
        return {
            d_attr: 'data-collection-params',
            value: _.map(this.$('.d_collection_item'), item => {
                var $item = $(item);
                var attrValue = $item.attr('data-products');
                var widgetVal = attrValue ? JSON.parse(attrValue) : false;
                return {
                    data: widgetVal,
                    title: $item.find('#d_collection_title').val(),
                };
            }),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Refresh list of products.
     *
     * @private
     */
    _togglePlaceHolder: function () {
        var items = !!this.$('.d_collection_item').length;
        this.trigger_up('widget_value_changed', {val: items});
        this.$('.d-snippet-config-placeholder').toggleClass('d-none', items);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickAddCollection: function () {
        this.$('.d_sortable_block').append(qweb.render('collection_item', {
            collection: {
                data: false,
            },
        }));
        this._togglePlaceHolder();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveCollectionClick: function (ev) {
        var $product = $(ev.currentTarget).closest('.d_collection_item');
        $product.remove();
        this._togglePlaceHolder();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickOpenConfigurator: function (ev) {
        var $target = $(ev.currentTarget);
        var id = _.uniqueId('d_id_');
        var $item = $target.closest('.d_collection_item');
        $item.attr('data-id', id);
        var attrValue = $item.attr('data-products');
        var widgetVal = attrValue ? JSON.parse(attrValue) : false;
        this.SnippetConfigurator = new SnippetConfigurator(this, {
            widgets: {
                ProductsWidget: widgetVal
            },
            size: 'large',
            title: _t('Product selector'),
        });
        this.SnippetConfigurator.on('d_final_pick', this, function (ev) {
            ev.stopPropagation();
            this.$('.d_collection_item[data-id=' + id + ']').attr('data-products', JSON.stringify(ev.data.ProductsWidget.value));
        });
        this.SnippetConfigurator.open();
    },
});

DialogWidgetRegistry.add('CollectionWidget', CollectionWidget);

return CollectionWidget;
});
