/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
import { loadJS } from "@web/core/assets";
export const MyOrders = publicWidget.Widget.extend({
    selector: '.js_my_orders',
    events: {
        'change #filterOptions': '_handleFilterChange',
        'click .btn-smash': '_handleSmash',
        'click .js_btn_cancel': '_cancelOrder',

    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        this.smash_count = 0;

        this.rpc = this.bindService("rpc");
        this.selected_option = 'all';

        loadJS('https://cdn.jsdelivr.net/npm/sweetalert2@11');

    },
    _filter_that_list: function (formData = {}) {

        this.rpc(`/filter_my_order/${this.selected_option}`, formData).then((data) => {
            if (data.success) {
                this.$('.my_orders_wrapper').html(data.content)
            }
            else {
                const props = {
                    'success': false,
                    'message': data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }
            this.$('#content_preloader').addClass('d-none');
        })
    },
    _handleFilterChange: function (ev) {
        this.selected_option = $(ev.target).val();
        this.$('#content_preloader').removeClass('d-none');
        this._filter_that_list();
    },
    _handleSmash: function (ev) {
        const smash_id = $(ev.target).closest('span').data('smash-id');
        this.rpc('/smash_that_order', { smash_id: smash_id }).then((data) => {
            if (data.success) {
                this.smash_count = this.smash_count + 1;
                const props = {
                    'message': _t("The Order Smashed Successfully!")
                }
                myUtils.sweetSuccessNotification(this.call.bind(this), props)
                if (this.smash_count > 3) {
                    const props = {
                        'success': false,
                        'message': _t("Its enough smash man!! Take rest."),
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)
                }
                this._filter_that_list();
            }
            else {
                const props = {
                    'success': false,
                    'message': data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)

            }
        })

    },

    _cancelOrder: function (ev) {
        const order_id = $(ev.target).data('order-id');
        Swal.fire({
            title: _t("Are you sure?"),
            text: _t("You won't be able to revert this cancellation!"),
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#3085d6",
            cancelButtonColor: "#d33",
            confirmButtonText: _t("Yes, cancel it!")
        }).then((result) => {
            if (result.isConfirmed) {
                this.rpc('/cancel_order', { order_id: order_id }).then((data) => {
                    if (data.success) {
                        myUtils.alert('toast', _t("Cancelled!"), 'success', _t("Your order has been cancelled."))
                        this._filter_that_list();
                    }
                    else {
                        myUtils.alert('toast', _t("Something went wrong!"), 'error', data.message)

                    }
                })




            }
        });
    },


});


publicWidget.registry.MyOrders = MyOrders;

export const EcommerceUserDashboard = publicWidget.Widget.extend({
    selector: '.js_user_dashboard',
    events: {
        'click .dash__link:not(.dash_home)': '_fetchCurrentPage',

    },
    init: function () {
        this._super.apply(this, arguments);

        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
        this.rpc = this.bindService('rpc');
    },

    _fetchCurrentPage: function (ev) {
        ev.preventDefault();
        const target = this.$(ev.target).closest('a');
        this.$('.dash__link').removeClass('active');
        target.addClass('active');
        const link = target.attr('href');
        this.$('#content_preloader').removeClass('d-none');
        this._fetchContent(link);
    },

    _fetchContent: function (link) {
        this.rpc(link, {}).then((data) => {
            this.$('#content_preloader').addClass('d-none');

            if (data.success) {
                this.$('.js_rendering').html(data.data)
            }
        })
    }
});


publicWidget.registry.EcommerceUserDashboard = EcommerceUserDashboard;



export const MyAuth = publicWidget.Widget.extend({
    selector: '#loginModal',
    events: {
        'click #submitBtn': '_handleAuthSubmit',

    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        this.rpc = this.bindService("rpc");

    },

    _handleAuthSubmit: function (ev) {
        ev.preventDefault();

        const email = this.$('#userEmail').val();
        const password = this.$('#userPass').val();

        if (!email || !password) {
            const props = {
                'success': false,
                'message': _t("Please enter email and password."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        }
        this.rpc('/user_login', { email: email, password: password }).then((data) => {
            if (data.success) {
                const props = {
                    'message': _t('Login successful.')
                }
                myUtils.sweetSuccessNotification(this.call.bind(this), props)
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }
            else {
                const props = {
                    'success': false,
                    'message': data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }
        })
    }


});
publicWidget.registry.MyAuth = MyAuth;