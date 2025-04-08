/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import wSaleUtils from "@website_sale/js/website_sale_utils";
const cartHandlerMixin = wSaleUtils.cartHandlerMixin;
import "@website/libs/zoomodoo/zoomodoo";

export const ProductsSidebarLg = publicWidget.Widget.extend({
    selector: '.js-sidebar',
    events: {
        'input input.min_price': '_onValidateNumberInput',
        'input input.max_price': '_onValidateNumberInput',

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


    _onValidateNumberInput: function (ev) {
        const inputField = ev.target;
        const value = inputField.value;

        if (!/^\d*$/.test(value)) {
            inputField.value = value.replace(/\D/g, '');
        }
    },


});

publicWidget.registry.ProductsSidebarLg = ProductsSidebarLg



export const ProductVariantAttributes = publicWidget.Widget.extend({
    selector: '.product-variants-attributes',
    events: {
        'change  input[type="checkbox"]': '_onSubmitAttributeFilter',
    },


    init: function () {
        this._super.apply(this, arguments);

        // this._changeCartQuantity = debounce(this._changeCartQuantity.bind(this), 500);
        // this._changeCountry = debounce(this._changeCountry.bind(this), 500);

        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        // delete this.events['change .main_product:not(.in_cart) input.js_quantity'];
        // delete this.events['change [data-attribute_exclusions]'];

        this.rpc = this.bindService("rpc");



    },

    _onSubmitAttributeFilter: function (ev) {
        // Get all checked values (checkboxes that are checked)
        const checkedValues = $('input[type="checkbox"]:checked').map(function () {
            return $(this).data('value-id');  // Collect checked values
        }).get();
    
        const urlParams = new URLSearchParams(window.location.search);
    
        const form = $('<form>', {
            'action': `${window.location.pathname}`,
            'method': 'GET'
        });
    
        // Create an array for the updated list of attribute_variants
        let attributeVariants = urlParams.getAll('attribute_variants');  // Get all current attribute_variants
    
        // Append the checked variants to the form
        checkedValues.forEach(value => {
            // If the value isn't already in attributeVariants, add it
            if (!attributeVariants.includes(value)) {
                attributeVariants.push(value);  // Add checked variant
            }
        });
    
        // Now create a new set of attributeVariants excluding unchecked ones
        const newAttributeVariants = [];
    
        // Loop through the current `attribute_variants` in the URL
        attributeVariants.forEach(value => {
            // Only add to the new list if the value is in the checked list (i.e., it's still checked)
            if (checkedValues.includes(value)) {
                newAttributeVariants.push(value);
            }
        });
    
        // Now append the updated attributeVariants to the form
        newAttributeVariants.forEach(value => {
            form.append($('<input>', {
                'type': 'hidden',
                'name': 'attribute_variants',
                'value': value,
            }));
        });
    
        // Append other existing URL parameters
        urlParams.forEach((value, key) => {
            if (key !== 'attribute_variants') {
                form.append($('<input>', {
                    'type': 'hidden',
                    'name': key,
                    'value': value,
                }));
            }
        });
    
        // Submit the updated form
        $('body').append(form);
        form.submit();
    }
    




});

publicWidget.registry.ProductVariantAttributes = ProductVariantAttributes

