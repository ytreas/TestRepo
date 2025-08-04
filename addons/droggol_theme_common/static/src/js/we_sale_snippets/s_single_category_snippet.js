odoo.define('droggol_theme_common.s_single_category_snippet', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var ProductRootWidget = require('droggol_theme_common.product.root.widget');
var Mixins = require('droggol_theme_common.mixins');

var CategoryMixins = Mixins.CategoryMixins;
var CategoryPublicWidgetMixins = Mixins.CategoryPublicWidgetMixins;
var core = require('web.core');
var config = require('web.config');
var _t = core._t;

publicWidget.registry.s_single_category_snippet = ProductRootWidget.extend(CategoryMixins, CategoryPublicWidgetMixins, {
    selector: '.s_d_single_category_snippet_wrapper',

    bodyTemplate: 's_single_category_snippet',

    bodySelector: '.s_d_single_category_snippet',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-category-params']),

    controllerRoute: '/droggol_theme_common/get_products_by_category',

    fieldstoFetch: ['name', 'price', 'description_sale', 'dr_label_id', 'rating', 'public_categ_ids'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_single_category_snippet.xml']),

    start: function () {
        var categoryParams = this.$target.attr('data-category-params');
        this.categoryParams = categoryParams ? JSON.parse(categoryParams) : false;
        this.initialCategory = false;
        if (this.categoryParams) {
            var categoryIDs = this.categoryParams.categoryIDs;
            // first category
            this.initialCategory = categoryIDs.length ? categoryIDs[0] : false;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _setDBData: function (data) {
        var categories = data.categories;
        if (categories && categories.length) {
            this.categoryName = categories.length ? categories[0].name : false;
        }
        this._super.apply(this, arguments);
    },
    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        this._initalizeOwlSlider(this.userParams.ppr);
    },
    /**
     * @private
     */
    _processData: function (data) {
        if (this.categoryName) {
            // group of 8 products
            var items = 8;
            if (config.device.isMobile) {
                items = 4;
            }
            var group = _.groupBy(data.products, function (product, index) {
                return Math.floor(index / (items));
            });
            return _.toArray(group);
        } else {
            return [];
        }
    },
    _initalizeOwlSlider: function () {
        this.$('.droggol_product_category_slider').owlCarousel({
            dots: false,
            margin: 10,
            stagePadding: 5,
            rtl: _t.database.parameters.direction === 'rtl',
            rewind: true,
            nav: true,
            navText: ['<div class="badge text-primary"><i class="lnr font-weight-bold lnr-chevron-left"></i></div>', '<div class="badge text-primary"><i class="lnr font-weight-bold lnr-chevron-right"></i></div>'],
            responsive: {
                0: {
                    items: 1,
                },
                576: {
                    items: 1,
                },
                768: {
                    items: 1,
                },
                992: {
                    items: 1,
                },
                1200: {
                    items: 1,
                }
            },
        });
    }
});
});
