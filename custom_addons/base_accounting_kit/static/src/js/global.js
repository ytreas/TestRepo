let element = document.querySelector('[title="odoo"]');
if (element !== null) {
    element.href = "https://shangrila.com.np/"
    element.setAttribute('title', 'Shangrila Microsystems Pvt. Ltd.')

}

function changeFavicon(url) {
    let link = document.querySelector("link[type='image/x-icon']");
    link.href = url;
}

changeFavicon('/base_accounting_kit/static/images/logo.jpg');


document.getElementById("o_search_modal").addEventListener("shown.bs.modal", function () {
    document.getElementById("globalSearch").focus();
});

