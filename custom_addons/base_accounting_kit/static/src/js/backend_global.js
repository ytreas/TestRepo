function changeFavicon(url) {
    let link = document.querySelector("link[type='image/x-icon']");
    link.href = url;
}

// function changeTitle(){
//     let title_val = document.querySelector("title");  
//     title_val=title_val.innerHTML;
//     console.log('before',title_val);
    
//     title_val = title_val.replace(/Odoo/i, "Lekha+"); 
//     console.log('after',title_val);
//     setTimeout(() => {
//         document.title = title_val;
//         console.log(document.title);
        
//     }, 5000);
// }


// changeTitle();
changeFavicon('/base_accounting_kit/static/images/logo.jpg');