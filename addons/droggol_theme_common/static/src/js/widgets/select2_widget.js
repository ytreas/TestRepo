odoo.define('droggol_theme_common.widgets.select2_widget', function (require) {
'use strict';

var core = require('web.core');
var AbstractWidget = require('droggol_theme_common.widgets.abstract_widget');

var qweb = core.qweb;

return AbstractWidget.extend({
    template: 'select2_widget',

    xmlDependencies: AbstractWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/widgets/select2_widget.xml']
    ),
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('.d-select2-input');
        this._initSelect2();
        this._initSortable();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    getValue: function (options) {
        var result = false;
        if (this.$input.val()) {
            if (this.multiSelect) {
                result = _.map(this.$input.val().split(","), function (id) {
                    return parseInt(id, 10);
                });
            } else {
                result = parseInt(this.$input.val());
            }
        }
        return result;
    },
    /**
     * @override
     * pass model insted of records for next version.
     */
    setValue: function (options) {
        this.fieldLabel = options.fieldLabel || '';
        this.multiSelect = options.multiSelect || false;
        this.records = options.records || false;
        this.recordsIDs = options.recordsIDs || false;
        this.routePath = options.routePath;
        this.routeParams = options.routeParams || {};
        this.select2Limit = options.select2Limit || 0;
        this.dropdownTemplate = options.dropdownTemplate;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize select2
     * @private
     */
    _initSortable: function () {
        var self = this;
        this.$input.select2('container').find('ul.select2-choices').sortable({
            containment: 'parent',
            start: function () {
                self.$input.select2('onSortStart');
            },
            update: function () {
                self.$input.select2('onSortEnd');
            }
        });
    },
    /**
     * Initialize select2
     * @private
     */
    _initSelect2: function () {
        var self = this;
        this.$input.select2({
            width: "100%",
            tokenSeparators: [",", " ", "_"],
            maximumInputLength: 35,
            minimumInputLength: 1,
            multiple: this.multiSelect,
            maximumSelectionSize: this.select2Limit,
            // Default tags value
            initSelection: function (element, callback) {
                var data = _.map(self.recordsIDs, function (recordsID) {
                    var rec = _.findWhere(self.records, {id: recordsID});
                    return {'id': rec.id, 'text': rec.name};
                });
                element.val('');
                callback(data);
            },
            dropdownCssClass: 'd-select2-dropdown',
            ajax: {
                url: this.routePath,
                dataType: 'json',
                quietMillis: 500,
                data: function (term) {
                    return _.extend({
                        term: term,
                    }, self.routeParams);
                },
                results: function (data) {
                    return {
                        results: self._processData(data)
                    };
                },
            },
            formatResult: function (data) {
                return qweb.render(self.dropdownTemplate, {
                    data: data
                });
            },
        });
    },
    /**
     * @private
     */
    _processData: function (data) {
        _.each(data, function (res) {
            // select2 tag val
            res['text'] = res.name || res.display_name;
        });
        return data;
    },
});

});
