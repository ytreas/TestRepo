odoo.define('droggol_theme_common.s_gallery_frontend', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var _t = core._t;

publicWidget.registry.s_gallery = publicWidget.Widget.extend({
    selector: '.s_gallery',
    read_events: {
        'click .gallery-image': '_onClickGalleryImage',
    },
    start: function () {
        this.items = _.map(this.$('.gallery-image'), function (item) {
            var $img = $(item).find('.img-fluid');
            if ($img.length) {
                return {
                    src: $img.attr('src'),
                    w: $img[0].naturalWidth,
                    h: $img[0].naturalHeight,
                    title: $img.attr('alt') || $img.attr('title'),
                };
            } else {
                return {
                    src: '/web/static/src/img/mimetypes/video.svg',
                    w: 300,
                    h: 300,
                    title: _t('Video')
                };
            }
        });
        return this._super.apply(this, arguments);
    },
    _onClickGalleryImage: function (ev) {
        var photoSwipe = new PhotoSwipe($('.pswp')[0], PhotoSwipeUI_Default, this.items, {
            shareButtons: [
                {id: 'download', label: _t('Download image'), url: '{{raw_image_url}}', download: true},
            ],
            index: $(ev.currentTarget).parent().index(),
            closeOnScroll: false,
            bgOpacity: 0.8,
            tapToToggleControls: false,
            clickToCloseNonZoomable: false,
        });
        photoSwipe.init();
    },
});

});
