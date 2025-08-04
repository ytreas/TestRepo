odoo.define('droggol_theme_common.wysiwyg.widgets.linkdialog', function (require) {

var LinkDialog = require('wysiwyg.widgets').LinkDialog;

LinkDialog.include({
    xmlDependencies: LinkDialog.prototype.xmlDependencies.concat(
        ['/droggol_theme_common/static/src/xml/wysiwyg-links.xml']
    )
});

});
