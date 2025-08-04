odoo.define('droggol_theme_common.product_selector', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('web_editor.widget');
var Select2Widget = require('droggol_theme_common.widgets.select2_widget');

var _t = core._t;

return weWidgets.Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: options.fieldLabel || _t("Droggol"),
            dialogClass: 'd-product-selector-dialog',
            technical: false,
            buttons: [
                {text: _t('Choose'), classes: 'btn-primary', close: true, click: this._onFinalPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
        }, {}));
        this.options = options;
    },
    /**
     * @override
     */
    start: function () {
        this.select2Widget = new Select2Widget(this, this.options);
        this.select2Widget.appendTo(this.$el);
        this.$modal.addClass('droggol_technical_modal');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    _onFinalPick: function () {
        this.trigger_up('d_product_pick', {result: this.select2Widget.getValue()});
    },
});
});
