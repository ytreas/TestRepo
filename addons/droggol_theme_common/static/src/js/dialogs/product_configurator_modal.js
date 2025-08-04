odoo.define('droggol_theme_common.product_configurator_modal', function (require) {
'use strict';
var OptionalProductsModal = require('sale_product_configurator.OptionalProductsModal');

OptionalProductsModal.include({
    init: function (parent, params) {
        this._super(parent, params);
        // [FIX] : changes container bcoz other wise modal will append to the form inside body this
        // thing create issue for QuickViewDialog and single product snippet
        this.container = $(parent).hasClass('d_cart_update_form') ? $('body')[0] : parent;
    },
});

});
