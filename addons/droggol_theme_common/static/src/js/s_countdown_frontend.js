odoo.define('droggol_theme_common.s_countdown_frontend', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var time = require('web.time');

publicWidget.registry.s_countdown = publicWidget.Widget.extend({
    selector: '.s_countdown',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        var eventTime = moment(time.str_to_datetime(this.$el.attr('data-due-date')));
        var currentTime = moment();
        var diffTime = eventTime - currentTime;
        var duration = moment.duration(diffTime);
        var interval = 1000;

        this.$el.find('.end_msg_container').addClass('css_non_editable_mode_hidden');
        if (diffTime > 0) {
            this.countDownTimer = setInterval(function () {
                duration = moment.duration(duration.asMilliseconds() - interval, 'milliseconds');
                if (duration.asMilliseconds() < 0) {
                    self._endCountdown();
                }
                var d = parseInt(moment.duration(duration).asDays());
                var h = moment.duration(duration).hours();
                var m = moment.duration(duration).minutes();
                var s = moment.duration(duration).seconds();

                d = $.trim(d).length === 1 ? '0' + d : d;
                h = $.trim(h).length === 1 ? '0' + h : h;
                m = $.trim(m).length === 1 ? '0' + m : m;
                s = $.trim(s).length === 1 ? '0' + s : s;

                self.$('.countdown_days').text(d);
                self.$('.countdown_hours').text(h);
                self.$('.countdown_minutes').text(m);
                self.$('.countdown_seconds').text(s);
            }, interval);
        } else {
            this._endCountdown();
        }
        return def;
    },
    _endCountdown: function () {
        if (this.$target.parents('.s_coming_soon').length) {
            if (!this.editableMode) {
                this.$target.parents('.s_coming_soon').addClass('d-none');
                this.$target.addClass('d_count_down_over');
            }
            $('body').css('overflow', 'auto');
        }
        this.$('.countdown_days').text('00');
        this.$('.countdown_hours').text('00');
        this.$('.countdown_minutes').text('00');
        this.$('.countdown_seconds').text('00');
        this.$el.find('.end_msg_container').removeClass('css_non_editable_mode_hidden');
        if (this.countDownTimer) {
            clearInterval(this.countDownTimer);
        }
    },
    destroy: function () {
        if (this.countDownTimer) {
            clearInterval(this.countDownTimer);
        }
        this._super.apply(this, arguments);
    },
});

});
