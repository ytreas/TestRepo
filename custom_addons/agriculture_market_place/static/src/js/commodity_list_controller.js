/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks"; 

export class CommodityListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onDownloadClick() {
        try {
            const action = await this.orm.call(
                'commodity.price.history',
                'action_export_xlsx',
                [[]]  // Empty list for all records
            );
            // console.log('Action:', action);
            
            if (action) {
               location.href = action.url;
            }
        } catch (error) {
            console.error('Download failed:', error);
        }
    }
}

registry.category("views").add("commodity_price_button_tree", {
    ...listView,
    Controller: CommodityListController,
    buttonTemplate: "commodity_price.ListView.Buttons",
});