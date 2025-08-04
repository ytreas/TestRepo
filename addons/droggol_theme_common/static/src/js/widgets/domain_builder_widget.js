odoo.define('droggol_theme_common.domain_builder', function (require) {

var core = require('web.core');
var Widget = require('web.Widget');
var utils = require('web.utils');
var Dialog = require('web_editor.widget').Dialog;
var DroggolUtils = require('droggol_theme_common.mixins').DroggolUtils;

var _t = core._t;
var qweb = core.qweb;


var modelDataCache = {
    cache: {},
    cacheDefs: {},
};
// [TO-DO]
// - maintain state proparly (even if i remove rule getDomain returns previous result)
// - Operator are not available when we initialize widget (it works fine after once field is changed)
var DomainBuilder = Widget.extend(DroggolUtils, {
    template: 'drg_domain_builder',
    xmlDependencies: [
        "/droggol_theme_common/static/src/xml/widgets/domain_builder_widget.xml"
    ],
    events: {
        'click .drg_add_rule': 'onClickAddRule',
        'click .db_condition': 'onClickCondition',
        'click .db_view_products': 'onClickViewProducts',
        'change #d_domain_limit_input': '_onChangeLimit',
    },
    custom_events: _.extend({}, Widget.prototype.custom_events || {}, {
        'remove_rule': 'onRemoveRule',
        'get_records': 'onGetRecords',
    }),
    init: function (parent, value) {
        var self = this;
        this.rawValue = this._processValue(value);
        this.domain = this.rawValue.domain || [];
        this.limit = this.rawValue.limit || 5;
        this.sortBy = 'price_desc';
        var allSortby = this._getOrderBy();
        // Fuck this hack coz i'm not gonna fix it today bcoz today is release date 1 june 2020 :)
        // Refactore logic in V14.
        _.each(allSortby, function (val, key) {
            if (val === self.rawValue.sortBy) {
                self.sortBy = key;
            }
        });
        // ==========================
        this.sortByVals = this._getSortByvals();
        this.ruleWidgets = [];
        this.recordCatch = {};
        this._super.apply(this, arguments);
    },
    start: function () {
        this._initDomainNodes();
        return this._super.apply(this, arguments);
    },
    _processValue: function (value) {
        if (_.isString(value)) {
            return JSON.parse(value);
        }
        if (_.isObject(value)) {
            return value;
        }
        return [];
    },
    getDomain: function () {
        var condition = this.$('.db_condition_btn').data('condition');
        var symbol = condition == 'all' ? '&' : '|';
        var domain = _.range(this.ruleWidgets.length - 1).map(function () { return symbol; });
        _.each(this.ruleWidgets, function (domainRow) {
            var domainNode = domainRow.getValue();
            if (domainNode[0] === '&' ) { // rare case between
                domain.push(domainNode[0]);
                domain.push(domainNode[1]);
                domain.push(domainNode[2]);
            } else {
                domain.push(domainNode);
            }
        });
        return {
            domain: domain,
            limit: parseInt(this.$('#d_domain_limit_input').val(), 10),
            sortBy: this._getParsedSortBy(this.$('#d_domain_sort_by_input').val())
        };
    },
    _initDomainNodes: function (ev) {
        var self = this;
        if (this.domain.length === 0) {
            return;
        }
        if (this.domain[0] === '|') {
            this.$('.db_condition_btn').text(_('Any'));
            this.$('.db_condition_btn').data('condition', 'any');
        } else {
            this.$('.db_condition_btn').text(_('All'));
            this.$('.db_condition_btn').data('condition', 'all');
        }
        function isOperator(val) {
            return val === "|" || val === "&";
        }
        var lastNode = false;
        var skipNextNode = false;
        _.each(this.domain, function (node, index) {
            if (isOperator(node) || skipNextNode) {
                lastNode = node;
                skipNextNode = false;
                // pass
                return;
            } else if (lastNode === '&' && node[0] === 'list_price' && (node[1] === '>' || node[1] === '<')) { // Between hack can be fixed with custom parser
                if (self.domain.length - 1 !== index) {
                    var nextNode = self.domain[index + 1];
                    var reverseOperator = node[1] === '>' ? '<' : '>';
                    if (nextNode[0] === 'list_price' && nextNode[1] === reverseOperator) {
                        skipNextNode = true;
                        var val = ['list_price', 'between', [node[2], nextNode[2]]];
                        lastNode = node;
                        self.onClickAddRule(false, val);
                        return;
                    }
                }
            }
            lastNode = node;
            self.onClickAddRule(false, node);
            return;
        });
    },
    onClickAddRule: function (ev, value) {
        if (ev) {
            ev.preventDefault();
        }
        var ruleId = _.uniqueId('rule_');
        var rule = new DomainBuilderRow(this, value, ruleId);
        this.ruleWidgets.push(rule);
        rule.appendTo(this.$('.drg_rule_container'));
    },
    onClickCondition: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        if ($link.data('condition') === 'all') {
            this.$('.db_condition_btn').text(_('All'));
            this.$('.db_condition_btn').data('condition', 'all');
        } else {
            this.$('.db_condition_btn').text(_('Any'));
            this.$('.db_condition_btn').data('condition', 'any');
        }
        this.getDomain();
    },
    onClickViewProducts: function () {
        var self = this;
        var domainInfo = this.getDomain();
        domainInfo['fields'] = ['name', 'id'];
        domainInfo['order'] = domainInfo['sortBy'];
        return this._rpc({
            route: '/droggol_theme_common/get_products_data',
            params: domainInfo,
        }).then(function (res) {
            var d = new Dialog(self, {
                title: _t('Selected Products'),
                // size: 'medium',
                buttons: [
                    { text: _t('Ok'), classes: 'btn-primary', close: true }
                ],
                $content: qweb.render('drg_domain_builder_products', res),
            });
            d.open();
            d._opened.then(function () {
                d.$modal.removeClass('o_technical_modal');
                d.$modal.addClass('droggol_technical_modal');
            });
        });
    },
    _onChangeLimit: function (ev) {
        var val = $(ev.currentTarget).val();
        this.$(ev.currentTarget).val(utils.confine(val.replace(/\D/g, ''), 1, 20));
    },
    onRemoveRule: function (ev) {
        var ruleId = ev.data.ruleId;
        this.ruleWidgets = _.filter(this.ruleWidgets, function (w) {
            if (w.ruleId === ruleId) {
                w.destroy();
                return false;
            }
            return true;
        });
    },
    onGetRecords: function (ev) {
        var model = ev.data.model;
        var callback = ev.data.callback;
        var FieldInfo = ev.data.FieldInfo;

        var def = modelDataCache.cacheDefs[model];
        if (!def) {
            def = modelDataCache.cacheDefs[model] = this._rpc({
                model: model,
                method: 'search_read',
                fields: ['id', 'display_name'],
                domain: FieldInfo.is_multi_website ? this._getDomainWithWebsite([]) : [],
            }).then(function (result) {
                modelDataCache.cache[model] = result;
            });
        }
        def.then(function () {
            callback(modelDataCache.cache[model]);
        });
    },
    /**
     * @private
     * @returns {Array}
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
    _getOrderBy: function () {
        return {
            price_asc: 'list_price asc',
            price_desc: 'list_price desc',
            name_asc: 'name asc',
            name_desc: 'name desc',
            newest_to_oldest: 'create_date desc',
        };
    },
    _getParsedSortBy: function (val) {
        var order = this._getOrderBy();
        return order[val];
    },
});

var DomainBuilderRow = Widget.extend({
    template: 'drg_domain_builder_row',
    events: {
        'click .drg_remove_rule': 'onRemoveRule',
        'change .db_input_field': 'onFieldChange',
        'change .db_input_operator': 'onOperatorChange',
        'click .pill_remove': 'onRemovePill'
    },
    init: function (parent, value, ruleId) {
        this.ruleId = ruleId;
        this.fields = this.getFieldList();
        this.value = value || [];
        this._super.apply(this, arguments);
    },
    start: function () {
        this.init = true;
        if (this.value.length) {  // INIT FIELD
            this.$('select.db_input_field').val(this.value[0]);
        }
        if (this.value.length) { // INIT OPERATOR
            this.replaceOperator();
            this.$('select.db_input_operator').val(this.value[1]);
        }
        this.onFieldChange(false, !!this.value.length);
        if (this.value.length) { // INIT VALUE
            if (this.value[1] === 'in' || this.value[1] === 'not in' || this.value[1] === 'child_of') {
                this.initTagsIds = this.value[2]; // Loaded from initAutoComplete due to deferred data.
            } else if (this.value[1] === 'between') {
                this.$('.db_row_min').val(this.value[2][0]);
                this.$('.db_row_max').val(this.value[2][1]);
            } else if (this.value[2]) {
                this.$('.db_input_value').val(this.value[2]);
            }
        }

        this.init = false;
        return this._super.apply(this, arguments);
    },
    getFieldList: function () {
        return [
            { 'type': 'text', 'name': 'name', 'label': _('Product Name') },
            { 'type': 'many2many', 'name': 'public_categ_ids', 'label': _('Product Category'), 'relationModel': 'product.public.category', 'is_multi_website': true },
            { 'type': 'many2one', 'name': 'dr_brand_id', 'label': _('Product Brand'), 'relationModel': 'dr.product.brand', 'is_multi_website': true },
            { 'type': 'many2one', 'name': 'dr_label_id', 'label': _('Product Label'), 'relationModel': 'dr.product.label' },
            { 'type': 'integer', 'name': 'list_price', 'label': _('Price') },
        ];
    },
    getOperatorInfo: function () {
        return {
            'text': {
                'ilike': "contains",
                'not ilike': "doesn't contain",
                '=': "is equal to",
                '!=': "is not equal to",
                'set': 'is set',
                'not set': 'is not set'
            },
            'many2many': {
                'in': "in",
                'not in': "not in",
                'child_of': "in child category of",
            },
            'many2one': {
                'in': "in",
                'not in': "not in",
                'set': 'is set',
                'not set': 'is not set'
            },
            'integer': {
                '=': "equals",
                '!=': "not in",
                '>': 'greater than',
                '<': 'less then',
                'between': 'is between'
            }
        };
    },
    getSelectedFieldInfo: function () {
        var fieldList = this.getFieldList();
        var fieldName = this.$('select.db_input_field').val();
        return _.findWhere(fieldList, { 'name': fieldName});
    },
    getOperatorValue: function () {
        return this.$('select.db_input_operator').val();
    },
    getOperatorList: function () {
        var selectedFieldInfo = this.getSelectedFieldInfo();
        var operatorInfo = this.getOperatorInfo();
        return operatorInfo[selectedFieldInfo.type];
    },
    initAutoComplete: function (model, records) {
        var self = this;
        var availableTags = _.map(records, function (record) {
            return {value: record.id.toString(), label: record.display_name};
        });
        this.$('.db_input_value').autocomplete({
            source: availableTags,
            select: this.onAutoCompleteChange.bind(this),
            disabled: false
        });
        if (this.initTagsIds) {
            _.each(this.initTagsIds, function (tagId) {
                var recordFound = _.findWhere(availableTags, { 'value': tagId.toString() });
                if (recordFound) {
                    self.onAutoCompleteChange(false, {'item': recordFound});
                }
            });
            this.initTagsIds = false;
        }
    },
    getValue: function () {
        var fieldName = this.$('.db_input_field').val();
        var operator = this.$('.db_input_operator').val();
        var selectedFieldInfo = this.getSelectedFieldInfo();
        var value = 0;
        if (operator === 'in' || operator === 'not in' || operator === 'child_of') {
            value = [];
            _.each(this.$('.pill_container .badge'), function (badge) {
                value.push(parseInt(badge.id));
            });
        } else {
            value = this.$('.db_input_value').val();
        }
        if (operator !== 'between' && selectedFieldInfo.type === "integer") {
            return [fieldName, operator, parseInt(value)];
        } else if (selectedFieldInfo.type !== "integer") {
            return [fieldName, operator, value];
        } else {
            var min = this.$('.db_row_min').val();
            var max = this.$('.db_row_max').val();
            min = min && parseInt(min) || 0;
            max = max && parseInt(max) || 0;
            return ['&', [fieldName, '>', min], [fieldName, '<', max]];
        }
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onRemoveRule: function (ev) {
        ev.preventDefault();
        this.trigger_up('remove_rule', {
            ruleId: this.ruleId
        });
    },
    onFieldChange: function (ev, noReplace) {
        if (!noReplace) {
            this.replaceOperator();
        }
        this.$('select.db_input_operator').change();
        this.$('.db_input_value').val('');
        this.$('.pill_container .badge').remove();
    },
    replaceOperator: function () {
        var operatorInfo = this.getOperatorList();
        var $operators = qweb.render('drg_domain_builder_row_operator', {operators: operatorInfo});
        this.$('.db_input_operator').replaceWith($operators);
    },
    onAutoCompleteChange: function (ev, ui) {
        var self = this;
        if (ui.item && ui.item.label) {
            var $pill = qweb.render('drg_domain_builder_row_pill', ui.item);
            this.$('.db_input_value').before($pill);
            setTimeout(function () {
                self.$('.db_input_value').val('');
            }, 10);
        }
    },
    onRemovePill: function (ev) {
        $(ev.currentTarget).parent().remove();
    },
    onOperatorChange: function (ev) {
        var self = this;
        var selectedOperator = this.getOperatorValue();
        var selectedFieldInfo = this.getSelectedFieldInfo();
        var model = selectedFieldInfo.relationModel;
        this.$(".db_input_value").autocomplete({
            disabled: true
        });
        // Special cases
        this.$(".db_value_col").removeClass('d-none');
        this.$(".db_value_range_col").addClass('d-none');
        this.$(".db_operator_col").removeClass('col-sm-8').addClass('col-sm-3');
        if (selectedOperator === 'set' || selectedOperator === 'not set') {
            this.$(".db_value_col").addClass('d-none');
            this.$(".db_operator_col").addClass('col-sm-8').removeClass('col-sm-3');
        }
        if (selectedOperator === 'between') {
            this.$(".db_value_col").addClass('d-none');
            this.$(".db_value_range_col").removeClass('d-none');
        }
        if (selectedOperator === 'in' || selectedOperator === 'not in' || selectedOperator === 'child_of') {
            this.trigger_up('get_records', {
                model: model,
                FieldInfo: selectedFieldInfo,
                callback: this.initAutoComplete.bind(this, model)
            });
        } else {
            this.$('.pill_container .badge').remove();
        }
    }
});

return {
    DomainBuilder: DomainBuilder,
    DomainBuilderRow: DomainBuilderRow,
};

});
