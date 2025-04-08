/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";



export class InheritedSwitchCompanyMenu extends SwitchCompanyMenu {
    setup() {
        super.setup();
    }
    clickSelectAll= (e)=>{
        let i = true;
        Array.from(e.target.parentNode.parentNode.querySelectorAll('[data-menu="company"]')).forEach(each=>{
            if(i){
                i = false;
                return
            }
            each.children[0].click();
            // this.toggleCompany(Number(each.dataset.companyId))
        })
        // browser.clearTimeout(this.toggleTimer);
        // this.toggleTimer = browser.setTimeout(() => {
        //     this.companyService.setCompanies("toggle", ...this.state.companiesToToggle);
        // }, this.constructor.toggleDelay);
    }
    clickSearchButton=e=>{
        if(Array.from(e.target.parentNode.parentNode.children).length<=1 || document.getElementById('companySwitcherSearchDiv')){
            return;
        }
        let searchContainer = document.createElement('div');
        searchContainer.classList = 'p-3';
        searchContainer.setAttribute('id','companySwitcherSearchDiv');

        let searchBox = document.createElement('input');
        searchBox.setAttribute('type','search');

        let resetBtn = document.createElement('button');
        resetBtn.classList = 'fa fa-refresh btn btn-sm btn-secondary';
        resetBtn.addEventListener('click',e=>{
            Array.from(Array.from(e.target.parentNode.parentNode.parentNode.children)[1].getElementsByClassName('company_label')).forEach(each=>{
                console.log('7777',each.parentNode.parentNode.children[0])
                if(Array.from(each.parentNode.parentNode.children)[0].children[0].children[0].classList.contains('fa-check-square')){
                    // this.toggleCompany(Number(each.parentNode.parentNode.dataset.companyId))
                    each.parentNode.parentNode.children[0].click()
                }
                // console.log(each.parentNode.parentNode.dataset.companyId)
            })
            browser.clearTimeout(this.toggleTimer);
            this.toggleTimer = browser.setTimeout(() => {
                this.companyService.setCompanies("toggle", ...this.state.companiesToToggle);
            }, this.constructor.toggleDelay);
        })

        searchContainer.appendChild(searchBox)
        searchContainer.appendChild(resetBtn)
        searchContainer.addEventListener('input',e=>{
            Array.from(Array.from(e.target.parentNode.parentNode.parentNode.children)[1].getElementsByClassName('company_label')).forEach(each=>{
                // console.log(each)
                if(!each.innerHTML.toLowerCase().includes(e.target.value.toLowerCase())){
                    if(!Array.from(each.parentNode.parentNode.parentNode.classList).includes('d-none')){
                        each.parentNode.parentNode.parentNode.classList.add('d-none');
                    }
                }
                else{
                    if(Array.from(each.parentNode.parentNode.parentNode.classList).includes('d-none')){
                        each.parentNode.parentNode.parentNode.classList.remove('d-none');
                    }
                }
            })
        })
        Array.from(e.target.parentNode.parentNode.children)[1].prepend(searchContainer);

        let search_div;
    }

}
InheritedSwitchCompanyMenu.template = "lekha.SwitchCompanyMenu";
export const systrayItem = {
    Component: InheritedSwitchCompanyMenu,
};

registry.category("systray").content.SwitchCompanyMenu[1].Component = InheritedSwitchCompanyMenu

// registry.category("systray").add("lekha.UserCompany", systrayItem, { sequence: 200 });
