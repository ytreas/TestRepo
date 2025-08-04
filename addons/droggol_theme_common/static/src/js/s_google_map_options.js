odoo.define('droggol_theme_common.s_google_map_options', function (require) {
'use strict';

var Dialog = require('web_editor.widget').Dialog;
var core = require('web.core');
var sOptions = require('web_editor.snippets.options');

var _t = core._t;

sOptions.registry.s_google_map = sOptions.Class.extend({
    xmlDependencies: ['/droggol_theme_common/static/src/xml/s_google_map.xml'],

    onBuilt: function () {
        this._super.apply(this, arguments);
        this.map('click', null, null);
    },

    map: function (previewMode, value, $opt) {
        var self = this;
        this.dialog = new Dialog(this, {
            size: 'medium',
            title: _t("Configure Map"),
            buttons: [
                {
                    text: _t("Save"), classes: 'btn-primary', click: function () {
                        var embedHtml = this.$('#embed_html').val().trim();
                        if (!embedHtml) {
                            self.$target.remove();
                            self.trigger_up('cover_update');
                        }
                        var regex = /<iframe .*src=[\"\'](.*?)[\"\'].*?>/;
                        if (regex.exec(embedHtml)) {
                            var src = regex.exec(embedHtml)[1];
                            self.$target.find('iframe.map').attr({src: src});
                        } else {
                            self.$target.remove();
                            self.trigger_up('cover_update');
                        }
                        this.close();
                    }
                }, {
                    text: _t("Cancel"), close: true, click: function () {
                        if (!self.$target.find('iframe.map').attr('src').trim()) {
                            self.$target.remove();
                            self.trigger_up('cover_update');
                        }
                    }
                },
            ],
            $content: $(core.qweb.render('droggol_theme_common.s_google_map')),
        }).open();

        this.dialog.opened().then((function () {
            this.$('#embed_html').val(self.$target.find('iframe.map').attr('src'));
        }).bind(this.dialog));
    },

});

});
