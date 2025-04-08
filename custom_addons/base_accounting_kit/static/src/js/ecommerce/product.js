/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import wSaleUtils from "@website_sale/js/website_sale_utils";
import { listenSizeChange, SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { session } from '@web/session';
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
import { jsonrpc } from "@web/core/network/rpc_service";


export const ProductPage = publicWidget.Widget.extend({
    selector: '.product-page',
    events: {
        'input input.input-quantity': '_onValidateNumberInput',
        'focusout input.input-quantity': '_onValidateNumberInputOnFocusout',
        'click .btn-dec': '_decreaseQuantity',
        'click .btn-inc': '_increaseQuantity',
        'click .show-more-btn': '_showMoreDescription',
        'click .add-to-wishlist': '_addToWishlist',
        'click .add-to-cart': '_addToCart',
        'click .buy-now': '_expressBuyNow',
        'click #close_share_btn': '_closeShareWrapper',
        'click #open_share_wrapper': '_openShareWrapper',
        'click .share-to-backdrop': '_closeShareWrapper',
        'change .arrt-select': '_fetchInitialProductAttributes',


    },
    init: function () {
        this._super.apply(this, arguments);


        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        this.product_id = null;
        this.p_quantity = null;
        this.unit_price = null;
        this.product_attribute_ids = null;
        this.user_id = null;

        this.rpc = this.bindService("rpc");
        this.screenSize = uiUtils.getSize();
        this.p_min_qty = 0
        this.p_max_qty = 0


    },

    start: function () {
        const descriptionContainer = this.$('.pdr .product-description');
        const showMore = this.$('.show-more-btn');
        if (descriptionContainer[0].scrollHeight > descriptionContainer.outerHeight() + 10) {
            showMore.removeClass('d-none');
        } else {
            showMore.addClass('d-none');
        }

        this._fetchInitialProductAttributes();


    },
    _closeShareWrapper: function (ev) {
        $('.share-to-backdrop').removeClass('show');
        $('.share-to-wrapper').removeClass('show');
    },
    _openShareWrapper: function (ev) {
        $('.share-to-backdrop').addClass('show');
        $('.share-to-wrapper').addClass('show');
    },
    _toggleModal: function (id) {
        $(`#${id}`).modal('show');
    },

    _onValidateNumberInput: function (ev) {
        const inputField = ev.target;
        let value = $(inputField).val();
        const maxVal = parseInt($('#max_qty').data('val'), 10);

        value = value.replace(/[^\d]/g, '');

        if (parseInt(value, 10) < 1) {
            value = '1';
        }

        if (maxVal && parseInt(value, 10) > maxVal) {
            value = maxVal.toString();
        }
        inputField.value = value;
    },
    _onValidateNumberInputOnFocusout: function (ev) {
        const inputField = ev.target;
        let value = $(inputField).val();
        let minVal = $(inputField).data('min-qty');
        minVal = parseInt(minVal, 10);

        if (value < parseInt(minVal)) {
            value = value = minVal.toString();

        }

        inputField.value = value;
    },

    _decreaseQuantity: function (ev) {
        let inputQuantityInput = this.$('.input-quantity');
        let inputQuantity = inputQuantityInput.val();
        const min_qty = $(inputQuantityInput).data('min-qty');
        if (inputQuantity > parseInt(min_qty) && inputQuantity != '') {
            this.$('.input-quantity').val(this.$('.input-quantity').val() - 1);

        }

    },
    _increaseQuantity: function (ev) {
        let inputQuantity = this.$('.input-quantity').val();
        if (inputQuantity < parseInt(this.$('#max_qty').data('val'), 10)) {
            if (inputQuantity == '') {
                this.$('.input-quantity').val(0);
                this.$('.input-quantity').val(parseInt(this.$('.input-quantity').val()) + 1);
            }
            else {
                this.$('.input-quantity').val(parseInt(this.$('.input-quantity').val()) + 1);

            }
        }

    },

    _showMoreDescription: function (ev) {
        this.$('.pdr .product-description').toggleClass('expanded');
        const isExpanded = this.$('.pdr .product-description').hasClass('expanded');
        this.$('.show-more-btn').text(isExpanded ? 'Show Less' : 'Show More');
    },
    _addToWishlist: function (ev) {
        if (session.user_id) {
            this._getProduct();
            this.rpc("/add-to-wishlist", {
                product_id: parseInt(this.product_id),
                qty: parseInt(this.p_quantity),
                attr: this.product_attribute_ids,
                user_id: parseInt(this.user_id),
                unit_price: parseFloat(this.unit_price),

            }).then((data) => {
                if (data && data.success) {
                    const wishlistIcon = this.$('i.add-to-wishlist');
                    if (wishlistIcon.length) {
                        wishlistIcon.removeClass('fa-regular').addClass('fa-solid added');
                    }
                    this.$('.js_wishlist_wrapper').html(data.wishlist_template);

                    myUtils.sweetSuccessNotification(this.call.bind(this), { 'message': data.item + ' ' + _t("added to your wishlist.") })
                    this._updateWishlistView(data.wishlist_count);

                }
                if (data && !data.success) {
                    const props = {
                        'success': data.success,
                        'message': data.message,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)

                }

            });

        } else {
            this._toggleModal('loginModal');
        }
    },
    _expressBuyNow: function (ev) {
        ev.preventDefault();
        if (session.user_id) {
            this._getProduct();
            this.rpc("/add-to-cart", {
                product_id: parseInt(this.product_id),
                qty: parseInt(this.p_quantity),
                attr: this.product_attribute_ids,
                user_id: parseInt(this.user_id),
                unit_price: parseFloat(this.unit_price),

            }).then((data) => {
                if (data && data.success) {
                    let cart_id = [{
                        cart_id: data.cart_id,
                    }]
                    this.$('#item_id').val(JSON.stringify(cart_id));
                    this._buyNow();
                }
                if (data && !data.success) {

                    const props = {
                        'success': false,
                        'message': _t('Something went wrong, Please try again later.') + data.message,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)
                }

            });
        }
        else {
            this._toggleModal('loginModal');

        }
    },
    _buyNow: function (ev) {
        if (document.getElementById('instant_buy__form').checkValidity()) {
            $('#t_amt').val(this.unit_price)
            $('#instant_buy__form').submit();
        }
        else {
            const props = {
                'success': false,
                'message': _t('Something went wrong, Please try again later.'),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        }
    },


    _addToCart: function (ev) {
        if (session.user_id) {
            this._getProduct();

            this.rpc("/add-to-cart", {
                product_id: parseInt(this.product_id),
                qty: parseInt(this.p_quantity),
                attr: this.product_attribute_ids,
                user_id: parseInt(this.user_id),
                unit_price: parseFloat(this.unit_price),

            }).then((data) => {
                if (data && data.success) {
                    this._userActivityAddToCart(parseInt(this.product_id), parseInt(this.user_id))
                    wSaleUtils.updateCartNavBar(data);
                    const props = {
                        'success': data.success,
                        'id': data.cart_id,
                        'image_url': data.image_url,
                        'quantity': data.individual_qty,
                        'name': data.name,
                        'description': '',
                        'price_total': data.price_total,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)


                }
                if (data && !data.success) {
                    const props = {
                        'success': data.success,
                        'message': data.message,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)

                }

            });




        } else {
            this._toggleModal('loginModal');
        }
    },

    _userActivityAddToCart: function (product_id, user_id) {
        let activity_details = {};
        activity_details = {
            "product_id": product_id,
            "activity_type": "cart",
            "user_id": user_id,
        }

        this.rpc("/create_user_activity", activity_details);

    },

    _getProduct: function (ev) {
        this.product_id = this.$('#product_id').data('value');
        this.p_quantity = this.$('#p_quantity').val();
        this.unit_price = this.$('#product_unit_price').val();
        let selectedValues = [];
        this.$('.arrt-select').each(function () {
            let values = $(this).val();
            if (values) {
                selectedValues = selectedValues.concat(values);
            }
        });
        this.product_attribute_ids = selectedValues;
        this.user_id = session.user_id;
    },

    _updateWishlistView: function (length) {
        const $wishButton = $('.o_wsale_my_wish');
        if ($wishButton.hasClass('o_wsale_my_wish_hide_empty')) {
            $wishButton.toggleClass('d-none', !length);
        }
        $wishButton.find('.my_wish_quantity').text(length);
    },


    _fetchInitialProductAttributes: function (ev) {
        this._getProduct();
        this.product_id = this.$('#product_id').data('value');
        const formData = {
            product_attributes: this.product_attribute_ids,
            vendor_product_id: this.product_id
        };

        this.rpc('/get_product_attributes_extra_info', formData).then((data) => {

            if (data.success) {
                this.unit_price = data.product_total_price
                this.$('#product_unit_price').val(data.product_total_price)
                this.$('#price_sell').text(data.product_total_price)
                this.$('.buy-add-cart').removeClass('d-none');

            }
            else {
                console.error(data.message);

            }


        });

    },
});






publicWidget.registry.ProductPage = ProductPage;

export const MyCart = publicWidget.Widget.extend({
    selector: '.my-cart-page',
    events: {
        'input input.input-quantity': '_onValidateNumberInput',
        'click .btn-dec': '_decreaseQuantity',
        'click .btn-inc': '_increaseQuantity',
        'change .select-an-item': '_calculateCheckedItems',
        'click .proceed_btn': '_handleProceedToPayment',

        'change #select_all0': '_onSelectAllChange',
        'change .select-company': '_onSelectAllCompanyItems',
        'change .select-an-item': '_onIndividualProductSelect',
        'click .js_btn_rm_cart': '_deleteTargeted',
        'click .action-delete': '_onRemoveSelected',
        'click .add-to-wishlist': '_onAddtoWishlist',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;


        this.cart_id = null;
        this.qty = null;

        this.product_id = null;
        this.p_quantity = null;
        this.unit_price = null;
        this.unit_price = null;
        this.product_attribute_ids = null;
        this.user_id = null;


        this.rpc = this.bindService("rpc");

    },

    _onValidateNumberInput: function (ev) {
        const inputField = ev.target;
        let value = inputField.value;
        const maxVal = parseInt($('#max_qty').data('val'), 10);

        value = value.replace(/[^\d]/g, '');

        if (parseInt(value, 10) < 1) {
            value = '1';
        }

        if (maxVal && parseInt(value, 10) > maxVal) {
            value = maxVal.toString();
        }

        inputField.value = value;
        if (inputField.value > 0) {
            this.cart_id = parseInt($(ev.target).data('cart-id'));
            this.qty = inputField.value;
            this._update_cart_on_input(ev);
        }

    },

    _decreaseQuantity: function (ev) {
        let $target = this.$(ev.currentTarget);
        let $inputElement = $target.closest('.js_product_quantity').find('.input-quantity');
        let inputQuantity = parseInt($inputElement.val(), 10) || 0;
        if (inputQuantity > 1) {
            $inputElement.val(inputQuantity - 1);
            this._update_cart(ev);

        }

    },

    _increaseQuantity: function (ev) {
        let $target = this.$(ev.currentTarget);
        let $inputElement = $target.closest('.js_product_quantity').find('.input-quantity');
        let inputQuantity = parseInt($inputElement.val(), 10) || 0;
        $inputElement.val(inputQuantity + 1);
        this._update_cart(ev);

    },
    _update_cart: function (ev) {
        let $target = this.$(ev.currentTarget);
        this.cart_id = $target.data('cart');
        let $qty = $target.closest('.quantity').find('.input-quantity');
        this.qty = parseInt($qty.val(), 10) || 0;

        // Update checkbox attributes values     
        let checkBoxAttr = $target;

        this._update_cart_rpc(ev);


    },
    _update_cart_on_input: function (ev) {
        setTimeout(() => {
            this._update_cart_rpc(ev);
        }, 1000);


    },

    _update_cart_rpc: function (ev) {
        this._calculateCheckedItems();

        this.rpc("/update-cart", {
            cart_id: parseInt(this.cart_id),
            qty: parseInt(this.qty),
            user_id: session.user_id,

        }).then((data) => {
            if (data.success) {
                wSaleUtils.updateCartNavBar(data);
            }
            else {
                const props = {
                    'success': false,
                    'message': data, message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }


        }).catch((err) => {
            const props = {
                'success': false,
                'message': _t('Cannot not update the cart due to', err),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        })
    },

    _calculateCheckedItems: function (ev) {
        let totalItemCount = 0;
        let totalPrice = 0;
        let my_orders = [];

        let checkedItems = this.$('.select-an-item:checked');
        checkedItems.each((index, checkbox) => {
            let inputQuantity = $(checkbox).parent().siblings('.js_product_quantity').find('.input-quantity');
            const itemCount = parseInt(inputQuantity.val()) || 0;
            const perUnitPrice = parseFloat($(checkbox).data('per-unit-price')) || 0;
            const cartId = $(checkbox).data('cart-id');
            totalItemCount += itemCount;
            totalPrice += itemCount * perUnitPrice;
            my_orders.push({
                cart_id: cartId,
            });
        });
        this.$('#my_orders').val(JSON.stringify(my_orders));

        this._calculateSubTotal(totalItemCount, totalPrice);

    },


    _calculateSubTotal: function (totalItemCount, totalPrice) {
        this.$('#odc_item_count').text(totalItemCount);
        this.$('#odc_item_price').text(this._priceFormatter(totalPrice.toFixed(2)));

        // Total price
        let shipping_fee = parseInt(this.$('#odc_shipping_price').text());
        let total_fee = totalPrice + shipping_fee;
        this.$('#odc_total_price').text(this._priceFormatter(total_fee.toFixed(2)));

        this.$('#checkout_qty').text(totalItemCount);


        // Form Data
        this.$('#t_amt').val(total_fee.toFixed(2));




    },

    _deleteTargeted: function (ev) {
        const target = this.$(ev.target).closest('.delete').data('cart-rm-id');
        const form = {
            type: 'cart',
            id: parseInt(target),

        }

        const targetItemName = this.$(ev.target).closest('.delete').data('item-title');
        this.rpc('/unlink_data', form).then((data) => {
            if (data.success) {
                this.$('.js_render_target_wrapper').html(data.data)
                const props = {
                    'message': targetItemName + ' ' + _t(" is removed.")
                }
                myUtils.sweetSuccessNotification(this.call.bind(this), props)
                const nav_data = {
                    "success": true,
                    "cart_quantity": data.cart_quantity,
                    "message": "Cart Updated Successfully!",
                }
                wSaleUtils.updateCartNavBar(nav_data);

            } else {
                const props = {
                    'success': false,
                    'message': _t("Ohh well, something went wrong because ") + ' ' + data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }
        })

    },


    _priceFormatter: function (amount) {
        let [integerPart, fractionalPart] = amount.split('.');

        let reversed = integerPart.split('').reverse();
        let formatted = [];

        for (let i = 0; i < reversed.length; i++) {
            if (i > 3 && (i - 3) % 2 === 0) {
                formatted.push(',');
            } else if (i > 0 && i <= 3 && i % 3 === 0) {
                formatted.push(',');
            }
            formatted.push(reversed[i]);
        }

        let formattedInteger = formatted.reverse().join('');

        return formattedInteger + '.' + fractionalPart;
    },

    _handleProceedToPayment: function (ev) {
        ev.preventDefault();
        this.$('#voucher').val(this.$('#my_voucher').val());
        if (this.$('#t_amt').val() !== '' && this.$('#t_amt').val() !== null && this.$('#t_amt').val() > 0) {
            this.$('form.proceed_to_payment_form').submit();
        }
        else {
            const props = {
                'success': false,
                'message': _t("Please select at least one item to continue."),
            }
            myUtils.sweetCartNotification(this.call.bind(this), props)
        }
    },

    _onSelectAllChange: function (event) {
        var isChecked = $(event.target).prop('checked');
        this.$('.select-an-item').prop('checked', isChecked);
        this.$('.select-company').prop('checked', isChecked);
        this._calculateCheckedItems();


    },


    _onSelectAllCompanyItems: function (event) {

        var isChecked = $(event.target).prop('checked');
        var companySection = $(event.target).closest('.cart0-products1-item');

        companySection.find('.select-an-item').prop('checked', isChecked);
        this._calculateCheckedItems();

    },

    _onIndividualProductSelect: function () {
        var allItems = this.$('.select-an-item');
        var totalItems = allItems.length;
        var selectedItems = allItems.filter(':checked').length;


        var isAllSelected = selectedItems === totalItems;

        this.$('#select_all0').prop('checked', isAllSelected);

        this.$('.select-company').each(function () {
            var companySection = $(this).closest('.cart0-products1-item');
            var companyItems = companySection.find('.select-an-item');
            var selectedCompanyItems = companyItems.filter(':checked').length;

            $(this).prop('checked', selectedCompanyItems === companyItems.length);
        });
        this._calculateCheckedItems();
    },




    _onRemoveSelected: function () {
        var selectedItems = this.$('.select-an-item:checked');
        if (selectedItems.length === 0) {
            myUtils.sweetCartNotification(this.call.bind(this), {
                'success': false,
                'message': _t('Please select an item to remove.')

            })
            return;
        }
        var cartIds = selectedItems.map(function (index, checkbox) {
            return $(checkbox).data('cart-id');
        }).get();

        this.rpc('/remove_from_cart', {
            params: {
                cart_ids: cartIds
            }
        }).then((res) => {
            if (res.success) {
                this.$('.js_render_target_wrapper').html(res.refresh_template)
                const props = {
                    'message': _t('Item/s removed successfully.')
                }
                myUtils.sweetSuccessNotification(this.call.bind(this), props)
                const nav_data = {
                    "success": true,
                    "cart_quantity": res.cart_quantity,
                    "message": "Cart Updated Successfully!",
                }
                wSaleUtils.updateCartNavBar(nav_data);


            }
            else {
                myUtils.sweetCartNotification(this.call.bind(this), {
                    'success': false,
                    'message': res.message

                })
            }
        }).catch((error) => {
            console.error('Error', error.message);
            alert(_t('An error occurred while fetching data from the server.'));
        });

    },



    _onAddtoWishlist: function (ev) {
        if (session.user_id) {
            let id_for_product = this._getProduct(ev);
            this.rpc("/cart_to_wishlist", {
                cart_id: parseInt(id_for_product),

            }).then((data) => {
                if (data.success) {
                    myUtils.sweetSuccessNotification(this.call.bind(this), { 'message': data.data })
                    this._updateWishlistView(data.len)
                }
                else {
                    const props = {
                        'success': false,
                        'message': data.message,
                    }
                    myUtils.sweetCartNotification(this.call.bind(this), props)
                }
            });

        } else {
            this._toggleModal('loginModal');
        }
    },
    _getProduct: function (ev) {
        this.product_id = $(ev.target).closest('i').data('wishlist-id');
        return this.product_id;
    },
    _updateWishlistView: function (length) {
        const $wishButton = $('.o_wsale_my_wish');
        if ($wishButton.hasClass('o_wsale_my_wish_hide_empty')) {
            $wishButton.toggleClass('d-none', !length);
        }
        $wishButton.find('.my_wish_quantity').text(length);
    },


});

publicWidget.registry.MyCart = MyCart;
