odoo.define('droggol_theme_common.product_quick_view', function (require) {
'use strict';

var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');
// Comparison is not used anywhere in this file it is here just to make sure that
// ProductComparison publicWidget added to registry
var Mixins = require('droggol_theme_common.mixins');

var ProductCarouselMixins = Mixins.ProductCarouselMixins;
require('website_sale_comparison.comparison');

publicWidget.registry.ProductComparison.include({
    selector: '.oe_website_sale:not(.d_website_sale)',
});

return Dialog.extend(ProductCarouselMixins, {
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/we_sale_snippets/dialog_product_quick_view.xml']
    ),
    template: 'droggol_theme_common.product_quick_view',
    events: _.extend({}, Dialog.prototype.events, {
        'dr_close_dialog': 'close',
    }),
    /**
     * @constructor
     */
    init: function (parent, options) {
        this.productID = options.productID;
        this.mini = options.mini || false;
        this.variantID = options.variantID || false;
        this.add_if_single_variant = options.add_if_single_variant || false;
        this.size = options.size || 'extra-large';
        this._super(parent, _.extend({
            renderHeader: false,
            renderFooter: false,
            technical: false,
            size: this.size,
            backdrop: true,
        }, options || {}));
    },
    // /**
    //  * @override
    //  */
    willStart: function () {
        var self = this;
        var allPromise = [this._super.apply(this, arguments)];
        this.contentPromise = ajax.jsonRpc('/droggol_theme_common/get_quick_view_html', 'call', {
            'options': {
                productID: this.productID,
                variantID: this.variantID,
                mini: this.mini,
                add_if_single_variant: this.add_if_single_variant,
            }
        }).then(function (content) {
            if (self.add_if_single_variant && $(content).hasClass('auto-add-product')) {
                self.preventOpening = true;
            }
            return content;
        });
        if (this.add_if_single_variant) {
            allPromise.push(this.contentPromise);
        }
        return Promise.all(allPromise);
    },
    /**
     * @override
     */
    start: function () {
        var sup = this._super.apply(this, arguments);
        // Append close button to dialog
        $('<button/>', {
            class: 'close',
            'data-dismiss': "modal",
            html: '<i class="lnr lnr-cross"/>',
        }).prependTo(this.$modal.find('.modal-content'));
        this.$modal.find('.modal-dialog').addClass('modal-dialog-centered d_product_quick_view_dialog dr_full_dialog');
        if (this.mini) {
            this.$modal.find('.modal-dialog').addClass('is_mini');
        }
        this.contentPromise.then(data => {
            this.$el.find('.d_product_quick_view_loader').replaceWith(data);
            this._updateIDs(this.$el);
            this.trigger_up('widgets_start_request', {
                $target: this.$('.oe_website_sale'),
            });
        });
        if (this.preventOpening) {
            return Promise.reject();
        }
        return sup;
    }
});
});
