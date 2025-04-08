/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks"; 

export class CommodityEntryListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onDownloadClick() {
        try {
            const action = await this.orm.call(
                'commodity.entry',
                'action_export_xlsx',
                [[]]
            );

            if (action && action.url) {
                window.location.href = action.url;
            }
        } catch (error) {
            console.error("Download failed:", error);
        }
    }
}

// Register the custom list view with the button
registry.category("views").add("commodity_entry_list_view", {
    ...listView,
    Controller: CommodityEntryListController,
    buttonTemplate: "commodity_entry.ListView.Buttons",
});
