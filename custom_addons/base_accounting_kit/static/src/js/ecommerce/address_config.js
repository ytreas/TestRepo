/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
export const AddressConfig = publicWidget.Widget.extend({
    selector: '.js_address_config_page',
    events: {
        'click .edit-address': '_handleAddressModal',
        'click .btn-cancel': '_closeModal',
        'click .btn-cancel-add-new': '_closeModalAddNew',
        'click .add-new-shipping-btn': '_addNewModal',
        'click .add-new-billing-btn': '_addNewModalBilling',       
        'click .btn-submit': '_handleFormSubmit',
        'click .js_btn_close': '_fetchDefaultLocations',
        'focusout input#phone': '_onValidatePhoneInput',
        'change input.js_shipping_address': '_updateAddressChange',
        'click .card_edit': '_deleteAddressCard',
        // 'click .proceed_to_pay_btn': '_validateForm',


    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        this.fullname = null;
        this.phone = null;
        this.email = null;
        this.street = null;
        this.address = null;
        this.type = null;
        this.default_billing_address = null;
        this.default_shipping_address = null;
        this.vendor_individual_subtotal = [];


        this.delivery_price = 0;
        this.rpc = this.bindService("rpc");


    },

    start() {
        this.rpc("/get_default_addresses", {
        }).then((data) => {
            this.$('.default_address_field').html(data.default_address);

        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        });


        this._get_vendor_to_delivery_location_distance();
        $('.proceed_to_pay_btn').removeClass('d-none');


    },

    _fetchDefaultLocations: function (ev) {
        this.rpc("/get_default_addresses", {
        }).then((data) => {
            this.$('.default_address_field').html(data.default_address);

        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        });
        this._closeModal('address_configure_modal');
    },
    _toggleModal: function (id) {
        $(`#${id}`).modal('toggle');
    },
    _closeModal: function (ev) {
        this._toggleModal('address_configure_modal');

    },
    _closeModalAddNew: function (ev) {
        this._toggleModal('add_new_address');

    },

    _handleAddressModal: function (ev) {
        this._toggleModal('address_configure_modal');
    },
    _addNewModal: function (ev) {
        this._toggleModal('address_configure_modal');
        this._toggleModal('add_new_address');
        this.rpc("/render_address_modal_view", {
        }).then((data) => {
            this.$('.modal-content-address').html(data.data);
            this.$('#modalTitle').text(_t('Add New Shipping Address'));
            this.$('#type').val('shipping')
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });
    },

    _addNewModalBilling: function (ev) {
        this.rpc("/render_address_modal_view", {
        }).then((data) => {
            this.$('.modal-content-address').html(data.data);
            this.$('#modalTitle').text(_t('Add New Billing Address'));
            this._toggleModal('address_configure_modal');
            this._toggleModal('add_new_address');
            this.$('#type').val('invoicing')
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });


    },
    __Msg: function (msg, icon) {
        if (icon === 'success') {
            myUtils.sweetSuccessNotification(this.call.bind(this), { 'message': msg || _t('Success') });
        }
        else {
            myUtils.sweetCartNotification(this.call.bind(this), { 'success': false, 'message': msg || _t('Something went wrong!!') });

        }
    },
    _handleFormSubmit: function (ev) {
        ev.preventDefault();
        const form = $('.addressForm')[0];
        this.fullname = this.$('#fullname').val().trim();
        this.phone = this.$('#phone').val().trim();
        this.email = this.$('#email').val().trim();
        this.street = this.$('#street').val().trim();
        this.address = this.$('#address').val().trim();
        this.type = this.$('#type').val();
        this.latitude = this.$('#address_latitude').val();
        this.longitude = this.$('#address_longitude').val();

        if (!this.fullname) {
            this.__Msg(_t("Full name cannot be empty."), 'error');
            return;
        }

        const phoneRegex = /^[0-9+]+$/;
        if (!this.phone || !phoneRegex.test(this.phone)) {
            this.__Msg(_t("Phone number is invalid."), 'error');
            return;

        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!this.email || !emailRegex.test(this.email)) {
            this.__Msg(_t("Email is invalid."), 'error');
            return;

        }

        if (!this.street) {
            this.__Msg(_t("Street cannot be empty."), 'error');
            return;

        }

        if (!this.address) {
            this.__Msg(_t("Address cannot be empty."), 'error');
            return;

        }

        const formData = {
            'fullname': this.fullname,
            'phone': this.phone,
            'email': this.email,
            'street': this.street,
            'address': this.address,
            'type': this.type,
            'latitude': this.latitude,
            'longitude': this.longitude,
        }
        this.rpc("/save_address", formData).then((data) => {
            if (data) {
                if (data.success) {
                    this._toggleModal('add_new_address');
                    this._updateMainAddressView();
                    myUtils.sweetSuccessNotification(this.call.bind(this), { 'message': data.data })
                } else {
                    const props = {
                        'success': false,
                        'message': _t("Cannot add new address"),
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)

                }
            }
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });


    },
    _updateMainAddressView: function (ev) {
        this.rpc("/update_main_address_view").then((data) => {
            if (data) {
                this.$('.js_main_address_modal').html(data.data)
                $(`#address_configure_modal`).modal('show');
                // location.reload();
                this._get_vendor_to_delivery_location_distance();

            }
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });
    },
    _updateAddressChange: function (ev) {
        const formData = {
            "address_id": $(ev.target).data('address-id'),
        };

        this.rpc("/change_address", formData).then((data) => {
            if (data) {
                if (data.success) {
                    const props = {
                        'message': _t("Address Updated Successfully")
                    }
                    myUtils.sweetSuccessNotification(this.call.bind(this), props)
                    this._updateMainAddressView();

                } else {
                    const props = {
                        'success': false,
                        'message': _t("Cannot change the address"),
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)

                }
            }
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });
    },


    _onValidatePhoneInput: function (ev) {
        // $('#result').text('');
        const phone = this.$('#phone').val().trim();
        const phoneRegex = /^9\d{9}$/;
        if (!phoneRegex.test(phone)) {
            $('#result').text('Invalid phone number. Please enter a 10-digit number starting with 9.').css('color', 'red');
            this.$('#phone').val(phone.replace(/[^0-9]/g, ''));
        } else {
            $('#result').text('');

        }
        if (phone.length > 10) {
            $(this).val(phone.slice(0, 10));
        }
    },


    _deleteAddressCard: function (ev) {
        const cardId = this.$(ev.target).closest('div').data('card-id');

        this.rpc("/delete_address", {
            card_id: cardId,
        }).then((data) => {
            if (data) {
                if (data.success) {
                    this._updateMainAddressView();
                    const props = {
                        'message': _t("Address Deleted Successfully")
                    }
                    myUtils.sweetSuccessNotification(this.call.bind(this), props)

                } else {
                    const props = {
                        'success': false,
                        'message': data.message,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)

                }
            }
        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t("Some error occurred! Please try again later."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)

        });
    },


    // _getVendorIndividualSubtotals: function () {
    //     let ev = this;
    //     this.vendor_individual_subtotal = [];
    //     this.$('.js_vendor_subtotal').each(function () {

    //         let values = {
    //             'vendor_id': $(this).data('company-id'),
    //             'total_price': $(this).data('company-total-price'),
    //         };
    //         console.log(values);

    //         ev.vendor_individual_subtotal.push(values);
    //     });
    //     return this.vendor_individual_subtotal;
    // },
    _get_vendor_to_delivery_location_distance: function () {
        let order = this.$('#order_arr').val();
        this.delivery_price = 0;

        this.rpc('/refresh_products_delivery_charges', { order }).then((data) => {
            if (data.success) {
                this.$('.js_product_template').html(data.template);
                let self = this;

                let delivery_prices = this.$('.js_delivery_item_price')
                delivery_prices.each(function (index, elem) {
                    let data_elem = $(elem).data('delivery-price');
                    self.delivery_price += parseInt(data_elem, 0);
                });
                $('#odc_shipping_price').text(this.delivery_price);

                const overall_total_price = parseInt($('#overall_total_price').val());

                $('#odc_item_price').text(overall_total_price - this.delivery_price);
                $('#odc_total_price').text(overall_total_price);
                $('#t_amt').val(parseInt(overall_total_price));

                // $('#price_breakdown').val(JSON.stringify(this._getVendorIndividualSubtotals()));



            }
            else {
                console.error(data.message);

            }
        });



    },

});


publicWidget.registry.AddressConfig = AddressConfig;



