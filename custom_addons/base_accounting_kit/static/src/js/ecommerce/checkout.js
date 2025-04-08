/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
export const CheckoutProceed = publicWidget.Widget.extend({
    selector: '.js_checkout',
    events: {
        'click .proceed_to_pay_btn': '_preparePaymentData',

    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
        this.delivery_price = 0;
        this.vendor_individual_subtotal=[];

        this.rpc = this.bindService("rpc");


    },

    _preparePaymentData: function (ev) {
        ev.preventDefault();
        let even=this;
        let pickup_type = $('.pickup_type:checked').val();
        if (!pickup_type) {
            const props = {
                'success': false,
                'message': _t("Please add shipping address"),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
            return;
        }
        const formData = {
            order_id: even.$('#my_orders').val(),
            total_amt: even.$('#t_amt').val(),
            pickup_type: pickup_type,
            price_breakdown: JSON.stringify(even._getVendorIndividualSubtotals()),
        }
        const formHasInvalidValue = Object.values(formData).some(value => value === null || value === undefined || value === '');
        if (formHasInvalidValue) {
            const props = {
                'success': false,
                'message': _t("Something went wrong please try again!!"),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
            return;
        }
        this.rpc("/get_checkout_confirmation", formData).then((data) => {
            if (data.success) {
                location.href = data.data;

            }
            else {
                const props = {
                    'success': false,
                    'message': _t("Oops! Something went wrong. Please try again later."),
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
    },

    _getVendorIndividualSubtotals: function () {
        let ev = this;
        this.vendor_individual_subtotal = [];
        $('.js_vendor_subtotal').each(function () {

            let values = {
                'vendor_id': $(this).data('company-id'),
                'total_price': $(this).data('company-total-price'),
            };

            ev.vendor_individual_subtotal.push(values);
        });
        return this.vendor_individual_subtotal;
    },

});

publicWidget.registry.CheckoutProceed = CheckoutProceed;


export const RegionAutoComplete = publicWidget.Widget.extend({
    selector: '.js_location_autocomplete',
    events: {
        'input #address': '_get_location_auto_complete',
        'keydown #address': '_handleSearchKeyDown',

    },
    init: function () {
        this._super.apply(this, arguments);
        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
        this.rpc = this.bindService("rpc");
        this.currentIndex = -1;
    },

    _get_location_auto_complete: function (ev) {
        const query = ev.target.value;
        const suggestionsList = $('#location-suggestions');
        suggestionsList.empty().show().append('<li>Loading...</li>');

        if (query.length < 3) {
            suggestionsList.hide();
            return;
        }

        const bbox = '80.0582,26.3470,88.2015,30.4227'; // Nepal's bounding box
        const url = `https://photon.komoot.io/api?q=${query}&bbox=${bbox}&limit=5`;

        fetch(url)
            .then((response) => response.json())
            .then((data) => {
                const suggestions = data.features.map((feature) => {
                    const name = feature.properties.name || feature.properties.street || '';
                    const city = feature.properties.city || '';
                    const region = feature.properties.state || '';
                    const [longitude, latitude] = feature.geometry.coordinates;
                    let address_val = {
                        name,
                        city,
                        region,
                        latitude,
                        longitude,
                    };

                    return address_val;
                });

                this._showSuggestions(suggestions);
            })
            .catch((error) => {
                console.error('Error fetching suggestions:', error);
                suggestionsList.hide();
            });
    },

    _showSuggestions: function (suggestions) {
        const suggestionsList = $('#location-suggestions');
        suggestionsList.empty();
        this._addOutsideClickHandler();

        if (suggestions.length === 0) {
            suggestionsList.hide();
            return;
        }

        suggestions.forEach((suggestion, index) => {
            const item = $('<li>', {
                class: 'list-group-item list-group-item-action',
                text: `${suggestion.name}, ${suggestion.city}, ${suggestion.region}`,
                tabindex: index,
            });
            item.on('click', () => {
                $('#address').val(`${suggestion.name}, ${suggestion.city}, ${suggestion.region}`);
                $('#address_latitude').val(suggestion.latitude);
                $('#address_longitude').val(suggestion.longitude);

                suggestionsList.hide();
            });
            suggestionsList.append(item);
        });

        suggestionsList.show();
        this.currentIndex = -1;
    },
    _handleSearchKeyDown: function (ev) {
        const items = $('#location-suggestions').find('li');
        if (items.length === 0) return;

        if (ev.key === 'ArrowDown') {
            this.currentIndex = (this.currentIndex + 1) % items.length;
            this._updateSelection(items);
            ev.preventDefault();
        } else if (ev.key === 'ArrowUp') {
            this.currentIndex = (this.currentIndex - 1 + items.length) % items.length;
            this._updateSelection(items);
            ev.preventDefault();
        } else if (ev.key === 'Enter') {

            if (this.currentIndex >= 0 && items[this.currentIndex]) {
                $('#address').val($(items[this.currentIndex]).text());
                $('#location-suggestions').hide();
            }
            ev.preventDefault();
        } else if (ev.key === 'Escape') {
            $('#location-suggestions').hide();
            ev.preventDefault();
        }
    },


    _updateSelection: function (items) {
        items.removeClass('active-list');

        if (this.currentIndex >= 0 && items[this.currentIndex]) {
            $(items[this.currentIndex]).addClass('active-list').focus();
        }
    },

    _closeRecommendations: function () {
        $('#location-suggestions').hide();
    },

    _addOutsideClickHandler: function () {
        this._outsideClickHandler = (event) => {
            const recommendationsContainer = $('#location-suggestions');
            if (!recommendationsContainer[0].contains(event.target) && !this.$('#address')[0].contains(event.target)) {
                this._closeRecommendations();
            }
        };

        document.addEventListener('click', this._outsideClickHandler);
    },
});
publicWidget.registry.RegionAutoComplete = RegionAutoComplete;



