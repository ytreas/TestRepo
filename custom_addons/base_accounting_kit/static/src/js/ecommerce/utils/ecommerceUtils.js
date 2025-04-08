/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

function sweetCartNotification(callService, props, options = {}) {
    if (props.success) {
        callService("cartNotificationService", "add", _t("Item(s) added to your cart"), {
            lines: [{
                'id': 1,
                'image_url': props.image_url,
                'quantity': props.quantity,
                'name': props.name,
                'description': '',
                'line_price_total': props.price_total,
            }],
            currency_id: 1,
            ...options,
        });
    }
    if (!props.success) {
        callService("cartNotificationService", "add", _t("Warning"), {
            warning: props.message || _t('Sorry, Something went wrong. Please try again.'),
            ...options,
        });
    }

    // console.log('callService',callService);
    // console.log('props',props);

}

function sweetSuccessNotification(callService, props, options = {}) {
    callService("cartNotificationService", "add", _t("Success"), {
        success: props.message || _t('Working like a butter!!'),
        ...options,
    });
}


function alert(type = 'dialog', title = null, icon = 'success', message) {
    if (type === 'dialog') {


    }
    if (type === 'toast') {
        const Toast = Swal.mixin({
            toast: true,
            position: "top-end",
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.onmouseenter = Swal.stopTimer;
                toast.onmouseleave = Swal.resumeTimer;
            }
        });
        Toast.fire({
            title: title,
            text: message,
            icon: icon
        });
    }
}


export default {
    sweetCartNotification: sweetCartNotification,
    sweetSuccessNotification: sweetSuccessNotification,
    alert: alert,
}