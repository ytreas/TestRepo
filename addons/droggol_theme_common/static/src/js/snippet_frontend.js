odoo.define('droggol_theme_common.snippet_frontend', function (require) {
'use strict';

require('web.dom_ready');
var Widget = require('web.Widget');

var PhotoSwipeLibraryWidget = Widget.extend({
    xmlDependencies: ['/droggol_theme_common/static/src/xml/photoswipe.xml'],
    template: 'droggol_theme_common.PhotoSwipeContainer',
});
var photoSwipe = new PhotoSwipeLibraryWidget();
photoSwipe.appendTo($('body'));

});
