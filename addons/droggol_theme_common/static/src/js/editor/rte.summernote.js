odoo.define('droggol_theme_common.rte.summernote', function (require) {

require('web_editor.rte.summernote');
var core = require('web.core');

var _t = core._t;

var dom = $.summernote.core.dom;
var eventHandler = $.summernote.eventHandler;

var fn_attach = eventHandler.attach;
eventHandler.attach = function (oLayoutInfo, options) {
    fn_attach.call(this, oLayoutInfo, options);
    create_dblclick_feature("i.lnr, span.lnr", function () {
        eventHandler.modules.imageDialog.show(oLayoutInfo);
    });
    create_dblclick_feature("i.lni, span.lni", function () {
        eventHandler.modules.imageDialog.show(oLayoutInfo);
    });
    create_dblclick_feature("i.ri, span.ri", function () {
        eventHandler.modules.imageDialog.show(oLayoutInfo);
    });
    function create_dblclick_feature(selector, callback) {
        var show_tooltip = true;

        oLayoutInfo.editor().on("dblclick", selector, function (e) {
            var $target = $(e.target);
            if (!dom.isContentEditable($target)) {
                // Prevent edition of non editable parts
                return;
            }

            show_tooltip = false;
            callback();
            e.stopImmediatePropagation();
        });

        oLayoutInfo.editor().on("click", selector, function (e) {
            var $target = $(e.target);
            if (!dom.isContentEditable($target)) {
                // Prevent edition of non editable parts
                return;
            }

            show_tooltip = true;
            setTimeout(function () {
                // Do not show tooltip on double-click and if there is already one
                if (!show_tooltip || $target.attr('title') !== undefined) {
                    return;
                }
                $target.tooltip({title: _t('Double-click to edit'), trigger: 'manuel', container: 'body'}).tooltip('show');
                setTimeout(function () {
                    $target.tooltip('dispose');
                }, 800);
            }, 400);
        });
    }
};

});
