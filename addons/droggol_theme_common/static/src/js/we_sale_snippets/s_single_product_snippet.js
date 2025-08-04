odoo.define('droggol_theme_common.s_single_product_snippet', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var RootWidget = require('droggol_theme_common.root.widget');

var Mixins = require('droggol_theme_common.mixins');
var core = require('web.core');

var qweb = core.qweb;
var _t = core._t;

var ProductCarouselMixins = Mixins.ProductCarouselMixins;

publicWidget.registry.s_d_single_product_cover_snippet = RootWidget.extend(ProductCarouselMixins, {
    selector: '.s_d_single_product_cover_snippet_wrapper',

    bodyTemplate: 's_d_single_product_cover_snippet',
    bodySelector: '.s_d_single_product_cover_snippet',

    controllerRoute: '/droggol_theme_common/get_single_product_data',
    noDataTemplateString: _t("No product found"),
    noDataTemplateSubString: _t("Sorry, this product is not available right now"),
    displayAllProductsBtn: false,

    drClearAttributes: (RootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    xmlDependencies: (RootWidget.prototype.xmlDependencies || [])
    .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_single_product_snippet.xml']),

    start: function () {
        var productParams = this.$target.attr('data-products-params');
        this.productParams = productParams ? JSON.parse(productParams) : false;
        this.initialProduct = false;
        this.productIDs = false;
        if (this.productParams) {
            var productIDs = this.productParams.productIDs;
            // first category
            if (productIDs.length) {
                this.initialProduct = productIDs[0];
                this.productIDs = productIDs;
            }
        }
        return this._super.apply(this, arguments);
    },
    /**
    * @private
    */
    _getOptions: function () {
        var options = {};
        if (this.initialProduct) {
            options['productID'] = this.initialProduct;
            return options;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        this.trigger_up('widgets_start_request', {
            $target: this.$('.oe_website_sale'),
        });
        this._updateIDs(this._getBodySelectorElement());
    }
});
publicWidget.registry.s_single_product_snippet = RootWidget.extend(ProductCarouselMixins, {
    selector: '.s_d_single_product_snippet_wrapper',

    drClearAttributes: (RootWidget.prototype.drClearAttributes || []).concat(['data-products-params']),

    bodyTemplate: 's_single_product_snippet',
    controllerRoute: '/droggol_theme_common/get_quick_view_html',
    bodySelector: '.d_single_product_continer',
    noDataTemplateString: _t("No product found"),
    noDataTemplateSubString: _t("Sorry, this product is not available right now"),
    displayAllProductsBtn: false,

    xmlDependencies: (RootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_single_product_snippet.xml']),

    start: function () {
        var productParams = this.$target.attr('data-products-params');
        this.productParams = productParams ? JSON.parse(productParams) : false;
        this.initialProduct = false;
        this.productIDs = false;
        if (this.productParams) {
            var productIDs = this.productParams.productIDs;
            // first category
            if (productIDs.length) {
                this.initialProduct = productIDs[0];
                this.productIDs = productIDs;
            }
        }
        return this._super.apply(this, arguments);
    },
    /**
    * @private
    */
    _getOptions: function () {
        var options = {};
        if (this.initialProduct) {
            options['productID'] = this.initialProduct;
            return options;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    _modifyElementsAfterAppend: function () {
        var self = this;
        this._super.apply(this, arguments);
        this.trigger_up('widgets_start_request', {
            $target: this.$('.oe_website_sale'),
        });
        this._updateIDs(this.$('.d_single_product_body[data-index=0]'));
        var $slider = this.$('.droggol_product_slider');
        $slider.owlCarousel({
            rewind: true,
            nav: true,
            margin: 20,
            rtl: _t.database.parameters.direction === 'rtl',
            stagePadding: 5,
            navText: ['<i class="lnr lnr-arrow-left"></i>', '<i class="lnr lnr-arrow-right"></i>'],
            responsive: {
                0: {
                    items: 1
                }
            },
        });
        $slider.on('changed.owl.carousel', function (event) {
            var index = event.item.index;
            var $nextItem = self.$('.d_single_product_body[data-index=' + index + ']');
            if (!$.trim($nextItem.html()).length) {
                var productID = parseInt($nextItem.attr('data-product-id'), 10);
                self._fetchProductsHtml(productID);
            }
        });
    },
    _fetchProductsHtml: function (productID) {
        this._rpc({
            route: '/droggol_theme_common/get_quick_view_html',
            params: {
                options: {productID: productID}
            },
        }).then(data => {
            var $target = this.$('.d_single_product_body[data-product-id=' + productID + ']');
            if (_.isArray(data)) {
                var $template = $(qweb.render(this.noDataTemplate, {data: data, widget: this}));
                $template.appendTo($target);
            } else {
                $target.html(data);
                this._updateIDs($target);
                this.trigger_up('widgets_start_request', {
                    $target: $target.find('.oe_website_sale'),
                });
            }
        });
    },
});
});
