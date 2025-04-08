/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
export const Payments = publicWidget.Widget.extend({
    selector: '.js_payment',
    events: {
        'click .js_btn_pay': '_preparePaymentData',
        'change .payment_option': '_select_payment_option',
        'click .btn-cancel': '_showModal',



    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
        this.order_id = null;
        this.t_amt = null;

        this.rpc = this.bindService("rpc");


    },
    start() {
        window.addEventListener('pageshow', function (event) {
            if (event.persisted) {
                window.location.reload();
            }
        });

        let customEvent = new CustomEvent('')
    },
    _showModal: function (ev) {
        this.$('#payment_modal').modal('hide');

    },
    _select_payment_option: async function (ev) {
        const currentElement = this.$(ev.target).closest('div');
        this.$('div').css('box-shadow', 'none');
        currentElement.css('box-shadow', '0 0 0 0.1rem #00ca61');
        this.$('.js_btn_pay').removeClass('d-none');
        let formData = {
            type: ev.target.value,
        }
        const initial_price = parseFloat($('span#odc_total_price').data('initial-charge'));
        let total_price = 0;

        await this.rpc("/get_extra_fees", formData).then((data) => {
            if (data.success) {
                this.$('.extra_charge_container').html(data.data.ui);
                total_price = initial_price + parseFloat(data.data.total_extra_price);
                this.$('#odc_total_price').text(total_price)
                this.t_amt = total_price;
            }
            else {
                const props = {
                    'success': false,
                    'message': _t("Oops! Something went wrong. Please try again later.") + data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }


        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        });

        formData = {
            type: ev.target.value,
            order_token: this.$('#order_id').val(),
            extra_charges: this._getExtraPrices(),
            t_amt: this.t_amt,
        };

        if (ev.target.value == 'cod') {
            this.$('.js_btn_pay').text(_t('Order Now'));
        }
        else if (ev.target.value == 'esewa') {
            this.rpc('/ecommerce_esewa_payment_redirect', formData).then((data) => {
                if (data.success) {
                    this.$('.js_payment_form_container').html(data.data);
                }

            }
            ).catch((e) => {
                const props = {
                    'success': false,
                    'message': _t("Some error occurred! Please try again later."),
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            })
        }

        else {
            this.$('.js_btn_pay').text(_t('Pay Now'));

        }

    },
    _preparePaymentData: function (ev) {
        ev.preventDefault();
        const payment_method = this.$('.payment_option:checked').val();
        let formData = {
            order_id: this.$('#order_id').val(),
            extra_charges: this._getExtraPrices(),
            t_amt: this.t_amt,
            payment_method: payment_method,
        }
        
        $('.loader-wrapper').removeClass('d-none');

        if (payment_method == 'cod') {
            this.rpc('/order_now', formData).then((data) => {
                if (data.success) {
                    myUtils.sweetSuccessNotification(this.call.bind(this), { 'message': data.message })
                    location.href = data.success_url
                }
                else {
                    const props = {
                        'success': false,
                        'message': data.message,
                    }
                    $('.loader-wrapper').addClass('d-none');
                    myUtils.sweetCartNotification(this.call.bind(this), props)
                }


            }).catch((err) => {
                const props = {
                    'success': false,
                    'message': _t("Some error occurred! Please try again later."),
                }
                $('.loader-wrapper').addClass('d-none');
                myUtils.sweetCartNotification(this.call.bind(this), props)
            })

        }
        else if (payment_method == 'esewa') {
            this.$('#paymentForm').submit();
        }
        else if (payment_method == 'khalti') {
            // formData.t_amt = 178; // For testing purpose only.
            this.rpc('/ecommerce_khalti_initiate', formData).then((data) => {
                if (data.success) {
                    location.href = data.data
                }
                else {
                    const props = {
                        'success': false,
                        'message': data.message,
                    }
                    $('.loader-wrapper').addClass('d-none');
                    myUtils.sweetCartNotification(this.call.bind(this), props)
                }

            }
            ).catch((e) => {

                const props = {
                    'success': false,
                    'message': _t("Some error occurred! Please try again later.") + e,
                }
                $('.loader-wrapper').addClass('d-none');
                myUtils.sweetCartNotification(this.call.bind(this), props)
            })
        }

        this._getExtraPrices();
        if (this.$('.payment_option:checked').val() == 'cod') {
        }

        setTimeout(() => {
            const props = {
                'success': false,
                'message': _t("Something went wrong! Please try again later."),
            }
            $('.loader-wrapper').addClass('d-none');
            myUtils.sweetCartNotification(this.call.bind(this), props)
        }, 1000*60*2);

    },



    _getExtraPrices: function (ev) {
        let charges = [];
        this.$('.extra_charge_price').each(function () {
            charges.push(this.value);
        });
        const total_extra_amt = this.$('#total_extra_amt').val();

        return {
            'charges_title': charges,
            'total_extra_amt': total_extra_amt
        };
    },
    _userActivityBuy: function (product_id, user_id) {
        let activity_details = {};
        activity_details = {
            "product_id": product_id,
            "activity_type": "purchase",
            "user_id": user_id,
        }

        this.rpc("/create_user_activity", activity_details);

    },




});


publicWidget.registry.Payments = Payments;



