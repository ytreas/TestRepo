/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

export class VehicleInfoListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onVehicleDownloadClick() {
        try {
            const action = await this.orm.call(
                'vehicle.info',
                'action_export_vehicle_xlsx',
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

registry.category("views").add("vehicle_info_button_tree", {
    ...listView,
    Controller: VehicleInfoListController,
    buttonTemplate: "vehicle_info.ListView.Buttons",
});
