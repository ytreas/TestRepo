odoo.define('droggol_theme_common.wysiwyg.widgets.media', function (require) {

var IconWidget = require('wysiwyg.widgets.media').IconWidget;

IconWidget.include({
    xmlDependencies: IconWidget.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/wysiwyg.xml']
    ),
    save: function () {
        var iconFont = this._getFont(this.selectedIcon) || {base: 'fa', font: ''};
        if (iconFont.base === 'lnr') {
            this.nonIconClasses = this.nonIconClasses.filter(icon => !_.contains(['fa', 'lni', 'ri'], icon));
        }
        if (iconFont.base === 'lni') {
            this.nonIconClasses = this.nonIconClasses.filter(icon => !_.contains(['fa', 'lnr', 'ri'], icon));
        }
        if (iconFont.base === 'ri') {
            this.nonIconClasses = this.nonIconClasses.filter(icon => !_.contains(['fa', 'lnr', 'lni'], icon));
        }
        if (iconFont.base === 'fa') {
            this.nonIconClasses = this.nonIconClasses.filter(icon => !_.contains(['lni', 'lnr', 'ri'], icon));
        }
        return this._super.apply(this, arguments);
    },
});

});
