odoo.define('droggol_theme_common.s_countdown_editor', function (require) {
'use strict';

var Dialog = require('web_editor.widget').Dialog;
var core = require('web.core');
var time = require('web.time');
var sOptions = require('web_editor.snippets.options');

var _t = core._t;

var CountdownDialog = Dialog.extend({
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/s_countdown.xml']
    ),
    template: 'droggol_theme_common.s_countdown_dialog',

    /**
     * @constructor
     */
    init: function (parent, data, options) {
        this._super(parent, _.extend({
            title: _t("Set a Due Date"),
            size: 'medium',
            buttons: [
                {text: _t("Save"), classes: 'btn-primary', click: this.save},
                {text: _t("Discard"), close: true},
            ],
        }, options || {}));

        this.data = data || {};
    },
    start: function () {
        var datePickerOptions = {
            minDate: moment({y: 1900}),
            maxDate: moment().add(200, 'y'),
            calendarWeeks: true,
            icons: {
                close: 'fa fa-check primary',
                today: 'far fa-calendar-check',
            },
            locale: moment.locale(),
            format: time.getLangDatetimeFormat(),
            sideBySide: true,
            buttons: {
                showClose: true,
                showToday: true,
            },
            widgetParent: 'body',
        };
        if (this.data.dueDate) {
            datePickerOptions.defaultDate = time.str_to_datetime(this.data.dueDate);
        } else {
            datePickerOptions.defaultDate = moment().add(1, 'days');
        }
        this.$('#due_date').datetimepicker(datePickerOptions);
        return this._super.apply(this, arguments);
    },
    save: function () {
        var $time = this.$('.dr-due-date');
        var time = $time.val();
        if (time !== '') {
            time = this._parse_date(time);
            if (time) {
                $time.val(time);
                $time.removeClass('is-invalid');
                return this._super.apply(this, arguments);
            }
        }
        $time.addClass('is-invalid');
    },
    _parse_date: function (value) {
        var datetime = moment(value, time.getLangDatetimeFormat(), true);
        if (datetime.isValid()) {
            return time.datetime_to_str(datetime.toDate());
        } else {
            return false;
        }
    },
});

sOptions.registry.s_countdown = sOptions.Class.extend({
    onBuilt: function () {
        this._super.apply(this, arguments);
        this.dueDate('click', null, null);
    },
    dueDate: function (previewMode, value, $opt) {
        var self = this;
        var dueDate = this.$target.attr('data-due-date');

        var countdownDialog = new CountdownDialog(this, {
            dueDate: dueDate,
        }).open();
        countdownDialog.on('save', this, function () {
            self.$target.attr('data-due-date', countdownDialog.$('.dr-due-date').val());
            self._refreshPublicWidgets();
        });
        countdownDialog.on('cancel', this, function () {
            if (!self.$target.attr('data-due-date')) {
                self.$target.remove();
                self.trigger_up('cover_update');
            }
        });
    },
    cleanForSave: function () {
        this.$el.find('.end_msg_container').addClass('css_non_editable_mode_hidden');
    }
});

});
