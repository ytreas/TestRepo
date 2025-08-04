odoo.define('droggol_theme_common.notification', function (require) {
"use strict";

var Notification = require('web.Notification');

return Notification.extend({

    template: "DroggolNotification",

    xmlDependencies: (Notification.prototype.xmlDependencies || [])
        .concat(['/droggol_theme_common/static/src/xml/droggol_notification.xml']),

    /**
    * @override
    */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.d_icon = params.d_icon;
        this.d_image = params.d_image;
    },
    start: function () {
        this.autohide = _.cancellableThrottleRemoveMeSoon(this.close, 5000, {leading: false});
        this.$el.on('shown.bs.toast', () => {
            this.autohide();
        });
        return this._super.apply(this, arguments);
    },
});
});
