odoo.define('droggol_theme_common.quick_view_product_btn', function (require) {
'use strict';

var QuickViewDialog = require('droggol_theme_common.product_quick_view');
var publicWidget = require('web.public.widget');

publicWidget.registry.d_product_quick_view = publicWidget.Widget.extend({
    selector: '.oe_website_sale',

    read_events: {
        'click .d_product_quick_view_btn': '_onProductQuickViewClick',
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onProductQuickViewClick: function (ev) {
        this.QuickViewDialog = new QuickViewDialog(this, {
            productID: parseInt($(ev.currentTarget).attr('data-product-id'))
        });
        this.QuickViewDialog.open();
    },
});

});
