odoo.define('droggol_theme_common.s_dynamic_mega_menu', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var DroggolRootWidget = require('droggol_theme_common.root.widget');

publicWidget.registry.s_d_category_mega_menu_3 = DroggolRootWidget.extend({
    selector: '.droggol_category_mega_menu_snippet',
    controllerRoute: '/droggol_theme_common/get_mega_menu_categories',
    xmlDependencies: (DroggolRootWidget.prototype.xmlDependencies || [])
    .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_dynamic_mega_menu.xml']),
    bodyTemplate: 's_d_category_mega_menu_3',
    drClearAttributes: (DroggolRootWidget.prototype.drClearAttributes || []).concat(['data-categories']),
    start: function () {
        var categoryParams = this.$target.attr('data-categories');
        var categoryIDs = categoryParams ? JSON.parse(categoryParams) : false;
        this.categoryIDs = categoryIDs;
        return this._super.apply(this, arguments);
    },
    _getOptions: function () {
        return {
            categoryIDs: this.categoryIDs || []
        };
    },
    _processData: function (data) {
        var categoryIDs = _.map(this.categoryIDs, function (categoryID) {
           var product = _.findWhere(data, {id: categoryID});
           if (product) {
               return product;
           }
        });
        return _.compact(categoryIDs);
    },
});

publicWidget.registry.s_d_category_mega_menu_1 = DroggolRootWidget.extend({
    selector: '.dr_category_mega_menu, .s_d_category_mega_menu_1',

    drClearAttributes: (DroggolRootWidget.prototype.drClearAttributes || []).concat(['data-mega-menu-category-params']),
    controllerRoute: '/droggol_theme_common/get_mega_menu_categories',
    xmlDependencies: (DroggolRootWidget.prototype.xmlDependencies || [])
    .concat(['/droggol_theme_common/static/src/xml/we_sale_snippets/s_dynamic_mega_menu.xml']),

    start: function () {
        var self = this;
        this.bodyTemplate = this.$target.attr('data-ds-id');
        var categoryParams = this.$target.attr('data-mega-menu-category-params');
        var categoryInfo = categoryParams ? JSON.parse(categoryParams) : false;
        this.categoryParams = categoryInfo.categories;
        this.categoriesTofetch = [];
        _.each(this.categoryParams, function (category) {
            self.categoriesTofetch.push(category.id);
            _.each(category.child, function (c) {
                self.categoriesTofetch.push(c);
            });
        });
        return this._super.apply(this, arguments);
    },
    _getOptions: function () {
        return {
            categoryIDs: this.categoriesTofetch
        };
    },
    _processData: function (data) {
        var result = [];
        _.each(this.categoryParams, function (category) {
            var childCategories = [];
            _.each(category.child, function (child) {
                childCategories.push(_.findWhere(data, {id: child}));
            });
            result.push({
                parentCategory: _.findWhere(data, {id: category.id}),
                childCategories: _.compact(childCategories),
            });
        });
        return result;
    },
});
});
