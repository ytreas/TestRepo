odoo.define('droggol_theme_common.wysiwyg.fonts', function (require) {
'use strict';

var fonts = require('wysiwyg.fonts');

fonts.fontIcons.unshift({base: 'lnr', parser: /\.(lnr-(?:\w|-)+)::?before/i});
fonts.fontIcons.unshift({base: 'lni', parser: /\.(lni-(?:\w|-)+)::?before/i});
fonts.fontIcons.unshift({base: 'ri', parser: /\.(ri-(?:\w|-)+)::?before/i});

});
