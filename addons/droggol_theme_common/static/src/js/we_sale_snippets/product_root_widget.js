odoo.define('droggol_theme_common.product.root.widget', function (require) {
'use strict';

var core = require('web.core');
var DroggolRootWidget = require('droggol_theme_common.root.widget');
var DroggolNotification = require('droggol_theme_common.notification');
var QuickViewDialog = require('droggol_theme_common.product_quick_view');
var wSaleUtils = require('website_sale.utils');

var qweb = core.qweb;
var _t = core._t;

return DroggolRootWidget.extend({

    xmlDependencies: (DroggolRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/droggol_notification_template.xml']),

    drClearAttributes: (DroggolRootWidget.prototype.drClearAttributes || []).concat(['data-user-params']),
    // Button par '.d_add_to_cart_btn' hovo compulsory che
    read_events: {
        'click .d_add_to_cart_btn': '_onAddToCartClick',
        'click .d_add_to_wishlist_btn': '_onAddtoWishlistClick',
        'click .d_product_quick_view': '_onProductQuickViewClick',
        'mouseenter .d_product_thumb_img': '_onMouseEnter',
    },

    /**
     * @override
     */
    start: function () {
        var userParams = this.$target.attr('data-user-params');
        this.userParams = userParams ? JSON.parse(userParams) : false;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Khangi/Private
    //--------------------------------------------------------------------------

    /**
    * @private
    */
    _addProductToCart: function (cartInfo) {
        // Do not add variant for default flow
        var isCustomFlow = _.contains(['side_cart', 'dialog', 'notification'], odoo.session_info.dr_cart_flow || 'default');
        var dialogOptions = {
            mini: true,
            size: 'small',
            add_if_single_variant: isCustomFlow,
        };
        dialogOptions['variantID'] = cartInfo.productID;
        this.QuickViewDialog = new QuickViewDialog(this, dialogOptions).open();
        return this.QuickViewDialog;
    },
    /**
    * @private
    */
    _getCartParams: function (ev) {
        return {
            productID: parseInt($(ev.currentTarget).attr('data-product-product-id')),
            qty: 1,
        };
    },
    /**
    * @private
    */
    _getOptions: function () {
        var options = {};
        // add new attribute to widget or just set data-userParams to $target
        if (this.userParams) {
            if (this.userParams.wishlist) {
                options['wishlist_enabled'] = true;
            }
            // fetch shop config only if 'wishlist', 'comparison', 'rating'
            // any one of this is enabled in current snippet
            if (this._anyActionEnabled(this._getMustDisabledOptions())) {
                options['shop_config_params'] = true;
            }
            return options;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
    * Check any given option is enabled(true) in userParams.
    * e.g. this.userParams.wishlist = true;
    * this method return true if any one of given option is true
    * @private
    */
    _anyActionEnabled: function (options) {
        return _.contains(_.values(_.pick(this.userParams, options)), true);
    },
    /**
     * @private
     */
    _getAllActions: function () {
        return ['wishlist', 'comparison', 'add_to_cart', 'quick_view'];
    },
    /**
    * @private
    * @see _getMustDisabledOptions of configurator
    */
    _getMustDisabledOptions: function () {
        return ['wishlist', 'comparison', 'rating'];
    },
    /**
     * init tooltips
     *
     * @private
     */
    _initTips: function () {
        this.$('[data-toggle="tooltip"]').tooltip();
    },
    /**
     * @override
     */
    _modifyElementsAfterAppend: function () {
        var self = this;
        this._initTips();
        _.each(this.wishlistProductIDs, function (id) {
            self.$('.d_add_to_wishlist_btn[data-product-product-id="' + id + '"]').prop("disabled", true).addClass('disabled');
        });
        this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _updateUserParams: function (shopConfigParams) {
        var self = this;
        if (this.userParams) {
            _.each(this._getMustDisabledOptions(), function (option) {
                var enabledInShop = shopConfigParams['is_' + option + '_active'];
                if (!enabledInShop) {
                    self.userParams[option] = false;
                }
            });
            // whether need to render whole container for
            // e.g if all actions are disabled then donot render overlay(contains add to card, wishlist btns etc)
            this.userParams['anyActionEnabled'] = this._anyActionEnabled(this._getAllActions());
        }
    },
    /**
    * Method is copy of wishlist public widget
    *
    * @private
    */
    _updateWishlistView: function () {
        if (this.wishlistProductIDs.length > 0) {
            $('.o_wsale_my_wish').show();
            $('.my_wish_quantity').text(this.wishlistProductIDs.length);
        } else {
            $('.o_wsale_my_wish').show();
            $('.my_wish_quantity').text('');
        }
    },
    /**
    * @private
    */
    _setDBData: function (data) {
        if (data.wishlist_products) {
            this.wishlistProductIDs = data.wishlist_products;
        }
        if (data.shop_config_params) {
            this._updateUserParams(data.shop_config_params);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param  {Event} ev
     */
    _onAddToCartClick: function (ev) {
        this._addProductToCart(this._getCartParams(ev));
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onProductQuickViewClick: function (ev) {
        // set $parentNode to fix bug
        this.QuickViewDialog = new QuickViewDialog(this, {
            productID: parseInt($(ev.currentTarget).attr('data-product-template-id')),
        });
        this.QuickViewDialog.open();
    },
    /**
    * @private
    */
    _removeProductFromWishlist: function (wishlistID, productID) {
        var self = this;
        this._rpc({
            route: '/shop/wishlist/remove/' + wishlistID,
        }).then(function () {
            $(".d_add_to_wishlist_btn[data-product-product-id='" + productID + "']").prop("disabled", false).removeClass('disabled');
            self.wishlistProductIDs = _.filter(self.wishlistProductIDs, function (id) {
                 return id !== productID;
             });
            self._updateWishlistView();
        });
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onAddtoWishlistClick: function (ev) {
        var productID = parseInt($(ev.currentTarget).attr('data-product-product-id'));
        this._rpc({
            route: '/droggol_theme_common/wishlist_general',
            params: {
                product_id: productID,
            },
        }).then(res => {
            this.wishlistProductIDs = res.products;
            this.displayNotification({
                Notification: DroggolNotification,
                sticky: false,
                type: 'abcd',
                message: qweb.render('DroggolWishlistNotification', {name: res.name}),
                className: 'd_notification d_notification_danger',
                d_image: _.str.sprintf('/web/image/product.product/%s/image_256', productID),
                buttons: [{
                    text: _t('See your wishlist'),
                    class: 'btn btn-link btn-sm p-0',
                    link: true,
                    href: '/shop/wishlist'
                    }, {
                    text: _t('Undo'),
                    class: 'btn btn-link btn-sm float-right',
                    click: this._removeProductFromWishlist.bind(this, res.wishlist_id, productID),
                }]
            });
            this._updateWishlistView();
            $(".d_add_to_wishlist_btn[data-product-product-id='" + productID + "']").prop("disabled", true).addClass('disabled');
        });
    },
    /**
     * @private
     */
    _onMouseEnter: function (ev) {
        var $target = $(ev.currentTarget);
        var src = $target.attr('src');
        var productID = $target.attr('data-product-id');
        var $card = this.$('.d_product_card[data-product-id=' + productID + ']');
        $card.find('.d-product-img').attr('src', src);
        $card.find('.d_product_thumb_img').removeClass('d_active');
        $target.addClass('d_active');
    },
});

});
