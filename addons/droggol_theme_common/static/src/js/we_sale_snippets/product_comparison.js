odoo.define('droggol_theme_common.product_comparison', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
require('website_sale_comparison.comparison');

publicWidget.registry.ProductComparison.include({
    // change selector
    selector: '#wrap',
    read_events: _.extend({
        'click .d_product_comparison': '_onClickCompareBtn',
    }, publicWidget.registry.ProductComparison.prototype.read_events),

    /**
     * @override
     */
    start: function () {
        var defs = [];

        // Right now we are calling super if #wrap contains .droggol_product_snippet
        // For V14 we only call super if wishlist feature is enabled for snippet.

        // var comparisonEnabled = false;
        // var $snippets = this.$('.droggol_product_snippet[data-user-params]');
        // _.each($snippets, function (snippet) {
        //     var $snippet = $(snippet);
        //     var userParams = $snippet.attr('data-user-params');
        //     userParams = userParams ? JSON.parse(userParams) : false;
        //     if (userParams && userParams.comparison) {
        //         comparisonEnabled = true;
        //     }
        // });
        if (this.$('.droggol_product_snippet[data-user-params]').length || this.$('.oe_website_sale').length) {
            defs.push(this._super.apply(this, arguments));
        }
        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickCompareBtn: function (ev) {
        var productId = $(ev.currentTarget).data('product-product-id');
        var comparison = this.productComparison;
        if (comparison.comparelist_product_ids.length < this.productComparison.product_compare_limit) {
            comparison._addNewProducts(productId);
        } else {
            comparison.$el.find('.o_comparelist_limit_warning').show();
            $('#comparelist .o_product_panel_header').popover('show');
        }
    },
});
});
