odoo.define('droggol_theme_common.widgets.category_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');
var Select2Dialog = require('droggol_theme_common.product_selector');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');
var utils = require('web.utils');

var Mixins = require('droggol_theme_common.mixins');

var CategoryMixins = Mixins.CategoryMixins;
var SortableMixins = Mixins.SortableMixins;
var DroggolUtils = Mixins.DroggolUtils;

var qweb = core.qweb;
var _t = core._t;

var CategoryWidget = AbstractWidget.extend(DroggolUtils, CategoryMixins, SortableMixins, {

    template: 'droggol_theme_common.category_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/category_widget.xml']
    ),

    events: _.extend({}, AbstractWidget.prototype.events, {
        'click .d_add_category': '_onAddCategoryClick',
        'click .d_view_category_products': '_onViewCategoryProductsClick',
        'click .d_remove_item': '_onRemoveCategoryClick',
        'change #d_sort_by_select, #d_ppc_select, #d_include_child_categories': '_onChangeFilters',
        'change #d_ppc_select': '_onChangeLimit',
    }),

    d_tab_info: {
        icon: 'fa fa-list',
        label: _t('Category'),
        name: 'CategoryWidget',
    },
    d_attr: 'data-category-params',

    /**
     * @constructor
     * @param {Object} options: useful parameters such as categoryIDs
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.categoryIDs = options.categoryIDs || [];
        this.limit = options.limit || 5;
        this.select2Limit = options.select2Limit || 0;
        this.sortBy = options.sortBy || 'price_desc';
        this.sortByVals = this._getSortByvals();
        this.includesChild = options.includesChild || true;
    },
    /**
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];
        if (this.categoryIDs.length) {
            defs.push(this._fetchCategories(this.categoryIDs).then(categories => {
                var FetchedCategories = _.map(categories, function (category) {
                    return category.id;
                });
                var categoryIDs = [];
                var fetchedCategories = [];
                this.categories = _.each(this.categoryIDs, function (categoryID) {
                    if (_.contains(FetchedCategories, categoryID)) {
                        categoryIDs.push(categoryID);
                        fetchedCategories.push(_.findWhere(categories, {id: categoryID}));
                    }
                });
                this.categoryIDs = categoryIDs;
                this.categories = fetchedCategories;
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
     * @override
     * @returns {Array} list of selected products
     */
    getValues: function () {
        return {
            d_attr: this.d_attr,
            value: {
                categoryIDs: this._getCategoryIDs(),
                sortBy: this._getSortBy(),
                limit: this._getLimit(),
                includesChild: this._isIncludeChild(),
            }
        };
    },
    /**
     * @private
     * @returns {Array} categoryIDs
     */
    _appendProducts: function (categoryID, products) {
        var $productBlock = this.$('.d_products_list_block[data-category-id=' + categoryID + ']');
        $productBlock.append(qweb.render('d_products_by_category', {
            products: products
        }));
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
     * @returns {Integer} categoryID
     */
    _fetchProducts: function (categoryID) {
        this._fetchProductsByCategory(categoryID, this._isIncludeChild(), this._getParsedSortBy(this._getSortBy()), this._getLimit()).then(data => {
            var products = data.products;
            this.$('.d_view_category_products[data-category-id=' + categoryID + '] .d_warning_no_products').toggleClass('d-none', !!products.length);
            this._initTips();
            this._appendProducts(categoryID, products);
        });
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
     * @private
     * @returns {Array} categoryIDs
     */
    _getSortByvals: function () {
        return {
            price_asc: _t("Price: Low to High"),
            price_desc: _t("Price: High to Low"),
            name_asc: _t("Name: A to Z"),
            name_desc: _t("Name: Z to A"),
            newest_to_oldest: _t("Newly Arrived"),
        };
    },
    /**
     * @private
     */
    _getSortBy: function () {
        return this.$('#d_sort_by_select').val();
    },
    /**
     * @private
     */
    _getLimit: function () {
        return parseInt(this.$('#d_ppc_select').val(), 10);
    },
    /**
     * init tooltips
     *
     * @private
     */
    _initTips: function () {
        this.$('[data-toggle="tooltip"]').tooltip();
    },
    /**
     * init tooltips
     *
     * @private
     */
    _isIncludeChild: function () {
        return this.$('#d_include_child_categories').prop('checked');
    },
    /**
     * @private
     * @returns {Array} categoryIDs
     */
    _refreshCategoryList: function () {
        var $categoryList = this.$('.d_sortable_block');
        $categoryList.empty();
        if (this.categories.length) {
            $categoryList.append(qweb.render('d_categories_list', {categories: this.categories}));
        }
        this._togglePlaceHolder();
    },
    _togglePlaceHolder: function () {
        var items = this.$('.d_category_item').length;
        this.trigger_up('widget_value_changed', {val: items});
        this.$('.d-category-placeholder').toggleClass('d-none', !!items);
        this.$('.d_category_input_group').toggleClass('d-none', !items);
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
            select2Limit: this.select2Limit,
        });
        this.CategoryDialog.on('d_product_pick', this, function (ev) {
            var categoriesToAdd = ev.data.result;
            if (categoriesToAdd) {
                var categoriesToFetch = _.without(categoriesToAdd, self._getCategoryIDs());
                // already Fetch krelo data use karvo navi selected category ni info fetch kri che
                self._fetchCategories(categoriesToFetch).then(categories => {
                    var allCategories = _.union(categories, self.categories);
                    self.categories = _.map(categoriesToAdd, function (category) {
                        return _.findWhere(allCategories, {id: category});
                    });
                    self._refreshCategoryList();
                    self.categoryIDs = self._getCategoryIDs();
                });
            } else {
                self.categories = [];
                self.categoryIDs = [];
                this._refreshCategoryList();
            }
        });
        this.CategoryDialog.open();
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
    /**
     * @private
     */
    _onChangeFilters: function () {
        // toggle open/close
        this.$('.d_products_list_block').addClass('d-none').empty();
        this.$('.d_warning_no_products').addClass('d-none');
        this.$('.d_view_category_products').addClass('d_product_to_fetch');
    },
    _onChangeLimit: function (ev) {
        var val = $(ev.currentTarget).val();
        this.$(ev.currentTarget).val(utils.confine(val.replace(/\D/g, ''), 1, 20));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onViewCategoryProductsClick: function (ev) {
        var $target = $(ev.currentTarget);
        var categoryID = parseInt($target.attr('data-category-id'), 10);
        if ($target.hasClass('d_product_to_fetch')) {
            $target.removeClass('d_product_to_fetch');
            this.$('.d_products_list_block[data-category-id=' + categoryID + ']').removeClass('d-none');
            this._fetchProducts(categoryID);
        } else {
            this.$('.d_products_list_block[data-category-id=' + categoryID + ']').toggleClass('d-none');
        }
    },
});

DialogWidgetRegistry.add('CategoryWidget', CategoryWidget);

return CategoryWidget;

});
