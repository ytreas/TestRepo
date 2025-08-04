odoo.define('droggol_theme_common.service_worker_register', function (require) {
'use strict';

require('web.dom_ready');
var Widget = require('web.Widget');
var utils = require('web.utils');

var html = document.documentElement;
var websiteID = html.getAttribute('data-website-id') || 0;

var PwaIosPopupWidget = Widget.extend({
    xmlDependencies: ['/droggol_theme_common/static/src/xml/pwa.xml'],
    template: 'droggol_theme_common.pwa_ios_popup_template',
    events: {
        'click': '_onClickPopup',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.websiteID = websiteID;
    },
    _onClickPopup: function () {
        utils.set_cookie(_.str.sprintf('dr-pwa-popup-%s', websiteID), true);
        this.destroy();
    },
});

$.ajax('/pwa/is_pwa_active', { dataType: "json" })
    .done(function (json_data) {
        if (json_data.pwa) {
            activateServiceWorker();
        } else {
            deactivateServiceWorker();
        }
    });

function displayPopupForiOS () {
    // Detects if device is on iOS
    const isIos = () => {
        return /^((?!chrome|android).)*safari/i.test(navigator.userAgent) && (navigator.userAgent.match(/iPad/i) || navigator.userAgent.match(/iPhone/i));
    }

    // Detects if device is in standalone mode
    const isInStandaloneMode = () => ('standalone' in window.navigator) && (window.navigator.standalone);

    // Checks if should display install popup notification:
    if (isIos() && !isInStandaloneMode()) {
        if (!utils.get_cookie(_.str.sprintf('dr-pwa-popup-%s', websiteID))) {
            var pwaIosPopupWidget = new PwaIosPopupWidget();
            pwaIosPopupWidget.appendTo($('body'));
        }
    }
}

function activateServiceWorker() {
    if (navigator.serviceWorker) {
        navigator.serviceWorker.register('/service_worker.js').then(function(registration) {
            displayPopupForiOS();
            console.log('ServiceWorker registration successful with scope:',  registration.scope);
        }).catch(function(error) {
            console.log('ServiceWorker registration failed:', error);
        });
    }
}

function deactivateServiceWorker() {
    if (navigator.serviceWorker) {
        navigator.serviceWorker.getRegistrations().then(function (registrations) {
            _.each(registrations, function (r) {
                r.unregister();
                console.log('ServiceWorker removed successfully');
            });
        }).catch(function (err) {
            console.log('Service worker unregistration failed: ', err);
        });
    }
}


});
