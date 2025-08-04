odoo.define('droggol_theme_common.wysiwyg', function (require) {
'use strict';

var WysiwygMultizone = require('web_editor.wysiwyg.multizone');
var snippetsEditor = require('web_editor.snippet.editor');

WysiwygMultizone.include({
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            if (this.$('.dr_offer_zone').length) {
                this.editor.snippetsMenu.toggleOfferSnippets(true);
            }
            if (this.$('.dr_category_zone').length) {
                this.editor.snippetsMenu.toggleCategorySnippets(true);
            }
        });
    },
});

snippetsEditor.Class.include({
    /**
     * @private
     * @param {boolean} show
     */
    toggleOfferSnippets: function (show) {
        setTimeout(() => this._activateSnippet(false));
        this.$('#snippet_offer').toggleClass('d-none', !show);
    },
    /**
     * @private
     * @param {boolean} show
     */
    toggleCategorySnippets: function (show) {
        setTimeout(() => this._activateSnippet(false));
        this.$('#snippet_category').toggleClass('d-none', !show);
    },
});

});
