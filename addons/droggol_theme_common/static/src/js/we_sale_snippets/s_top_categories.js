odoo.define('droggol_theme_common.s_top_categories', function (require) {
"use strict";

var core = require('web.core');
var publicWidget = require('web.public.widget');
var RootWidget = require('droggol_theme_common.root.widget');
var Mixins = require('droggol_theme_common.mixins');

var CategoryMixins = Mixins.CategoryMixins;

var _t = core._t;

publicWidget.registry.s_d_top_categories = RootWidget.extend(CategoryMixins, {
    selector: '.s_d_top_categories',

    bodyTemplate: 's_top_categories_snippet',
    controllerRoute: '/droggol_theme_common/get_top_categories',

    drClearAttributes: (RootWidget.prototype.drClearAttributes || []).concat(['data-category-params']),

    xmlDependencies: (RootWidget.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_top_categories.xml']),

    noDataTemplateString: _t("No categories found!"),

    noDataTemplateSubString: false,
    displayAllProductsBtn: false,

    start: function () {
        var categoryParams = this.$target.attr('data-category-params');
        this.categoryParams = categoryParams ? JSON.parse(categoryParams) : false;
        return this._super.apply(this, arguments);
    },
    /**
    * @private
    */
   _getOptions: function () {
       var options = {};
       if (this.categoryParams) {
           this.categoryParams['sortBy'] = this._getParsedSortBy(this.categoryParams.sortBy);
           options['params'] = this.categoryParams;
           return options;
        } else {
            return this._super.apply(this, arguments);
        }
    },
    _setDBData: function (data) {
        this._super.apply(this, arguments);
        var FetchedCategories = _.map(data, function (category) {
            return category.id;
        });
        var categoryIDs = [];
        _.each(this.categoryParams.categoryIDs, function (categoryID) {
            if (_.contains(FetchedCategories, categoryID)) {
                categoryIDs.push(categoryID);
            }
        });
        this.categoryParams.categoryIDs = categoryIDs;
    },
    /**
    * @private
    */
    _processData: function (data) {
        return _.map(this.categoryParams.categoryIDs, function (categoryID) {
            return _.findWhere(data, {id: categoryID});
        });
    },
});

});
