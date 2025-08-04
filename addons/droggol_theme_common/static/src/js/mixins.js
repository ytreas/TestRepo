odoo.define('droggol_theme_common.mixins', function (require) {
"use strict";

var core = require('web.core');
var wUtils = require('website.utils');
var DroggolNotification = require('droggol_theme_common.notification');
var ConfirmationDialog = require('theme_prime.cart_confirmation_dialog');

var _t = core._t;
var qweb = core.qweb;

var DroggolUtils = {
    _getDomainWithWebsite: function (domain) {
        return domain.concat(wUtils.websiteDomain(this));
    },
};

var OwlMixin = {
    _initalizeOwlSlider: function (ppr) {
        var responsive = {
            0: {
                items: 1,
            },
            576: {
                items: 2,
            },
            768: {
                items: 3,
            },
            992: {
                items: 3,
            },
            1200: {
                items: ppr,
            }
        };
        if (this.$('.s_d_horizontal_card').length) {
            responsive = {
                0: {
                    items: 1,
                },
                576: {
                    items: ppr,
                },
            };
        }
        this.$('.droggol_product_slider').owlCarousel({
            dots: false,
            margin: 20,
            stagePadding: 5,
            rewind: true,
            rtl: _t.database.parameters.direction === 'rtl',
            nav: true,
            navText: ['<i class="lnr lnr-arrow-left"></i>', '<i class="lnr lnr-arrow-right"></i>'],
            responsive: responsive,
        });
    }
};

var CategoryMixins = {
    _getParsedSortBy: function (val) {
        var order = {
            price_asc: 'list_price asc',
            price_desc: 'list_price desc',
            name_asc: 'name asc',
            name_desc: 'name desc',
            newest_to_oldest: 'create_date desc',
        };
        return order[val];
    },
    /**
     * @private
     * @returns {Integer} categoryID
     */
    _fetchProductsByCategory: function (categoryID, includesChild, order, limit, fields) {
        var operator = '=';
        if (includesChild) {
            operator = 'child_of';
        }
        // this._rpc will work for now next version may includes service mixins
        return this._rpc({
            route: '/droggol_theme_common/get_products_by_category',
            params: {
                domain: [['public_categ_ids', operator, categoryID]],
                fields: fields,
                options: {
                    order: order,
                    limit: limit,
                }
            },
        });
    }
};
var CategoryPublicWidgetMixins = {
    /**
     * @private
     * @returns {Array} options
     */
    _getOptions: function () {
        var options = this._super.apply(this, arguments) || {};
        if (!this.initialCategory) {
            return false;
        }
        var categoryIDs = this.categoryParams.categoryIDs;
        options['order'] = this._getParsedSortBy(this.categoryParams.sortBy);
        options['limit'] = this.categoryParams.limit;
        // category name id vadi dict first time filter render karva mate
        options['get_categories'] = true;
        options['categoryIDs'] = categoryIDs;
        options['categoryID'] = this.initialCategory;
        return options;
    },
    /**
     * @private
     * @returns {Array} domain
     */
    _getDomain: function () {
        if (!this.initialCategory) {
            return false;
        }
        var operator = '=';
        if (this.categoryParams.includesChild) {
            operator = 'child_of';
        }
        return [['public_categ_ids', operator, this.initialCategory]];
    },
};
var SortableMixins = {
    /**
     * @private
     */
    _makeListSortable: function () {
        this.$('.d_sortable_block').nestedSortable({
            listType: 'ul',
            protectRoot: true,
            handle: '.d_sortable_item_handel',
            items: 'li',
            toleranceElement: '> .row',
            forcePlaceholderSize: true,
            opacity: 0.6,
            tolerance: 'pointer',
            placeholder: 'd_drag_placeholder',
            maxLevels: 0,
            expression: '()(.+)',
        });
    },
};
var ProductCarouselMixins = {
    _updateIDs: function ($target) {
        // carousel with same id fuck everything
        var newID = _.uniqueId('d_carousel_');
        $target.find('#o-carousel-product').addClass('d_shop_product_details_carousel');
        $target.find('#o-carousel-product').attr('id', newID);
        $target.find('[href="#o-carousel-product"]').attr('href', '#' + newID);
        $target.find('[data-target="#o-carousel-product"]').attr('data-target', '#' + newID);
    },
};
var ProductsBlockMixins = {
    start: function () {
        var productParams = this.$target.attr('data-products-params');
        this.productParams = productParams ? JSON.parse(productParams) : false;
        this.selectionType = false;
        if (this.productParams) {
            this.selectionType = this.productParams.selectionType;
        }
        return this._super.apply(this, arguments);
    },
    /**
    * @private
    */
    _getDomain: function () {
        var domain = false;
        switch (this.selectionType) {
            case 'manual':
                if (this.productParams.productIDs.length) {
                    domain = [['id', 'in', this.productParams.productIDs]];
                }
                break;
            case 'advance':
                if (_.isArray(this.productParams.domain_params.domain)) {
                    domain = this.productParams.domain_params.domain;
                }
                break;
        }
        return domain ? domain : this._super.apply(this, arguments);
    },
    /**
    * @private
    */
    _getLimit: function () {
        if (this.selectionType === 'advance') {
            return this.productParams.domain_params.limit || 5;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
    * @private
    */
    _getSortBy: function () {
        if (this.selectionType === 'advance') {
            return this.productParams.domain_params.sortBy;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
    * @private
    */
    _getProducts: function (data) {
        var products;
        var productParams = this.productParams;
        if (productParams) {
            switch (productParams.selectionType) {
                case 'manual':
                    // sort products in correct order
                    products = _.map(this.productParams.productIDs, function (productID) {
                        var product = _.findWhere(data.products, {id: productID});
                        if (product) {
                            return product;
                        }
                    });
                    break;
                case 'advance':
                    products = data.products;
                    break;
            }
        }
        return _.compact(products);
    },
    /**
    * @private
    */
    _processData: function (data) {
        this._super.apply(this, arguments);
        return this._getProducts(data);
    },
};

var CartManagerMixin = {

    _handleCartConfirmation: function (cart_flow, data) {
        var methodName = _.str.sprintf('_cart%s', _.str.classify(cart_flow));
        return this[methodName](data);
    },

    _cartNotification: function (data) {
        return this.displayNotification({
            Notification: DroggolNotification,
            sticky: true,
            type: 'abcd',
            message: qweb.render('DroggolAddToCartNotification', { name: data.product_name }),
            className: 'd_notification d_notification_primary',
            d_icon: 'lnr lnr-cart text-primary',
            d_image: _.str.sprintf('/web/image/product.product/%s/image_256', this.rootProduct.product_id),
            buttons: [{
                text: _t('View cart'),
                class: 'btn btn-link btn-sm p-0',
                link: true, href: '/shop/cart'
            }]
        });
    },

    _cartDialog: function (data) {
        new ConfirmationDialog(this, {
            data: data,
            size: 'medium'
        }).open();
    },

    _cartSideCart: function (data) {
        if (!$('.dr_sale_cart_sidebar_container.open').length) {
            if ($('.dr_sale_cart_sidebar:first').length) {
                $('.dr_sale_cart_sidebar:first').trigger('click');
                return;
            }
        }
        // Fallback on notification in case menu is not there
        return this._cartNotification(data);
    },
};

return {
    DroggolUtils: DroggolUtils,
    OwlMixin: OwlMixin,
    CategoryMixins: CategoryMixins,
    CategoryPublicWidgetMixins: CategoryPublicWidgetMixins,
    SortableMixins: SortableMixins,
    ProductCarouselMixins: ProductCarouselMixins,
    ProductsBlockMixins: ProductsBlockMixins,
    CartManagerMixin: CartManagerMixin,
};
});
