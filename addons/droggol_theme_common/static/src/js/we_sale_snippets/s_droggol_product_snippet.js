odoo.define('droggol_theme_common.droggol_product_snippet', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var ProductRootWidget = require('droggol_theme_common.product.root.widget');
var Mixins = require('droggol_theme_common.mixins');
var config = require('web.config');
var OwlMixin = Mixins.OwlMixin;
var ProductsBlockMixins = Mixins.ProductsBlockMixins;
var core = require('web.core');
var _t = core._t;


publicWidget.registry.s_d_products_snippet = ProductRootWidget.extend(OwlMixin, ProductsBlockMixins, {
    selector: '.s_d_products_snippet_wrapper',

    bodyTemplate: 'd_s_cards_wrapper',

    bodySelector: '.s_d_products_snippet',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    controllerRoute: '/droggol_theme_common/get_products_data',

    fieldstoFetch: ['name', 'price', 'description_sale', 'dr_label_id', 'rating', 'public_categ_ids', 'product_template_image_ids'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/cards.xml']),
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
});

publicWidget.registry.s_d_product_count_down = ProductRootWidget.extend(ProductsBlockMixins, {
    selector: '.s_d_product_count_down',

    bodyTemplate: 's_d_product_count_down_template',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    controllerRoute: '/droggol_theme_common/get_products_data',

    fieldstoFetch: ['name', 'price', 'description_sale', 'rating', 'public_categ_ids', 'offer_data', 'dr_label_id'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_d_product_count_down.xml']),

    /**
     * @private
     */
    _getOptions: function () {
        var options = this._super.apply(this, arguments);
        if (this.selectionType) {
            options = options || {};
            options['shop_config_params'] = true;
        }
        return options;
    },
    /**
     * @private
     */
    _setDBData: function (data) {
        this.shopParams = data.shop_config_params;
        this._super.apply(this, arguments);
    },
    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        this.trigger_up('widgets_start_request', {
            editableMode: this.editableMode,
            $target: this.$('.s_countdown'),
        });
        this.$('.droggol_product_slider_top').owlCarousel({
            dots: false,
            margin: 20,
            stagePadding: 5,
            rewind: true,
            rtl: _t.database.parameters.direction === 'rtl',
            nav: true,
            navText: ['<i class="lnr h4 lnr-chevron-left"></i>', '<i class="lnr h4 lnr-chevron-right"></i>'],
            responsive: {
                0: {
                    items: 1
                },
                768: {
                    items: 2,
                },
                992: {
                    items: 1,
                },
                1200: {
                    items: 1,
                },
            },
        });
    },
});

publicWidget.registry.s_d_product_small_block = ProductRootWidget.extend(ProductsBlockMixins, {
    selector: '.s_d_product_small_block',

    bodyTemplate: 's_d_product_small_block_template',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    controllerRoute: '/droggol_theme_common/get_products_data',

    fieldstoFetch: ['name', 'price', 'rating', 'public_categ_ids', 'dr_label_id'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_d_product_count_down.xml']),

    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        var self = this;
        this._super.apply(this, arguments);
        var numOfCol = this.$el.hasClass('in_confirm_dialog') ? 4 : 3;

        this.$('.droggol_product_slider_top').owlCarousel({
            dots: false,
            margin: 20,
            stagePadding: 5,
            rewind: true,
            nav: true,
            rtl: _t.database.parameters.direction === 'rtl',
            navText: ['<i class="lnr h4 lnr-chevron-left"></i>', '<i class="lnr h4 lnr-chevron-right"></i>'],
            onInitialized: function () {
                var $img = self.$('.d-product-img:first');
                if (self.$('.d-product-img:first').length) {
                    $img.one("load", function () {
                        setTimeout(function () {
                            if (!config.device.isMobile) {
                                var height = self.$target.parents('.s_d_2_column_snippet').find('.s_d_product_count_down .owl-item.active').height();
                                self.$('.owl-item').height(height);
                            }
                        }, 300);
                    });
                }
            },
            responsive: {
                0: {
                items: 2,
                },
                576: {
                    items: 2,
                },
                768: {
                    items: 2,
                },
                992: {
                    items: 2,
                },
                1200: {
                    items: numOfCol,
                },
            },
        });
    },
});

publicWidget.registry.s_d_single_product_count_down = ProductRootWidget.extend(ProductsBlockMixins, {
    selector: '.s_d_single_product_count_down',

    bodyTemplate: 's_d_single_product_count_down_temp',

    controllerRoute: '/droggol_theme_common/get_products_data',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    fieldstoFetch: ['name', 'price', 'offer_data', 'description_sale'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_d_product_count_down.xml']),

    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        this.trigger_up('widgets_start_request', {
            editableMode: this.editableMode,
            $target: this.$('.s_countdown'),
        });
        this.$('.droggol_product_slider_single_product').owlCarousel({
            dots: false,
            margin: 20,
            rtl: _t.database.parameters.direction === 'rtl',
            stagePadding: 5,
            rewind: true,
            nav: true,
            navText: ['<i class="lnr lnr-arrow-left"></i>', '<i class="lnr lnr-arrow-right"></i>'],
            responsive: {
                0: {
                items: 1,
                },
            },
        });
    },
});

publicWidget.registry.s_d_image_products_block = ProductRootWidget.extend(ProductsBlockMixins, {
    selector: '.s_d_image_products_block_wrapper',

    bodyTemplate: 's_d_image_products_block_tmpl',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    bodySelector: '.s_d_image_products_block',

    controllerRoute: '/droggol_theme_common/get_products_data',

    fieldstoFetch: ['name', 'price', 'rating', 'public_categ_ids', 'dr_label_id'],

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_image_products.xml']),
    _processData: function (data) {
        var products = this._getProducts(data);
        var items = 6;
        if (config.device.isMobile) {
            items = 4;
        }
        var group = _.groupBy(products, function (product, index) {
            return Math.floor(index / (items));
        });
        return _.toArray(group);
    },
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        this.$('.droggol_product_slider_top').owlCarousel({
            dots: false,
            margin: 10,
            stagePadding: 5,
            rewind: true,
            nav: true,
            rtl: _t.database.parameters.direction === 'rtl',
            navText: ['<i class="lnr h4 lnr-chevron-left"></i>', '<i class="lnr h4 lnr-chevron-right"></i>'],
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
    },
});

});
