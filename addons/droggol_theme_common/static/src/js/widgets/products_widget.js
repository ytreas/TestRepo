odoo.define('droggol_theme_common.widgets.products_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var Select2Dialog = require('droggol_theme_common.product_selector');
var DomainBuilder = require('droggol_theme_common.domain_builder').DomainBuilder;
var Mixins = require('droggol_theme_common.mixins');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');

var SortableMixins = Mixins.SortableMixins;

var qweb = core.qweb;
var _t = core._t;

var ProductsWidget = AbstractWidget.extend(SortableMixins, {

    template: 'droggol_theme_common.products_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/products_widget.xml']
    ),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'click .d_add_product': '_onAddProductClick',
        'click .d_remove_item': '_onRemoveProductClick',
        'click .d_selection_type_btn': '_onSwitchSelectionTypeClick',
    }),

    d_tab_info: {
        icon: 'fa fa-cubes',
        label: _t('Products'),
        name: 'ProductsWidget',
    },
    d_attr: 'data-products-params',

    /**
     * @override
     * @returns {Promise}
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        if (this.productIDs.length && this.activeSelectionType === 'manual') {
            defs.push(this._fetchProductsData(this.productIDs).then(data => {
                this._setProducts(data);
            }));
        }
        return Promise.all(defs);
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        this._makeListSortable();
        this._togglePlaceHolder();
        this._appendDomainBuilder();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     * @returns {Array} list of selected products
     */
    getValues: function () {
        var result = {
            selectionType: this.activeSelectionType,
        };
        switch (this.activeSelectionType) {
            case 'manual':
                result['productIDs'] = this._getProductIDs();
                break;
            case 'advance':
                result['domain_params'] = this.DomainBuilder.getDomain();
                break;
        }
        return {
            value: result,
            d_attr: this.d_attr
        };
    },
    /**
     * @constructor
     * @param {Object} options: useful parameters such as productIDs, domain etc.
     */
    setValue: function (options) {
        options = options || {};
        this.productIDs = options.productIDs || [];
        this.domain_params = options.domain_params || false;
        this.products = [];
        this.activeSelectionType = options.selectionType || 'manual';
        this.noSwicher = options.noSwicher || false;
        this.select2Limit = options.select2Limit || 0;
        this._setSelectionType();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Refresh list of products.
     *
     * @private
     */
    _refreshProductsList: function () {
        var $productList = this.$('.d_sortable_block');
        $productList.empty();
        if (this.products.length) {
            $productList.append(qweb.render('droggol_theme_common.products_list', {products: this.products}));
        }
        this._togglePlaceHolder();
    },
    /**
     * @private
     */
    _appendDomainBuilder: function () {
        this.DomainBuilder = new DomainBuilder(this, this.domain_params);
        this.DomainBuilder.appendTo(this.$('.d_advance_selection_body'));
    },
    /**
     * Product na related data fetch karava mate aa method willStart vkht
     * ane new product add karvama avse tyare call thse.
     * aa method shop na configure na data pan lavse
     * ex. wishlist shop ma enable che k nathi
     *
     * @param {Array} productIDs
     * @private
     */
    _fetchProductsData: function (productIDs) {
        var params = {
            domain: [['id', 'in', productIDs]],
            fields: ['name', 'price', 'description_sale', 'website_published', 'dr_label_id'],
       };
        return this._rpc({
            route: '/droggol_theme_common/get_products_data',
            params: params,
        });
    },
    /**
     * @private
     * @returns {Array} productIDs
     */
    _getProductIDs: function () {
        return _.map(this.$('.d_list_item'), item => {
            return $(item).data('productId');
        });
    },
    /**
     * @private
     */
    _getSelectionTypes: function () {
        return {
            manual: {
                label: _t('Manual Selection'),
                type: 'manual',
            },
            advance: {
                label: _t('Advance Selection'),
                type: 'advance',
            }
        };
    },
    /**
     * Set Products [ For more info contact KIG :) ]
     *
     * @param {Array} data
     * @private
     */
    _setProducts: function (data) {
        var products = _.map(this.productIDs, function (product) {
            return _.findWhere(data.products, {id: product});
        });
        this.products = _.compact(products);
        this.productIDs = _.map(this.products, function (product) {
            return product.id;
        });
    },
    /**
     * @private
     */
    _setSelectionType: function () {
        this.SelectionBtns = _.map(this._getSelectionTypes(), r => {
            r['active'] = r.type === this.activeSelectionType;
            return r;
        });
    },
    /**
     * Jo placeholder display karavu hoy or hide karvu hoy.
     *
     * @private
     */
    _togglePlaceHolder: function () {
        var items = this.$('.d_list_item').length;
        this.trigger_up('widget_value_changed', {val: this.activeSelectionType === 'advance' ? true : items});
        this.$('.d-snippet-config-placeholder').toggleClass('d-none', !!items);
        this.$('.d_product_selector_title').toggleClass('d-none', !items);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Select2Dialog just select kareli products nu list apse
     * aema price ne badhi fields nai hoy to ae fields fetch kari ne
     * _refreshProductsList call karvi.
     *
     * @private
     */
    _onAddProductClick: function () {
        var self = this;
        var currentSelectedProducts = this._getProductIDs();
        var ProductDialog = new Select2Dialog(this, {
            multiSelect: true,
            records: this.products,
            recordsIDs: currentSelectedProducts,
            routePath: '/product_snippet/get_product_by_name',
            fieldLabel: _t("Select Product"),
            dropdownTemplate: 'd_select2_products_dropdown',
            select2Limit: this.select2Limit,
        });
        ProductDialog.on('d_product_pick', this, function (ev) {
            var productsToAdd = ev.data.result;
            if (productsToAdd) {
                var productsToFetch = _.without(productsToAdd, currentSelectedProducts);
                self._fetchProductsData(productsToFetch).then(data => {
                    var products = _.union(data.products, self.products);
                    self.products = _.map(productsToAdd, function (product) {
                        return _.findWhere(products, {id: product});
                    });
                    self._refreshProductsList();
                    self.productIDs = self._getProductIDs();
                });
            } else {
                self.products = [];
                self.productIDs = [];
                this._refreshProductsList();
            }
        });
        ProductDialog.open();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveProductClick: function (ev) {
        var $product = $(ev.currentTarget).closest('.d_list_item');
        $product.remove();
        this.products = _.without(this.products, _.findWhere(this.products, {id: parseInt($product.attr('data-product-id'), 10)}));
        this.productIDs = this._getProductIDs();
        this._togglePlaceHolder();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSwitchSelectionTypeClick: function (ev) {
        var $target = $(ev.currentTarget);
        this.activeSelectionType = $target.data('type');
        this.$('.d_body_content').addClass('d-none');
        this.$('.d_' + $target.data('type') + '_selection_body').removeClass('d-none');
        this._togglePlaceHolder();
    },
});

DialogWidgetRegistry.add('ProductsWidget', ProductsWidget);

return ProductsWidget;

});
