odoo.define('droggol_theme_common.contentMenu', function (require) {
"use strict";

var contentMenu = require('website.contentMenu');

contentMenu.EditMenuDialog.include({
    xmlDependencies: contentMenu.EditMenuDialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/website.contentMenu.xml']
    ),
    events: _.extend({}, contentMenu.EditMenuDialog.prototype.events, {
        'click span.dr_special_menu': '_onClickSpecialMenu',
    }),
    _onClickSpecialMenu: function (ev) {
        var $menu = $(ev.currentTarget).closest('[data-menu-id]');
        var menuID = $menu.data('menu-id');
        var menu = this.flat[menuID];
        var isActive = menu.fields['is_special_menu'];
        _.each(this.flat, function(menu_data, key) {
            menu_data.fields['is_special_menu'] = false;
        });
        this.$('.dr_special_menu').removeClass('badge-info');
        if (!isActive) {
            menu.fields['is_special_menu'] = true;
            $menu.find('.dr_special_menu').addClass('badge-info');
        }
    }
});

});
