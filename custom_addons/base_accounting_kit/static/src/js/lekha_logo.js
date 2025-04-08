odoo.define('lekha.website_logo',[] ,async function(require){
    "use strict";
	// var core = require('web.core');
	// var ajax = require('web.ajax');
	// var rpc = require('web.rpc');
	// var QWeb = core.qweb;
	// var _t = core._t;

    let url = window.origin,palika_name='Lekha+',palika_type='';
    if(url.toLowerCase().includes('lekhaplus.com')){
        palika_name = 'लेखा+';
        palika_type = ' ';
    }
    
    let logo_container = document.getElementById('website_company_logo');   
    let p = document.createElement('p')
    p.innerHTML = palika_type
    logo_container.children[0].children[0].innerHTML = palika_name
    logo_container.children[0].append(p)

})