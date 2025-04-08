/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/libs/zoomodoo/zoomodoo";
import { jsonrpc } from "@web/core/network/rpc_service";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { session } from '@web/session';
import { loadJS } from "@web/core/assets";
import myUtils from "@base_accounting_kit/js/ecommerce/utils/ecommerceUtils";
export const ProductsSearch = publicWidget.Widget.extend({
    selector: '.js_searchbar',
    events: {
        'input input.search-bar': '_showRecommendations',
        'focus input.search-bar': '_showRecommendations',
        'click document': '__addOutsideClickHandler',
        'input input.max_price': '_onValidateNumberInput',
        'change  input.min_price': '_onApplyPriceChange',
        'change  input.max_price': '_onApplyPriceChange',
        'click  button#price_filter': '_onSubmitPriceRangeFilter',
        'click  a.search_activity': '_userActivitySearch',
        'submit  form#product_search_form': '_productSearchFormSubmitActivity',
        'submit  form#product_search_global_form': '_productSearchFormSubmitGlobalActivity',


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

    _showRecommendations: function (ev) {
        if (ev.target.value.length > 0) {
            let search = {
                keywords: ev.target.value
            };
            let url = '/products?q=';
            if ($('#vendor_search').length > 0) {
                search = {
                    keywords: ev.target.value,
                    vendor: $('#vendor_search').data('vendor-id')
                };
                url = `/products?vendor=${$('#vendor_search').data('company-slug')}&q=`;
            }

            this.rpc(`/products/searchbar`, search).then((data) => {
                try {
                    this.results = '';
                    this.$('ul.searchbar_results').html('');
                    this.$('.search-recommendations-container').removeClass('d-none');

                    if (data.products.length > 0) {
                        data.products.forEach(element => {
                            this.results += `<li><a class="search_activity" data-search-query="${element.product_name}" href='${url}${encodeURIComponent(element.product_name)}'>${element.product_name}<i class="fa fa-search" aria-hidden="true"></i></a></li>`;
                        });
                        this.$('ul.searchbar_results').html(this.results + `<li  class="text-center"><a class="text-center query-all search_activity" data-search-query="${ev.target.value}" href="${url}${encodeURIComponent(ev.target.value)}">${_t('See all')}</a></li>`);
                    }
                    else {
                        this.$('ul.searchbar_results').html(`<li class="text-center">${_t('No results found!')}</li>`);

                    }
                    this._addOutsideClickHandler();

                }
                catch (e) {
                    this.$('ul.searchbar_results').html(`<li class="text-center">${_t('Error processing results')}</li>`);
                }

            }).catch((e) => {
                this.$('ul.searchbar_results').html(`<li class="text-center">${_t('An error occurred while fetching products. Please try again.')}</li>`);

            });

        } else {
            this._closeRecommendations();
        }


    },

    _closeRecommendations: function () {
        this.$('.search-recommendations-container').addClass('d-none');
    },

    _addOutsideClickHandler: function () {
        this._outsideClickHandler = (event) => {
            const recommendationsContainer = this.$('.search-recommendations-container');
            if (!recommendationsContainer[0].contains(event.target) && !this.$('.search-bar')[0].contains(event.target) && !this.$('.search-btn')[0].contains(event.target)) {
                this._closeRecommendations();
            }
        };

        document.addEventListener('click', this._outsideClickHandler);
    },

    _userActivitySearch: function (e) {
        let activity_details = {};
        if (session.user_id) {

            activity_details = {
                "search_query": this.$(e.target).closest('a').data('search-query'),
                "activity_type": "search",
                "user_id": session.user_id,
            }

        }
        else {
            activity_details = {
                "search_query": this.$(e.target).closest('a').data('search-query'),
                "activity_type": "search",
                "session_id": this.getSessionId(),
            }

        }
        this.rpc("/create_user_activity", activity_details);

    },
    _productSearchFormSubmitActivity: function (e) {
        e.preventDefault();
        let activity_details = {};
        if (session.user_id) {

            activity_details = {
                "search_query": this.$('.search-bar').val(),
                "activity_type": "search",
                "user_id": session.user_id,


            }

        }
        else {
            activity_details = {
                "search_query": this.$('product_search_form .search-bar').val(),
                "activity_type": "search",
                "session_id": this.getSessionId(),
            }

        }
        this.rpc("/create_user_activity", activity_details).then((data) => {
            this.$('#product_search_form')[0].submit();
        })
        
    },
    _productSearchFormSubmitGlobalActivity: function (e) {
        e.preventDefault();
        let activity_details = {};
        if (session.user_id) {

            activity_details = {
                "search_query": this.$('#product_search_global_form .search-bar').val(),
                "activity_type": "search",
                "user_id": session.user_id,


            }

        }
        else {
            activity_details = {
                "search_query": this.$('#product_search_global_form .search-bar').val(),
                "activity_type": "search",
                "session_id": this.getSessionId(),
            }

        }
        this.rpc("/create_user_activity", activity_details).then((data) => {
            this.$('#product_search_global_form')[0].submit();
        })
        
    },

    getSessionId() {
        let sessionId = localStorage.getItem("guest_session_id");
        if (!sessionId) {
            sessionId = "guest_" + Math.random().toString(36).slice(2, 11);
            localStorage.setItem("guest_session_id", sessionId);
        }
        return sessionId;
    }



});

publicWidget.registry.ProductsSearch = ProductsSearch;





/***
 * 
 *  Main JS
 * 
 * 
 * /***/

export const AllProductsLayout = publicWidget.Widget.extend({
    selector: '.js_all_products',
    events: {
        'click button#layout_grid': '_changeLayoutCols',
        'click button#layout_grid_columns': '_changeLayoutRows',
        'click a.sort-by-item': '_onSubmitProductFilter',
        'change  input.min_price': '_onApplyPriceChange',
        'change  input.max_price': '_onApplyPriceChange',
        'click  button#price_filter': '_onSubmitProductFilter',
        'click  a.product_link': '_userActivityView',
        'click  span.products_page_add_to_wishlist': '_addToWishlist',
    },

    init: function () {
        this._super.apply(this, arguments);

        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        this.isLayoutRows = true;

        this.maxLength = 50;
        this.rpc = this.bindService("rpc");
        loadJS('https://cdn.jsdelivr.net/npm/sweetalert2@11');

    },

    start: function () {
        this.product_title = this.$('.product-title');
        // this.maxLength=100;
        // if (this.product_title.length) {
        //     this._truncate_title();
        // }



    },

    _changeLayoutCols: function (ev) {
        this.$('.products').removeClass('grid');
        this.$('.product-details').addClass('d-none');
        this.maxLength = 50;
        this._truncate_title();
        this._change_product_layout(ev);



    },
    _changeLayoutRows: function (ev) {
        this.$('.products').addClass('grid');
        this.$('.product-details').removeClass('d-none');

        this.maxLength = 200;
        this._truncate_title();

        this._change_product_layout(ev);

    },

    _truncate_title: function () {
        if (uiUtils.getSize() >= SIZES.SM) {
            $('.toggle_summary_div').addClass('d-none d-xl-block');
            this.$('.product-title').toArray().forEach((e) => {
                this.product_title_value = $(e).data('product-name');
                this.truncatedName = this.product_title_value.length > this.maxLength
                    ? this.product_title_value.slice(0, this.maxLength) + '...'
                    : this.product_title_value;
                $(e).html(this.truncatedName);
            });
        };



    },

    _change_product_layout: function (ev) {

        var clickedValue = $(ev.target).data('layout-mode');
        var isList = clickedValue === 'list';
        jsonrpc('/shop/save_shop_layout_mode', {
            'layout_mode': isList ? 'list' : 'grid',
        });
        isList ? $('#layout_grid_columns').addClass('focused') && $('#layout_grid').removeClass('focused') : $('#layout_grid').addClass('focused') && $('#layout_grid_columns').removeClass('focused');


    },

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyPriceChange: function (ev) {
        var maxPrice = 0;
        var minPrice = 0;
        var priceRange = this.$('#price_range');

        if (uiUtils.getSize() >= 4) {
            maxPrice = $('#max_price_lg').val();
            minPrice = $('#min_price_lg').val();

        }
        else {
            maxPrice = $('#max_price_sm').val();
            minPrice = $('#min_price_sm').val();
        }

        if (minPrice == '' && maxPrice == '') {
            priceRange.val(``);

        }
        else {

            priceRange.val(`${minPrice}-${maxPrice}`);
        }


    },



    _onSubmitProductFilter: function (ev, type = 'sort_by') {
        // const form = $('<form>', {
        //     'action': `${window.location.href}`,
        //     'method': 'GET'
        // });

        if (this.$(ev.target).data('attr-value') == 'sort_by') {
            this.$('#sort_by_value').val(this.$(ev.target).data('sort-value'))
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.delete('sort_by');
            currentUrl.searchParams.append('sort_by', this.$('#sort_by_value').val());
            window.location.href = currentUrl.toString();
        }

        if (this.$(ev.currentTarget).data('attr-value') == 'price_range') {
            if ($('#price_range').val() !== '') {
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.delete('price');
                currentUrl.searchParams.append('price', this.$('#price_range').val());
                window.location.href = currentUrl.toString();
            }

        }

    },

    _userActivityView: function (e) {
        let activity_details = {};
        if (session.user_id) {

            activity_details = {
                "product_id": this.$(e.target).closest('a').data('product-id'),
                "activity_type": "view",
                "user_id": session.user_id,


            }

        }
        else {
            activity_details = {
                "product_id": this.$(e.target).closest('a').data('product-id'),
                "activity_type": "view",
                "session_id": this.getSessionId(),


            }

        }
        this.rpc("/create_user_activity", activity_details);

    },
    _addToWishlist: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var productId = $(event.currentTarget).find('.add-to-wishlist').data('product-id');
        if (session.user_id) {
            this.rpc("/add-to-wishlist-products", {
                product_id: parseInt(productId),
                user_id: parseInt(session.user_id),
            }).then((data) => {
                if (data && data.success) {
                    const wishlistIcon = $(event.currentTarget).find('.add-to-wishlist');
                    if (wishlistIcon.length) {
                        wishlistIcon.removeClass('fa-regular').addClass('fa-solid added');
                    }
                    // this.$('.js_wishlist_wrapper').html(data.wishlist_template);

                    myUtils.alert('toast',data.message, 'success','')
                    this._updateWishlistView(data.wishlist_count);

                }
                if (data && !data.success) {
                    myUtils.alert('toast','', 'error', data.message)
                }

            });

        } else {
            $(`#loginModal`).modal('show');
        }


    },
    _updateWishlistView: function (length) {
        const $wishButton = $('.o_wsale_my_wish');
        if ($wishButton.hasClass('o_wsale_my_wish_hide_empty')) {
            $wishButton.toggleClass('d-none', !length);
        }
        $wishButton.find('.my_wish_quantity').text(length);
    },


    getSessionId() {
        let sessionId = localStorage.getItem("guest_session_id");
        if (!sessionId) {
            sessionId = "guest_" + Math.random().toString(36).slice(2, 11);
            localStorage.setItem("guest_session_id", sessionId);
        }
        return sessionId;
    }









});
publicWidget.registry.AllProductsLayout = AllProductsLayout;





