odoo.define('droggol_theme_common.s_category_snippet', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var ProductRootWidget = require('droggol_theme_common.product.root.widget');
var core = require('web.core');
var Mixins = require('droggol_theme_common.mixins');

var OwlMixin = Mixins.OwlMixin;
var CategoryMixins = Mixins.CategoryMixins;
var CategoryPublicWidgetMixins = Mixins.CategoryPublicWidgetMixins;

var qweb = core.qweb;
var _t = core._t;

publicWidget.registry.s_category_snippet = ProductRootWidget.extend(OwlMixin, CategoryMixins, CategoryPublicWidgetMixins, {
    selector: '.s_d_category_snippet_wrapper',

    drClearAttributes: (ProductRootWidget.prototype.drClearAttributes || []).concat(['data-category-params', 'data-category-filter']),

    bodyTemplate: 'd_s_category_cards_wrapper',

    bodySelector: '.s_d_category_snippet',

    controllerRoute: '/droggol_theme_common/get_products_by_category',

    fieldstoFetch: ['name', 'price', 'description_sale', 'dr_label_id', 'rating', 'public_categ_ids', 'product_template_image_ids'],

    noDataTemplateSubString: _t("Sorry, We couldn't find any products under this category"),

    read_events: _.extend({
        'click .d_category_lable': '_onCategoryLableClick',
    }, ProductRootWidget.prototype.read_events),

    xmlDependencies: (ProductRootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/cards.xml',
        '/droggol_theme_common/static/src/xml/category_filters.xml']),

    start: function () {
        var categoryParams = this.$target.attr('data-category-params');
        var categoryFilterStyle = this.$target.attr('data-category-filter');
        this.categoryParams = categoryParams ? JSON.parse(categoryParams) : false;
        this.categoryFilterStyle = categoryFilterStyle ? JSON.parse(categoryFilterStyle) : false;
        this.initialCategory = false;
        if (this.categoryParams) {
            var categoryIDs = this.categoryParams.categoryIDs;
            // first category
            this.initialCategory = categoryIDs.length ? categoryIDs[0] : false;
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Activate clicked category
     * @param {Integer} categoryID
     * @private
     */
    _activateCategory: function (categoryID) {
        this.$('.d_s_category_cards_item').addClass('d-none');
        this.$('.d_s_category_cards_item[data-category-id=' + categoryID + ']').removeClass('d-none');
    },
    /**
     * Fetch and render products for category
     * @private
     * @param {Integer} categoryID
     */
    _fetchAndAppendByCategory: function (categoryID) {
        this._activateCategory(categoryID);
        this._fetchProductsByCategory(categoryID, this.categoryParams.includesChild, this._getParsedSortBy(this.categoryParams.sortBy), this.categoryParams.limit, this.fieldstoFetch).then(data => {
            this._renderNewProducts(data.products, categoryID);
        });
    },
    /**
     * initialize owlCarousel.
     * @override
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        var categories = this.fetchedCategories;
        // if first categories is archive or moved to another website then activate first category
        if (categories.length && categories[0] !== this.initialCategory) {
            this._fetchAndAppendByCategory(categories[0]);
        }
        if (this.userParams.layoutType === 'slider') {
            this._initalizeOwlSlider(this.userParams.ppr);
        }
    },
    /**
     * @override
     */
    _processData: function (data) {
        var categories = this.fetchedCategories;

        if (!categories.length) {
            this._appendNoDataTemplate();
            return [];
        }

        // if initialCategory is archive or moved to another website
        if (categories.length && categories[0] !== this.initialCategory) {
            return [];
        } else {
            return data.products;
        }
    },
    /**
     * Render and append new products.
     * @private
     * @param {Array} products`
     * @param {Integer} categoryID`
     */
    _renderNewProducts: function (products, categoryID) {
        var $tmpl = $(qweb.render('d_s_category_cards_item', {
            data: products,
            widget: this,
            categoryID: categoryID
        }));
        this.$('.d_loader_default').remove();
        $tmpl.appendTo(this.$('.d_s_category_cards_container'));
        this._initalizeOwlSlider(this.userParams.ppr);
    },
    /**
     * @override
     */
    _setDBData: function (data) {
        var categories = _.map(this.categoryParams.categoryIDs, function (categoryID) {
            return _.findWhere(data.categories, {id: categoryID});
        });
        this.categories = _.compact(categories);
        this.fetchedCategories = _.map(this.categories, function (category) {
            return category.id;
        });
        this.categoryParams.categoryIDs = this.fetchedCategories;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCategoryLableClick: function (ev) {
        var $target = $(ev.currentTarget);
        this.$('.d_category_lable').removeClass('d_active');
        $target.addClass('d_active');
        var categoryID = parseInt($target.attr('data-category-id'), 10);
        if (!this.$('.d_s_category_cards_item[data-category-id=' + categoryID + ']').length) {
            if (this.loaderTemplate) {
                var $template = $(qweb.render(this.loaderTemplate));
                $template.addClass('d_loader_default');
                $template.appendTo(this.$('.d_s_category_cards_container'));
            }
            this._fetchAndAppendByCategory(categoryID);
        } else {
            this._activateCategory(categoryID);
        }
    },
});

});
