odoo.define('droggol_theme_common.widgets.mega_menu_category_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var Select2Dialog = require('droggol_theme_common.product_selector');
var Mixins = require('droggol_theme_common.mixins');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');

var SortableMixins = Mixins.SortableMixins;
var DroggolUtils = Mixins.DroggolUtils;

var qweb = core.qweb;
var _t = core._t;

var MegaMenuCategoryWidget = AbstractWidget.extend(SortableMixins, DroggolUtils, {

    template: 'droggol_theme_common.mega_menu_category_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/mega_menu_category_widget.xml']
    ),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'click .d_add_category': '_onAddCategoryClick',
        'click .dr_add_child_category': '_onAddChildCategoryClick',
        'click .d_remove_item': '_onRemoveCategoryClick',
    }),

    d_tab_info: {
        icon: 'fa fa-list',
        label: _t('Category'),
        name: 'MegaMenuCategoryWidget',
    },
    d_attr: 'data-mega-menu-category-params',
    /**
     * @constructor
     * @param {Object} options: useful parameters such as categoryIDs
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.categories = options.categories || [];
        var parentCategoryIDs = _.map(this.categories, function (data) {
            return data.id;
        });
        this.parentCategoryIDs = _.compact(parentCategoryIDs);
    },
    /**
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        var self = this;
        if (this.parentCategoryIDs.length) {
            defs.push(this._fetchCategories(this.parentCategoryIDs).then(categoriesFromDB => {
                var FetchedCategories = _.map(categoriesFromDB, function (category) {
                    return category.id;
                });
                var categories = [];
                var parentCategoryIDs = [];
                _.each(this.parentCategoryIDs, function (parentCategoryID) {
                    if (_.contains(FetchedCategories, parentCategoryID)) {
                        var category = _.findWhere(self.categories, {id: parentCategoryID});
                        _.extend(category, _.findWhere(categoriesFromDB, {id: parentCategoryID}));
                        categories.push(category);
                        parentCategoryIDs.push(parentCategoryID);
                    }
                });
                this.categories = categories;
                this.parentCategoryIDs = parentCategoryIDs;
            }));
        }
        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        this._makeListSortable();
        this._togglePlaceHolder();
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @returns {Array} categoryIDs
     */
    _getCategoryIDs: function () {
        return _.map(this.$('.d_category_item'), item => {
            return parseInt($(item).attr('data-category-id'), 10);
        });
    },
    /**
     * @override
     * @returns {Array} list of selected products
     */
    getValues: function () {
        var categories = _.map(this.$('.d_category_item'), function (category) {
            var $category = $(category);
            return {
                id: parseInt($category.attr('data-category-id'), 10),
                child: JSON.parse($category.attr('data-child'))
            };
        });
        return {
            d_attr: this.d_attr,
            value: {
                categories: _.compact(categories),
            }
        };
    },
    _togglePlaceHolder: function () {
        var items = this.$('.d_category_item').length;
        this.trigger_up('widget_value_changed', {val: items});
        this.$('.d-category-placeholder').toggleClass('d-none', !!items);
        this.$('.d_category_input_group').toggleClass('d-none', !items);
    },
    /**
     * @private
     * @returns {Array} categoryIDs
     */
    _fetchCategories: function (categoryIDs) {
        return this._rpc({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['id', 'name', 'display_name'],
            domain: this._getDomainWithWebsite([['id', 'in', categoryIDs]]),
        });
    },
    /**
     * @private
     */
    _refreshCategoryList: function () {
        var $categoryList = this.$('.d_sortable_block');
        $categoryList.empty();
        if (this.categories.length) {
            $categoryList.append(qweb.render('d_categories_list', {categories: this.categories}));
        }
        this._togglePlaceHolder();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddCategoryClick: function () {
        var self = this;
        this.CategoryDialog = new Select2Dialog(this, {
            multiSelect: true,
            records: this.categories,
            recordsIDs: this._getCategoryIDs(),
            routePath: '/product_snippet/get_category_by_name',
            fieldLabel: _t("Select Category"),
            dropdownTemplate: 'category_select2_dropdown',
        });
        this.CategoryDialog.on('d_product_pick', this, function (ev) {
            var categoriesToAdd = ev.data.result;
            if (categoriesToAdd) {
                var categoriesToFetch = _.difference(categoriesToAdd, self._getCategoryIDs());
                // already Fetch krelo data use karvo navi selected category ni info fetch kri che
                self._fetchCategories(categoriesToFetch).then(categories => {
                    _.each(categories, function (category) {
                        category['child'] = [];
                    });
                    var allCategories = _.union(categories, self.categories);
                    self.categories = _.map(categoriesToAdd, function (category) {
                        return _.findWhere(allCategories, {id: category});
                    });
                    self._refreshCategoryList();
                    self.parentCategoryIDs = self._getCategoryIDs();
                });
            } else {
                self.categories = [];
                self.parentCategoryIDs = [];
                this._refreshCategoryList();
            }
        });
        this.CategoryDialog.open();
    },
    _onAddChildCategoryClick: function (ev) {
        var $category = $(ev.currentTarget).closest('.d_category_item');
        var categoryID = parseInt($category.attr('data-category-id'), 10);
        var childCategories = JSON.parse($category.attr('data-child'));
        this._fetchCategories(childCategories).then(categories => {
            var CategoryDialog = new Select2Dialog(this, {
                multiSelect: true,
                records: categories,
                recordsIDs: _.map(categories, function (c) { return c.id }),
                routePath: '/product_snippet/get_category_by_name',
                fieldLabel: _t("Select Category"),
                dropdownTemplate: 'category_select2_dropdown',
                routeParams: {
                    category_id: parseInt($category.attr('data-category-id'), 10)
                }
            });
            CategoryDialog.on('d_product_pick', this, function (ev) {
                var selectedChildCategory = ev.data.result;
                var category = _.findWhere(this.categories, {id: categoryID});
                category.child = selectedChildCategory;
                this._refreshCategoryList();
            });
            CategoryDialog.open();
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveCategoryClick: function (ev) {
        var $category = $(ev.currentTarget).closest('.d_category_item');
        $category.remove();
        this.categories = _.without(this.categories, _.findWhere(this.categories, {id: parseInt($category.attr('data-category-id'), 10)}));
        this.categoryIDs = this._getCategoryIDs();
        this._togglePlaceHolder();
    },
});


DialogWidgetRegistry.add('MegaMenuCategoryWidget', MegaMenuCategoryWidget);

return MegaMenuCategoryWidget;
});
