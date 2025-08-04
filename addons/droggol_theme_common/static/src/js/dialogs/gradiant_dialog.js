odoo.define('droggol_theme_common.gradiant_dialog', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('wysiwyg.widgets');
var ColorpickerDialog = require('web.ColorpickerDialog');

var _t = core._t;
var QWeb = core.qweb;

// [TO-DO] set throttle on events

return weWidgets.Dialog.extend({
    xmlDependencies: weWidgets.Dialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/dialogs/gradiant_dialog.xml']
    ),
    template: 'droggol_theme_common.gradiant_dialog',

    events: _.extend({}, weWidgets.Dialog.prototype.events || {}, {
        'mousedown .drg-gradient-dot-visual': '_onMouseDown',
        'mousemove': '_onMouseMove',
        'mouseup': '_onMouseUp',
        'mousedown .drg-gradient-dot-delete': '_onDeleteDot',
        'mouseup .drg-gradient-dot-delete': '_onDeleteDotUp',
        'mousedown .drg-gradient-dot-edit': '_onEditDot',
        'input .gradiant-range-input': '_onDirectionChange',
        'change .drg-gradient-type': '_onTypeChange',
        'click .drg-inbuilt-gradient': '_onInbuiltGradientClick'
    }),
    /**
     * @override
     */
    init: function (parent, options) {
        options = options || {};
        this.image = options.image;
        this._parseValue(options.value);
        this._super(parent, _.extend({
            title: _t('Pick a gradient'),
            technical: false,
            dialogClass: 'drg-gradient-dialog',
            buttons: [
                {text: _t('Apply'), classes: 'btn-primary', close: true, click: this._onApplyPick.bind(this)},
                {text: _t('Discard'), close: true},
            ],
            size: 'extra-large',
        }, options));
        this.inbuiltGrediant = {
            gr_1: [{
                color: 'rgba(0, 210, 255, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(58, 123, 213, 0.8)',
                percentage: 100
            }],
            gr_2: [{
                color: 'rgba(242, 112, 156, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(255, 148, 114, 0.8)',
                percentage: 100
            }],
            gr_3: [{
                color: 'rgba(255, 148, 114, 0)',
                percentage: 0
            }, {
                color: 'rgba(0, 171, 205, 1)',
                percentage: 100
            }],
            gr_4: [{
                color: 'rgba(229, 93, 135, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(95, 195, 228, 0.9)',
                percentage: 100
            }],
            gr_5: [{
                color: 'rgba(48, 207, 208, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(51, 8, 103, 0.8)',
                percentage: 100
            }],
            gr_6: [{
                color: 'rgba(204, 149, 192, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(219, 212, 180, 0.8)',
                percentage: 50
            }, {
                color: 'rgba(122, 161, 210, 0.8)',
                percentage: 100
            }],
            gr_7: [{
                color: 'rgba(2, 170, 176, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(0, 205, 172, 0.8)',
                percentage: 100
            }],
            gr_8: [{
                color: 'rgba(173, 83, 137, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(60, 16, 83, 0.8)',
                percentage: 100
            }],
            gr_9: [{
                color: 'rgba(58, 28, 113, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(215, 109, 119, 0.8)',
                percentage: 50
            }, {
                color: 'rgba(255, 175, 123, 0.8)',
                percentage: 100
            }],
            gr_10: [{
                color: 'rgba(229, 93, 135, 0.8)',
                percentage: 50
            }, {
                color: 'rgba(95, 195, 228, 0.8)',
                percentage: 50
            }],
            gr_11: [{
                color: 'rgba(229, 93, 135, 0)',
                percentage: 40
            }, {
                color: 'rgba(255, 175, 123, 0.8)',
                percentage: 40
            }],
            gr_12: [{
                    color: 'rgba(255, 175, 123, 0.8)',
                    percentage: 20
                }, {
                    color: 'rgba(229, 93, 135, 0)',
                    percentage: 20
                }, {
                    color: 'rgba(229, 93, 135, 0)',
                    percentage: 80
                }, {
                    color: 'rgba(255, 175, 123, 0.8)',
                    percentage: 80
            }],
        };
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$modal.addClass('droggol_technical_modal');
        setTimeout(function () {
            self.$('.gradiant-range-input').val(self.gradientDirection);
            self.$('.drg-gradient-type').filter("[value='" + self.gradientType + "']").prop('checked', true);
            if (self.initValue) {
                _.each(self.initValue, function (dotData) {
                    self._appendDot(dotData);
                });
            }
            self.updateGradient();
        }, 100);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    _parseValue: function (value) {
        if (!value || value === 'none') {
            this.initValue = [{
                color: 'rgba(0, 210, 255, 0.8)',
                percentage: 0
            }, {
                color: 'rgba(58, 123, 213, 0.8)',
                percentage: 100
            }];
            return;
        }
        var self = this;
        this.initValue = [];
        this.gradientType = 'linear-gradient';
        if (value) {
            var val = value.replace(/, ?url\(["']?(.+?)["']?\)/, '');

            // match gradient type
            var typeMatch = value.match('linear-gradient|radial-gradient');
            this.gradientType = typeMatch && typeMatch[0] || 'linear-gradient';

            // match gradient direction
            var directionMatch = value.match('([0-9]+)deg');
            this.gradientDirection = directionMatch && parseInt(directionMatch[1]) || 45;

            // match gradient colors
            var m;
            var regex = /(rgba?\([0-9]+, ?[0-9]+, ?[0-9]+(?:, [0-9.]*)?\)) ?([0-9.]+)%/g;
            while ((m = regex.exec(val)) !== null) {
                // This is necessary to avoid infinite loops with zero-width matches
                if (m.index === regex.lastIndex) {
                    regex.lastIndex++;
                }
                // The result can be accessed through the `m`-variable.
                if (m.length === 3) {
                    self.initValue.push({
                        color: m[1],
                        percentage: parseFloat(m[2])
                    });
                }
            }
        }
    },
    /**
     * @private
     */
    _appendDot: function (data) {
        var dotTemplate = QWeb.render('droggol_theme_common.gradiant_dialog_dot', data);
        this.$('.drg-gradient-selector').append(dotTemplate);
        this.updateGradient();
    },
    /**
     * @private
     */
    getRandomColor: function () {
        return "rgba(0,0,0,0.5)";
    },
    /**
     * @private
     */
    updateGradient: function () {
        this.$('.drg-gradient-selector').css('background-image', this.getGradientStr('to right', 'linear-gradient'));
        if (this.image) {
            var imageStr = _.str.sprintf(' %s, url(%s)', this.getGradientStr(), this.image);
        } else {
            var imageStr = _.str.sprintf(' %s', this.getGradientStr());
        }
        this.$('.drgl-gradiant-image-preview').css('background-image', imageStr);
    },
    /**
     * @private
     */
    _onApplyPick: function () {
        this.trigger_up('gradiant_pick', {
            style: $(".drgl-gradiant-image-preview").css('background-image')}
        );
    },
    /**
     * @private
     */
    getGradientStr: function (direction, gradientType) {
        var dotList = [];
        _.each(this.$('.drg-gradient-dot'), function (el) {
            var $el = $(el);
            dotList.push({
                color: $el.find('.drg-gradient-dot-visual').css('background-color'),
                percentage: $el.attr('percentage') && parseFloat($el.attr('percentage')) || 0
            });
        });
        dotList = _.sortBy(dotList, function (l) {
            return l.percentage;
        });

        var colorStrList = _.map(dotList, function (dot) {
            return _.str.sprintf('%s %s%%', dot.color, dot.percentage);
        });
        var colorStr = colorStrList.join(', ');
        var directionDeg = this.$('.gradiant-range-input').val();
        if (!direction) {
            direction = _.str.sprintf("%sdeg", directionDeg || 45);
        }
        if (!gradientType) {
            gradientType = this.$("input[name='gradient_type']:checked").val();
        }
        var result = '';
        if (gradientType === 'linear-gradient') {
            result = _.str.sprintf('%s(%s, %s)', gradientType, direction, colorStr);
        } else {
            result = _.str.sprintf('%s(%s, %s)', gradientType, 'circle', colorStr);
        }
        return result;
    },
    /**
     * @private
     */
    _inbuiltGradientToStr: function (dotList) {
        var colorStrList = _.map(dotList, function (dot) {
            return _.str.sprintf('%s %s%%', dot.color, dot.percentage);
        });
        var colorStr = colorStrList.join(', ');
        return _.str.sprintf('linear-gradient(135deg, %s)', colorStr);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onMouseDown: function (ev) {
        this.doNotAdd = true;
        this.activeDot = $(ev.currentTarget).parent();
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onMouseMove: function (ev) {
        if (this.activeDot) {
            var percentage = this._getPercenteage(ev);
            this.activeDot.css('left', _.str.sprintf('%s%%', percentage));
            this.activeDot.attr('percentage', percentage);
            this.updateGradient();
        }
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onMouseUp: function (ev) {
        if (!this.doNotAdd && !this.activeDot) {
            this._onAddDot(ev);
        }
        this.doNotAdd = false;
        this.activeDot = false;
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onAddDot: function (ev) {
        if ($(ev.target).hasClass('drg-gradient-selector')) {
            var percentage = this._getPercenteage(ev);
            var data = {
                color: this.getRandomColor(),
                percentage: percentage,
            };
            this._appendDot(data);
        }
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onDeleteDot: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.doNotAdd = true;
        var $target = $(ev.currentTarget);
        $target.parent().remove();
        this.updateGradient();
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onDeleteDotUp: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.doNotAdd = true;
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _onEditDot: function (ev) {
        var $target = $(ev.currentTarget);
        var $dialog = new ColorpickerDialog(this, {
            defaultColor: $target.attr('color')
        });
        $dialog.open();
        $dialog.on('colorpicker:saved', this, function (ev) {
            var data = ev.data;
            var color = _.str.sprintf('rgba(%s, %s, %s, %s)', data.red, data.green, data.blue, data.opacity / 100);
            $target.siblings('.drg-gradient-dot-visual').css('background-color', color);
            $target.attr('color', color);
            this.updateGradient();
        });
    },
    /**
     * @private
     * @param  {Event} ev
     */
    _getPercenteage: function (ev) {
        var $gradientSelector = this.$('.drg-gradient-selector');
        var offset = $gradientSelector.offset();
        var left = ev.pageX - offset.left;
        var width = $gradientSelector.width();
        var percentage = (left / width) * 100 - 0.4;
        // percentage = Math.round(percentage);
        percentage = percentage.toFixed(2);
        percentage = Math.max(percentage, 0);
        percentage = Math.min(percentage, 100);
        return percentage;
    },
    /**
     * @private
     */
    _onDirectionChange: function () {
        var value = this.$('.gradiant-range-input').val();
        this.$('.drg-range-preview').text(value + 'deg');
        this.updateGradient();
    },
    /**
     * @private
     */
    _onTypeChange: function () {
        this.updateGradient();
    },
    _onInbuiltGradientClick: function (ev) {
        var self = this;
        this.$('.drg-gradient-dot').remove();
        var key = $(ev.currentTarget).attr('key');
        _.each(this.inbuiltGrediant[key], function (dotData) {
            self._appendDot(dotData);
        });
    }
});

});
