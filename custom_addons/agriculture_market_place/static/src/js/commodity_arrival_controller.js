/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class CommodityArrivalListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onDownloadClick() {
        try {
            const action = await this.orm.call(
                'commodity.arrival',
                'action_export_xlsx',
                [[]]
            );
            
            if (action && action.url) {
                location.href = action.url; 
            }
        } catch (error) {
            console.error('Download failed:', error);
        }
    }
}

registry.category("views").add("commodity_arrival_button_tree", {
    ...listView,
    Controller: CommodityArrivalListController,
    buttonTemplate: "commodity_arrival.ListView.Buttons",
});
