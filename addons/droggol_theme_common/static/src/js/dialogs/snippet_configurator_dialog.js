odoo.define('droggol_theme_common.dialog.snippet_configurator_dialog', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('web_editor.widget');

var DialogWidgetRegistry = require('droggol_theme_common.dialog_widgets_registry');

var WeDialog = weWidgets.Dialog;

var _t = core._t;

return WeDialog.extend({

    template: 'droggol_theme_common.dialog.snippet_configurator_dialog',

    xmlDependencies: WeDialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/dialogs/snippet_configurator_dialog.xml']
    ),
    custom_events: _.extend({}, WeDialog.prototype.custom_events, {
        widget_value_changed: '_onValueChanged',
    }),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: options.title || _t('Snippet Configurator'),
            size: options.size || 'extra-large',
            buttons: [
                {text: _t('Choose'), classes: 'd_final_pick_btn btn-primary', close: true, click: this._onFinalPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
            technical: false,
            dialogClass: 'd-snippet-config-dialog p-0'
        } || {}));
        this.tabs = [];
        // widget ni key widget and value ae initialize mate na parameters
        this.widgets = options.widgets;
        this._initializeWidgets();
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        this.$modal.addClass('droggol_technical_modal');
        this._appendWidgets();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _appendWidgets: function () {
        var self = this;
        _.each(this.widgets, function (val, key) {
            if (self[key]) {
                self[key].appendTo(self.$('#' + key)).then(function () {
                    self._initTips();
                });
            }
        });
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
     * @private
     */
    _initializeWidgets: function () {
        var self = this;
        _.each(this.widgets, function (val, key) {
            var widget = DialogWidgetRegistry.get(key);
            self[key] = new widget(self, val);
            self.tabs.push(self[key].d_tab_info);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFinalPick: function () {
        var self = this;
        var result = {};
        _.each(this.widgets, function (val, key) {
            if (self[key]) {
                result[key] = self[key].getValues();
            }
        });
        this.trigger_up('d_final_pick', result);
    },
    /**
     * @private
     */
    _onValueChanged: function (ev) {
        this.$footer.find('.d_final_pick_btn').prop('disabled', !ev.data.val);
    },
});

});
