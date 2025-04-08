/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { jsonrpc } from "@web/core/network/rpc_service";
import { session } from '@web/session';
import wSaleUtils from "@website_sale/js/website_sale_utils";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";


export const MyWishlist = publicWidget.Widget.extend({
    selector: '.js_my_wishlist_page',  // Targeting the wishlist container
    events: {
        'change #select_all01': '_onSelectAllChange',
        'change .select-company': '_onSelectAllCompanyItems',
        'change .select-an-item': '_onIndividualProductSelect',
        'click .delete': '_deleteTargeted',
        'click .action-right': '_onRemoveSelected',
        'click .add-to-cart': '_onAddtoCart',
        // 'click .remove-wishlist': '_removeWishlist', 

    },

    init: function () {
        this._super.apply(this, arguments);
        this.isWebsite = true;
        this.screenSize = uiUtils.getSize();

        this.product_ids = [];
        this.selectedItems = [];
        this.rpc = this.bindService('rpc');
    },


    _onSelectAllChange: function (event) {
        var isChecked = $(event.target).prop('checked');
        this.$('.select-an-item').prop('checked', isChecked);
        this.$('.select-company').prop('checked', isChecked);
    },
    _onSelectAllCompanyItems: function (event) {
        var isChecked = $(event.target).prop('checked');
        var companySection = $(event.target).closest('.cart0-products1-item');
        companySection.find('.select-an-item').prop('checked', isChecked);
    },
    _onIndividualProductSelect: function () {
        var allItems = this.$('.select-an-item');
        var totalItems = allItems.length;
        var selectedItems = allItems.filter(':checked').length;

        // Check if all products are selected
        var isAllSelected = selectedItems === totalItems;

        // Update the "Select Everything" checkbox based on whether all products are selected
        this.$('#select_all01').prop('checked', isAllSelected);

        // Update the individual company "Select All" checkboxes based on the selected products in each company section
        this.$('.select-company').each(function () {
            var companySection = $(this).closest('.cart0-products1-item');
            var companyItems = companySection.find('.select-an-item');
            var selectedCompanyItems = companyItems.filter(':checked').length;

            // If all products in the company are selected, check the company "Select All" checkbox
            $(this).prop('checked', selectedCompanyItems === companyItems.length);
        });
    },




    _onRemoveSelected: function () {
        var selectedItems = this.$('.select-an-item:checked');

        if (selectedItems.length === 0) {
            alert(_t('Please select items to remove.'));
            return;
        }


        var wishlistIds = selectedItems.map(function (index, checkbox) {
            return $(checkbox).data('wishlist-id');
        }).get();


        selectedItems.each(async (index, checkbox) => {
            var productItem = $(checkbox).closest('.cart0prd');
            var wishlistId = $(checkbox).data('wishlist-id');
            var productID = $(checkbox).data('product-id');
            var product_name = $(checkbox).data('product-name');

            jsonrpc('/remove_from_wishlist', {
                params: {
                    wishlist_ids: wishlistIds
                }
            }).then((res) => {
                if (res) {
                    selectedItems.each(function () {
                        var productItem = $(this).closest('.cart0prd');
                        productItem.remove();
                    });
                    location.reload();
                }
            }).catch((error) => {
                console.error('Error fetching total sold:', error);
                alert(_t('An error occurred while fetching data from the server.'));
            });

        });
    },

    _deleteTargeted: function (ev) {
        const target = this.$(ev.target).closest('.delete').data('wishlist-id');
        const form = {
            type: 'wishlist',
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
                this._updateWishlistView(data.data_count)

            } else {
                const props = {
                    'success': false,
                    'message': _t("Ohh well, something went wrong because ") + ' ' + data.message,
                }
                myUtils.sweetCartNotification(this.call.bind(this), props)
            }
        })

    },
    _updateWishlistView: function (length) {
        const $wishButton = $('.o_wsale_my_wish');
        if ($wishButton.hasClass('o_wsale_my_wish_hide_empty')) {
            $wishButton.toggleClass('d-none', !length);
        }
        $wishButton.find('.my_wish_quantity').text(length);
    },



    _onAddtoCart: function (ev) {
        if (session.user_id) {
            let id_for_product = $(ev.target).closest('.addto_cart').data('wishlist-id');
            console.log("this.product_id", id_for_product);
            jsonrpc("/wishlist_to_cart", {
                params: {
                    wishlist_id: parseInt(id_for_product),
                }
            }).then((data) => {
                console.log('datadasa',data);
                
                if (data.success) {
                    this.$('.js_render_target_wrapper').html(data.refresh_template)
                    const props = {
                        'message': data.message,
                        'cart_quantity': data.cart_quantity,

                    }
                    wSaleUtils.updateCartNavBar(props);
                    myUtils.sweetSuccessNotification(this.call.bind(this), props)

                }
                else {
                    myUtils.sweetCartNotification(this.call.bind(this), {
                        'success': false,
                        'message': data.message,
                    })

                }
                // location.reload();
            });

        } else {
            this._toggleModal('loginModal');
        }
    },

    // _getProduct: function (ev) {
    //     console.log("HEr in _getProduct")
    //     this.product_id = $(ev.target).closest('i').data('wishlist-id');
    //     console.log("this.product_id",this.product_id);
    //     return this.product_id;
    // },


    // _removeWishlist: function (ev) {
    //     if (session.user_id) {
    //         this.product_id = $(ev.target).closest('i').data('wishlist-id');
    //         console.log("this.product_id @@",this.product_id);
    //     }
    // },


});

publicWidget.registry.MyWishlist = MyWishlist;