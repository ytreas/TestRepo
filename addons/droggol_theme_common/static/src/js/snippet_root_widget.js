odoo.define('droggol_theme_common.root.widget', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var qweb = core.qweb;
var _t = core._t;

return publicWidget.Widget.extend({
    disabledInEditableMode: false,
    xmlDependencies: ['/droggol_theme_common/static/src/xml/snippet_root_widget.xml'],

    // RPC call karti vkhte potana controller no route controllerRoute parameter ma set karvo
    controllerRoute: false,
    // Product related je fields fetch karvana hoy database mathi te fields
    fieldstoFetch: false,
    // Je template snippet ma append karvanu hoy te template nu name
    bodyTemplate: false,
    // Je node par 'bodyTemplate' append karvanu hoy
    // every time aaj node par append thse template ane destroy ma remove pan aaj content thse
    bodySelector: false,
    // Je loader nu template display karvu hoy ae loader
    loaderTemplate: 'droggol_default_loader',
    // Je template display karvu hoy edit mode e.g alert 'Click here to Add Products'
    editorTemplate: false,
    // Loader display karvu 6e k nai te
    displayLoader: true,
    // Remove Attributs for public users
    drClearAttributes: [],

    // Je template display karvu hoy jyare database mathi koi data na made

    noDataTemplate: 'droggol_default_no_data_templ',

    noDataTemplateImg: '/droggol_theme_common/static/src/img/no_data.svg',

    noDataTemplateString: _t("No products found!"),

    noDataTemplateSubString: _t("Sorry, We couldn't find any products"),

    displayAllProductsBtn: true,

    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        var params = this._getParameters();
        if (!_.isEmpty(params)) {
            if (this.fieldstoFetch) {
                _.extend(params, {fields: this.fieldstoFetch});
            }
            defs.push(this._fetchData(params));
        } else {
            if (this.editableMode && this.editorTemplate) {
                this.$target.addClass('droggol_snippet');
                this._renderAndAppendQweb(this.editorTemplate, 'd_editor_tmpl_default');
            }
        }
        return Promise.all(defs);
    },
    /**
    * @override
    */
    destroy: function () {
        this._super.apply(this, arguments);
        this._modifyElementsBeforeRemove();
        this._getBodySelectorElement().empty();
    },

    //--------------------------------------------------------------------------
    // Khangi/Private
    //--------------------------------------------------------------------------


    /**
    * @private
    */
    _appendLoader: function () {
        if (this.displayLoader && this.loaderTemplate) {
            this._renderAndAppendQweb(this.loaderTemplate, 'd_loader_default');
        }
    },
    /**
     * @private
     */
    _appendNoDataTemplate: function () {
        if (this.noDataTemplate) {
            this._renderAndAppendQweb(this.noDataTemplate, 'd_no_data_tmpl_default');
        }
    },
    /**
     * @private
     */
    _cleanBeforeAppend: function () {
        // Remove elements
        this.$('.d_loader_default').remove();
        this.$('.d_no_data_tmpl_default').remove();
        this.$('.d_editor_tmpl_default').remove();
    },
    /**
     * @private
     */
    _cleanAttributes: function () {
        var self = this;
        if (_.has(odoo.session_info, "is_droggol_editor") && !odoo.session_info.is_droggol_editor) {
            _.each(this.drClearAttributes, function (attr) {
                self.$target.removeAttr(attr);
            });
        }
    },
    /**
     * @private
     */
    _getBodySelectorElement: function () {
        var selector = this.bodySelector;
        return selector ? this.$(selector) : this.$target;
    },
    /**
     * @private
     */
    _getDomain: function () {
        return false;
    },
    /**
     * @private
     */
    _getOptions: function () {
        return false;
    },
    /**
     * @private
     */
    _getLimit: function () {
        return false;
    },
    /**
     * @private
     */
    _getSortBy: function () {
        return false;
    },
    /**
     * @private
     */
    _getParameters: function () {
        var domain = this._getDomain();
        var params = {};
        if (domain) {
            params['domain'] = domain;
        }
        var limit = this._getLimit();
        if (limit) {
            params['limit'] = limit;
        }
        var order = this._getSortBy();
        if (order) {
            params['order'] = order;
        }
        var options = this._getOptions();
        if (options) {
            params['options'] = options;
        }
        return params;
    },
    /**
     * @private
     */
    _onSuccessResponse: function (response) {
        var hasData = this._responseHasData(response);
        if (hasData) {
            this._setDBData(response);
            var processedData = this._processData(response);
            this._renderContent(processedData);
        } else {
            this._appendNoDataTemplate();
        }
    },
    /**
     * @private
     */
    _fetchData: function (params) {
        this._appendLoader();
        return this._rpc({
            route: this.controllerRoute,
            params: params,
        }).then(response => {
            this._onSuccessResponse(response);
        });
    },
    /**
     * @private
     */
    _modifyElementsBeforeRemove: function () {},
    /**
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this.$('.d_body_tmpl_default').removeClass('d_body_tmpl_default');
        this._cleanAttributes();
    },
    /**
     * @private
     * in case database mathi avela data ne process karvani jarur pde to
     * ae vastu dhyan ma rakhvi k aa process thayelo data j template render thata jse
     */
    _processData: function (data) {
        return data;
    },
    /**
     * @private
     */
    _responseHasData: function (data) {
        return data;
    },
    /**
     * @private
     * Widget na 'this' ma value change/set karava mate.
     */
    _setDBData: function (data) {},
    /**
     * @private
     */
    _renderAndAppendQweb: function (template, className, data) {
        if (!template) {
            // for safety
            return;
        }
        var $template = $(qweb.render(template, {data: data, widget: this}));
        $template.addClass(className);
        // html() make sure template appends only once.
        this._getBodySelectorElement().html($template);
    },
    /**
     * @private
     */
    _renderContent: function (data) {
        this._cleanBeforeAppend();
        this._renderAndAppendQweb(this.bodyTemplate, 'd_body_tmpl_default', data);
        this._modifyElementsAfterAppend();
    },
});

});
