odoo.define('droggol_theme_common.snippet_general', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.dr_s_coming_soon = publicWidget.Widget.extend({
    selector: '.s_coming_soon',
    disabledInEditableMode: false,

    start: function () {
        if (!this.editableMode || !this.$('.d_count_down_over').length) {
            $('body').css('overflow', 'hidden');
        }
        if (this.editableMode) {
            this.$target.removeClass('d-none');
            $('body').css('overflow', 'auto');
        }
        return this._super.apply(this, arguments);
    },
    destroy: function () {
        $('body').css('overflow', 'auto');
        this._super.apply(this, arguments);
    },
});

});
