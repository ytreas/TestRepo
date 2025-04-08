document.addEventListener( 'DOMContentLoaded', function () {
   if($('#thumbnail-carousel .splide__slide').length){
      new Splide( '#thumbnail-carousel', {
            fixedWidth: 100,
            gap       : 2,
            rewind    : false,
            pagination: false,
      } ).mount();
   }

   if($('#r-products-carousel .splide__slide').length){
      new Splide( '#r-products-carousel', {
            fixedWidth: 200,
            autoHeight:false,
            gap       : 2,
            rewind    : false,
            pagination: false,
      } ).mount();
   }

   //  $('.arrt-select').niceSelect();



  } );
  