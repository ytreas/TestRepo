odoo.define('droggol_theme_common.s_products_collection', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var ProductRootWidget = require('droggol_theme_common.product.root.widget');

publicWidget.registry.s_products_collection = ProductRootWidget.extend({
    selector: '.s_d_products_collection',

    fieldstoFetch: ['rating', 'public_categ_ids'],

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-collection-params', 'data-collection-style']),

    bodyTemplate: 'd_s_cards_collection_wrapper',

    controllerRoute: '/droggol_theme_common/get_products_by_collection',

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/cards_collection.xml']),

    start: function () {
        var collectionParams = this.$target.attr('data-collection-params');
        this.collectionParams = collectionParams ? JSON.parse(collectionParams) : false;
        var collectionStyle = this.$target.attr('data-collection-style');
        this.collectionStyle = collectionStyle ? JSON.parse(collectionStyle) : false;
        if (this.collectionParams) {
            this.numOfCol = 12 / this.collectionParams.length;
            if (this.numOfCol < 4) {
                this.numOfCol = 4;
            }
        }
        return this._super.apply(this, arguments);
    },
    /**
    * @private
    */
    _getOptions: function () {
        var options = {};
        if (this.collectionParams) {
            // For V14 we will make collection with owlCarousel
            // each slider contains 5 products
            options['collections'] = this.collectionParams;
            return options;
        } else {
            return this._super.apply(this, arguments);
        }
    },
});
});
