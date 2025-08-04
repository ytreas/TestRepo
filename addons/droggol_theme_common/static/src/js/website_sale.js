odoo.define('droggol_theme_common.website_sale', function (require) {
'use strict';

require('website_sale.cart');
var core = require('web.core');
var qweb = core.qweb;
var publicWidget = require('web.public.widget');
var portalChatter = require('portal.chatter');
var PortalChatter = portalChatter.PortalChatter;
var wSaleUtils = require('website_sale.utils');

PortalChatter.include({
    xmlDependencies: (PortalChatter.prototype.xmlDependencies || [])
        .concat([
            '/droggol_theme_common/static/src/xml/portal_chatter.xml'
        ]),
});

// Add to cart popover
publicWidget.registry.websiteSaleCartLink.include({
    selector: '#top_menu a[href$="/shop/cart"]:not(.dr_sale_cart_sidebar)',
});
publicWidget.registry.DrSaleCartSidebar = publicWidget.Widget.extend({
    selector: '.dr_sale_cart_sidebar',
    read_events: {
        'click': '_onClick',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.$backdrop = $('<div class="modal-backdrop show"/>');
    },
    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        $.get('/shop/cart', {
            type: 'dr_sale_cart_request',
        }).then(function (data) {
            var $data = $(data);
            $data.appendTo('body');
            $data.addClass('open', 500, 'linear');
            self.$backdrop.appendTo('body');
            $('body').addClass('modal-open');
            self.trigger_up('widgets_start_request', {
                $target: $data,
                options: {
                    $drCartBackdropEl: self.$backdrop
                }
            });
        });
    },
});

publicWidget.registry.CartManger = publicWidget.Widget.extend({
    selector: '.dr_sale_cart_sidebar_container',

    read_events: {
        'click .dr_sale_cart_sidebar_close': '_removeSidebar',
        'click .d_remove_cart_line': 'async _onRemoveLine',
    },

    init: function (parent, options) {
        this.$backdrop = options.$drCartBackdropEl;
        this.$backdrop.on('click', this._removeSidebar.bind(this));
        return this._super.apply(this, arguments);
    },

    _removeSidebar: function (ev) {
        ev.preventDefault();
        this.$backdrop.remove();
        this.$el.removeClass('open', 500, 'linear', function () {
            $('body').removeClass('modal-open');
            $('.dr_sale_cart_sidebar_container').remove();
        });
    },
    _onRemoveLine: function (ev) {
        ev.preventDefault();
        var lineId = $(ev.currentTarget).data('line-id');
        var productId = $(ev.currentTarget).data('product-id');
        return this._rpc({
            route: "/shop/cart/update_json",
            params: {
                line_id: lineId,
                product_id: productId,
                set_qty: 0
            }
        }).then(this._refreshCart.bind(this));
    },

    _refreshCart: function (data) {
        var self = this;
        data['cart_quantity'] = data.cart_quantity || 0;
        wSaleUtils.updateCartNavBar(data);
        return $.get('/shop/cart', {
            type: 'dr_sale_cart_request',
        }).then(function (data) {
            var $data = $(data);
            self.$el.children().remove();
            $data.children().appendTo(self.$el);
            return;
        });
    }

});

publicWidget.registry.DrAjaxLoadProducts = publicWidget.Widget.extend({
    xmlDependencies: ['/droggol_theme_common/static/src/xml/website_sale.xml'],
    selector: '#products_grid',
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        var ajaxEnabled = this.$target.attr('data-ajax-enable');
        this.ajaxEnabled = ajaxEnabled ? ajaxEnabled : false;
        this.$pager = $('.products_pager:not(.dr_dump_pager)');
        if (this.ajaxEnabled && this.$pager.children().length && this.$('.o_wsale_products_grid_table_wrapper tbody tr:last').length) {
            this.$pager.addClass('d-none');
            this._setState();
            var position = $(window).scrollTop();
            $(window).on('scroll.ajax_load_product', _.throttle(function (ev) {
                var scroll = $(window).scrollTop();
                if (scroll > position) {
                    // Trigger only when scrollDown
                    self._onScrollEvent(ev);
                }
                position = scroll;
            }, 20));
        }
        return Promise.all(defs);
    },
    _setState: function () {
        this.$lastLoadedProduct = this.$('.o_wsale_products_grid_table_wrapper tbody tr:last');
        this.$productsContainer = this.$('.o_wsale_products_grid_table_wrapper tbody');
        this.readyNextForAjax = true;
        this.pageURL = this.$pager.find('li:last a').attr('href');
        this.lastLoadedPage = 1;
        var pages = $('.dr_dump_pager').attr('data-total-page');
        this.totalPages = pages ? parseInt(pages) : false;
    },
    _onScrollEvent: function (ev) {
        var self = this;
        if (this.$lastLoadedProduct.offset().top - $(window).scrollTop() + this.$lastLoadedProduct.height() < $(window).height() - 25 && this.readyNextForAjax && this.totalPages > this.lastLoadedPage) {
            this.readyNextForAjax = false;
            var newPage = self.lastLoadedPage + 1;
            $.ajax({
                url: this.pageURL,
                type: 'GET',
                beforeSend: function () {
                    var tmpl = qweb.render('droggol_small_loader');
                    $(tmpl).appendTo(self.$('.o_wsale_products_grid_table_wrapper'));
                },
                success: function (page) {
                    self.$('.dr_small_loader').remove();
                    var $renderedPage = $(page);
                    var $productsToAdd = $renderedPage.find("#products_grid .o_wsale_products_grid_table_wrapper table tr");
                    self.$productsContainer.append($productsToAdd);
                    self.readyNextForAjax = true;
                    self.$lastLoadedProduct = self.$('.o_wsale_products_grid_table_wrapper tbody tr:last');
                    self.lastLoadedPage = newPage;
                    self.pageURL = $renderedPage.find('.products_pager:not(.dr_dump_pager) li:last a').attr('href');
                    if ($renderedPage.find('.products_pager:not(.dr_dump_pager) li:last').hasClass('disabled')) {
                        var tmpl = qweb.render('dr_all_products_loaded');
                        $(tmpl).appendTo(self.$('.o_wsale_products_grid_table_wrapper'));
                    }
                }
            });
        }
    },
});
});
