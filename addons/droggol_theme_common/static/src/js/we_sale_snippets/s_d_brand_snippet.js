odoo.define('droggol_theme_common.s_d_brand_snippet', function (require) {
"use strict";

var core = require('web.core');
var publicWidget = require('web.public.widget');
var RootWidget = require('droggol_theme_common.root.widget');

var _t = core._t;

publicWidget.registry.s_d_brand_snippet = RootWidget.extend({
    selector: '.s_d_brand_snippet_wrapper',

    controllerRoute: '/droggol_theme_common/get_brands',
    bodyTemplate: 's_d_brand_snippet',
    bodySelector: '.s_d_brand_snippet',

    fieldstoFetch: ['id'],

    displayAllProductsBtn: false,

    noDataTemplateString: _t("No brands are found!"),

    noDataTemplateSubString: _t("Sorry, We couldn't find any brands right now"),

    xmlDependencies: (RootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_d_brand_snippet.xml']),

    start: function () {
        var brandsCount = this.$target.attr('data-brand-limit');
        this.brandsCount = brandsCount ? JSON.parse(brandsCount) : 12;
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _getOptions: function () {
        return {
            'limit': this.brandsCount,
        };
    },
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        if (this.$target.hasClass('dr_slider_mode')) {
            this.$('.s_d_brand_snippet > .row').addClass('owl-carousel');
            // remove col-* classses
            this.$('.s_d_brand_snippet > .row > *').removeAttr('class');
            this.$('.s_d_brand_snippet > .row').removeClass('row');
            this.$('.owl-carousel').owlCarousel({
                nav: false,
                autoplay: true,
                autoplayTimeout: 4000,
                margin: 10,
                responsive: {
                    0: {
                        items: 2,
                    },
                    576: {
                        items: 4,
                    },
                }
            });
        }
    },
});

});