/****
 * 
 * 
 * Product->Product Hero
 * 
 */

export const ProductImageZoom = publicWidget.Widget.extend({
    selector: '.js_product_image_zoom',
    events: {
        'click .featured-img img': '_makeMainImage',
        'mouseover .featured-img img': '_makeMainImage',
        'click .js_prev_content': '_gotoPreviousImage',
        'click .js_next_content': '_gotoNextImage',
    },

    init: function () {
        this._super.apply(this, arguments);

        this.rpc = this.bindService("rpc");
        this.scrollAmount = 60;
    },

    // start: function () {



    // },


    _makeMainImage: function (ev) {
        const currentlyActive = this.$('.featured-img .active');

        const clickedImage = this.$(ev.target);

        if (!clickedImage.is(currentlyActive)) {
            currentlyActive.removeClass('active');
            clickedImage.addClass('active');
            const closestImg = clickedImage.closest('img');
            this.$('.js_featured_main_img_spotlight_holder').attr('href', closestImg.attr('src'))

            this.$('.main-featured-img img').attr('src', closestImg.attr('src'));
        }


    },
    _gotoPreviousImage: function (ev) {
        let $currentlyActive = this.$('.featured-img .active');
        let $prevImageSlide = $currentlyActive.closest('.splide__slide').prev();
        let $img = $prevImageSlide.find('img');

        if ($img.length > 0) {

            $currentlyActive.removeClass('active');
            $img.addClass('active');
            let imgSrc = $img.attr('src');
            let $mainImg = this.$('.main-featured-img img');

            $mainImg.fadeOut(200, function () {
                $mainImg.attr('src', imgSrc).fadeIn(300);
            });

            this.$('.js_featured_main_img_spotlight_holder').attr('href', imgSrc);
        }
    },

    _gotoNextImage: function (ev) {
        let $currentlyActive = this.$('.featured-img .active');
        let $nextImageSlide = $currentlyActive.closest('.splide__slide').next();
        let $img = $nextImageSlide.find('img');

        if ($img.length > 0) {
            $currentlyActive.removeClass('active');
            $img.addClass('active');

            let imgSrc = $img.attr('src');
            let $mainImg = this.$('.main-featured-img img');

            $mainImg.fadeOut(200, function () {
                $mainImg.attr('src', imgSrc).fadeIn(300);
            });

            this.$('.js_featured_main_img_spotlight_holder').attr('href', imgSrc);
        }
    },



});

publicWidget.registry.ProductImageZoom = ProductImageZoom;
