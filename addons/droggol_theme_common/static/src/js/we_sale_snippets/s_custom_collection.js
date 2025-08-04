odoo.define('droggol_theme_common.s_custom_collection', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var ProductRootWidget = require('droggol_theme_common.product.root.widget');
var core = require('web.core');
var Mixins = require('droggol_theme_common.mixins');

var OwlMixin = Mixins.OwlMixin;
var qweb = core.qweb;

publicWidget.registry.s_custom_collection = ProductRootWidget.extend(OwlMixin, {

    selector: '.s_d_custom_collection',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-category-filter', 'data-collection-params']),

    read_events: _.extend({
        'click .d_category_lable': '_onCategoryLableClick',
    }, ProductRootWidget.prototype.read_events),

    bodyTemplate: 'd_s_category_cards_wrapper',

    fieldstoFetch: ['name', 'price', 'description_sale', 'dr_label_id', 'rating', 'public_categ_ids', 'product_template_image_ids'],

    controllerRoute: '/droggol_theme_common/_get_products_from_collection',

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/cards.xml',
        '/droggol_theme_common/static/src/xml/category_filters.xml']),

    start: function () {
        var categoryFilterStyle = this.$target.attr('data-category-filter');
        var collectionParams = this.$target.attr('data-collection-params');
        this.collectionParams = collectionParams ? JSON.parse(collectionParams) : false;
        this.categoryFilterStyle = categoryFilterStyle ? JSON.parse(categoryFilterStyle) : false;
        this.categories = false;
        if (this.collectionParams) {
            this.categories = _.map(this.collectionParams, function (collection, index) {
                collection['id'] = index + 1;
                return {
                    id: index + 1,
                    name: collection.title,
                };
            });
            this.initialCategory = this.categories[0].id;
        }
        return this._super.apply(this, arguments);
    },
    _processData: function (data) {
        var products = data;
        if (this.collectionParams && this.collectionParams[0].data.selectionType === 'manual') {
            products = _.map(this.collectionParams[0].data.productIDs, function (product) {
                return _.findWhere(data, {id: product});
            });
            products = _.compact(products);
        }
        return products;
    },
    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        if (this.userParams.layoutType === 'slider') {
            this._initalizeOwlSlider(this.userParams.ppr);
        }
    },
    /**
     * @private
      * duplicate method (in V13) do something generic in next version.
     */
    _activateCategory: function (categoryID) {
        this.$('.d_s_category_cards_item').addClass('d-none');
        this.$('.d_s_category_cards_item[data-category-id=' + categoryID + ']').removeClass('d-none');
    },
    /**
     * @private
     */
    _getParameters: function () {
        var params = this._super.apply(this, arguments);
        if (this.initialCategory) {
            params['collection'] = this._getCollectionData(this.initialCategory).data;
        }
        return params;
    },
    /**
     * @private
     */
    _getCollectionData: function (collectionID) {
        return _.findWhere(this.collectionParams, {id: collectionID});
    },
    /**
     * @private
     * duplicate method (in V13) do something generic in next version V14.
     */
    _renderNewProducts: function (products, categoryID) {
        var collection = this._getCollectionData(categoryID);
        if (collection.data.selectionType === 'manual') {
            var filteredProducts = _.map(collection.data.productIDs, function (product) {
                return _.findWhere(products, {id: product});
            });
            products = _.compact(filteredProducts);
        }
        var $tmpl = $(qweb.render('d_s_category_cards_item', {
            data: products,
            widget: this,
            categoryID: categoryID
        }));
        $tmpl.appendTo(this.$('.d_s_category_cards_container'));
        this._activateCategory(categoryID);
        this._initalizeOwlSlider(this.userParams.ppr);
    },
    /**
     * @private
     */
    _fetchProductsByColletion: function (ID) {
        return this._rpc({
            route: '/droggol_theme_common/_get_products_from_collection',
            params: {
                fields: this.fieldstoFetch,
                collection: this._getCollectionData(ID).data,
            },
        });
    },
    /**
    * @private
    * duplicate method (in V13) do something generic in next version.
    */
    _onCategoryLableClick: function (ev) {
        var $target = $(ev.currentTarget);
        this.$('.d_category_lable').removeClass('d_active');
        $target.addClass('d_active');
        var categoryID = parseInt($target.attr('data-category-id'), 10);
        if (!this.$('.d_s_category_cards_item[data-category-id=' + categoryID + ']').length) {
            this._fetchProductsByColletion(categoryID).then(data => {
                this._renderNewProducts(data, categoryID);
            });
        } else {
            this._activateCategory(categoryID);
        }
    },
});
});
