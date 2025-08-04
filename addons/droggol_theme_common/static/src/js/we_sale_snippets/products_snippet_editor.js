odoo.define('droggol_theme_common.product_image.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var options = require('web_editor.snippets.options');
var website_options = require('website.editor.snippets.options');
var SnippetConfigurator = require('droggol_theme_common.dialog.snippet_configurator_dialog');
var SnippetRegistry = require('droggol_theme_common.snippet_registry');
var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');
var DroggolGradientDialog = require('droggol_theme_common.gradiant_dialog');
var Select2Dialog = require('droggol_theme_common.product_selector');

var Mixins = require('droggol_theme_common.mixins');
var DroggolUtils = Mixins.DroggolUtils;

var _t = core._t;

options.registry.droggol_category_mega_menu_snippet = options.Class.extend(DroggolUtils, {
    // TO-DO no need to load all the template from this file must be changed in V14
    xmlDependencies: ['/droggol_theme_common/static/src/xml/widgets/category_widget.xml'],
    /**
     * @see this.selectClass for parameters
     */
    setCategory: function (previewMode, value, $opt) {
        var self = this;
        var categoryParams = this.$target.attr('data-categories');
        var categoryIDs = categoryParams ? JSON.parse(categoryParams) : false;
        this.categoryIDs = categoryIDs;
        if (this.categoryIDs.length) {
            this._fetchCategories(this.categoryIDs).then(categories => {
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
                self._openDialog({records: fetchedCategories, recordsIDs: categoryIDs});
            });
        }
        this._fetchCategories(categoryIDs).then(function (categories) {
        });
    },
    _fetchCategories: function (categoryIDs) {
        return this._rpc({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['id', 'name', 'display_name'],
            domain: this._getDomainWithWebsite([['id', 'in', categoryIDs]]),
        });
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._super();
        this._openDialog();
    },
    _openDialog: function (recordsInfo) {
        var self = this;
        recordsInfo = recordsInfo || {};
        this.CategoryDialog = new Select2Dialog(this, {
            multiSelect: true,
            records: recordsInfo.records || [],
            recordsIDs: recordsInfo.recordsIDs || [],
            routePath: '/product_snippet/get_category_by_name',
            fieldLabel: _t("Select Category"),
            dropdownTemplate: 'category_select2_dropdown',
            select2Limit: 12,
        });
        this.CategoryDialog.on('d_product_pick', this, function (ev) {
            var categories = ev.data.result;
            self.$target.attr('data-categories', JSON.stringify(categories));
            self._refreshPublicWidgets();
        });
        this.CategoryDialog.open();
    },
});
options.registry.dr_brand_snippet_option = options.Class.extend({
    brandCount: function (previewMode, value, $opt) {
        this.$target.attr('data-brand-limit', parseInt(value));
        this._refreshPublicWidgets();
    },
    selectClass: function (previewMode, value, $li) {
        this._super(previewMode, value, $li);
        if (previewMode === true) {
            this._refreshPublicWidgets();
        }
    },
    /**
     * @override
     */
    _setActive: function () {
        this._super(...arguments);
        var brandsCount = this.$target.attr('data-brand-limit');
        var numOfBrands = brandsCount ? JSON.parse(brandsCount) : 12;
        this.$el.find('[data-brand-count]').removeClass('active');
        this.$el.find('[data-brand-count=' + numOfBrands + ']').addClass('active');
    },
});
options.registry.droggol_gradient_option = options.Class.extend({
    /**
     * @override
     */
    setGradient: function (previewMode, value, $opt) {
        this._openDialog();
    },
    /**
     * @private
     */
    _openDialog: function () {
        var self = this;
        var value = this.$target.css('background-image');
        var match = value.match(/url\(["']?(.+?)["']?\)/);
        var image = match ? match[1] : '';
        this.DroggolGradientDialog = new DroggolGradientDialog(this, {
            image: image,
            value: value
        }).open();
        this.DroggolGradientDialog.on('gradiant_pick', this, function (ev) {
            self.$target.css('background-image', ev.data.style || value);
        });
    },
    /**
    * @private
    */
    _toggleOption: function () {
        this.$el.toggleClass('d-none', this.$target.css('background-image') === 'none');
    },
});

options.registry.droggol_product_snippet = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    onBuilt: function () {
        this._super();
        if (this.$target.hasClass('droggol_product_snippet')) {
            this.$target.attr('data-empty-message', _t('No products are selected.'));
            this.$target.attr('data-sub-message', _t('Please select products from snippet option.'));
        }
        this._openDialog();
    },
    /**
     * @see this.selectClass for parameters
     */
    setGrid: function (previewMode, value, $opt) {
        this._openDialog();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getConfiguratorParams: function () {
        this.usedAttrs = [];
        var self = this;
        var snippet = this.$target.attr('data-ds-id');
        var params = {};
        var snippetConfig = SnippetRegistry.get(snippet);
        var defaultValue = snippetConfig.defaultValue;
        _.each(snippetConfig.widgets, function (widget) {
            var attr = DialogWidgetRegistry.get(widget).prototype.d_attr;
            self.usedAttrs.push(attr);
            var attrValue = self.$target.attr(attr);
            var widgetVal = attrValue ? JSON.parse(attrValue) : false;
            if (defaultValue) {
                widgetVal = widgetVal || {};
                _.extend(widgetVal, defaultValue);
            }
            params[widget] = widgetVal;
        });
        return params;
    },
    /**
     * @private
     */
    _setConfiguratorParams: function (widgets) {
        var self = this;
        _.each(widgets, function (widget) {
            self.$target.attr(widget.d_attr, JSON.stringify(widget.value));
        });
    },
    /**
     * @private
     */
    _openDialog: function () {
        this.SnippetConfigurator = new SnippetConfigurator(this, {
            widgets: this._getConfiguratorParams()
        });
        this.SnippetConfigurator.on('d_final_pick', this, function (ev) {
            this._setConfiguratorParams(ev.data);
            this._refreshPublicWidgets();
        });
        this.SnippetConfigurator.on('cancel', this, function () {
            var self = this;
            var hasAttr = false;
            _.each(this.usedAttrs, function (attr) {
                if (self.$target[0].hasAttribute(attr)) {
                    hasAttr = true;
                }
            });
            if (!hasAttr) {
                // remove snippet on Discard
                this.$target.remove();
            }
        });
        this.SnippetConfigurator.open();
    },
});

options.registry.background_position.include({
    backgroundPosition: function (previewMode, value, $opt) {
        var self = this;
        this._super(...arguments);
        this.modal.opened().then(function () {
            // Make sure that image is append to dialog
            setTimeout(function () {
                var $img = self.modal.$el.find('.img.img-fluid');
                var bgImg = self.$target.css('background-image');
                if (bgImg.includes('linear-gradient')) {
                    var match = bgImg.match(/url\(["']?(.+?)["']?\)/);
                    var image = match ? match[1] : '';
                    $img.attr('src', image);
                }
            }, 100);
        });
    },
});

options.registry.carousel.include({
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);

        // Enable gradient support for carousel
        this.$target.on('slid.bs.carousel', function () {
            self.trigger_up('option_update', {
                optionName: 'droggol_gradient_option',
                name: 'target',
                data: self.$target.find('.carousel-item.active'),
            });
        });

        return def;
    }
});


options.registry.parallax.include({

    onFocus: function () {

        this.trigger_up('option_update', {
            optionName: 'droggol_gradient_option',
            name: 'target',
            data: this.$target.find('> .s_parallax_bg'),
        });
        return this._super.apply(this, arguments);

    },

});

options.registry.background.include({
    background: function (previewMode, value, $opt) {
        this._super(...arguments);
        // on color button leave reset original image with gradient
        if (previewMode === 'reset' && this.__dBackgroundCss && this.__dBackgroundCss.includes('linear-gradient')) {
            this.$target.css('background-image', this.__dBackgroundCss);
        }
    },
    _onBackgroundColorUpdate: function (ev, previewMode) {
        if (previewMode === true) {
            this.__dBackgroundCss = this.$target.css('background-image');
        }
        if (previewMode === false) {
            this.__dBackgroundCss = undefined;
        }
        return this._super(...arguments);
    },
    _getSrcFromCssValue: function (value) {
        if (value === undefined) {
            value = this.$target.css('background-image');
        }
        var match = value.match(/url\(["']?(.+?)["']?\)/);
        var imageSrc = match ? match[1] : 'none';
        return imageSrc;
    },
});
});
