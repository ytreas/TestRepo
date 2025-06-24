/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks"; 
import { listView } from '@web/views/list/list_view';
import { useState } from "@odoo/owl";


export class buttonController extends ListController {
   setup() {
         super.setup();
         this.rpc = useService("rpc");
         this.orm = useService("orm");
         this.actionService = useService("action");
         this.state = useState({
            fromDate: '',
            toDate: '',
            searchTerm: ''
        });
         console.log('Context during setup', this.props.context);
         console.log('Selection during setup', this.props.selection);
      }
      mounted() {
         super.mounted();
         // Now try accessing the context after the view is mounted
         if (this.view && this.view.context) {
             this.context = this.view.context;  // Access context here
             console.log('Context during mounted:', this.context);
         } else {
             console.error('Context is still not available in mounted');
         }
     }
     OnPrintClick() {
         console.log('OnPrintClick called'); 
         
         const selectedRecords = this.props.selection || this.env.model.root.selection;
         // console.log('Selected Records:', selectedRecords);

         const selectedDatabaseIds = Array.from(selectedRecords).map(record => record.resId);
         // console.log('Selected Database IDs:', selectedDatabaseIds);

         this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'vehicle.number.wizard',
            name:'Company Vehicle Report',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
            context: {
               default_selected_ids: selectedDatabaseIds, // Pass selected database IDs to the wizard
            },
         });
      }
     
    }
    

registry.category("views").add("print_button", {
   ...listView,
   Controller: buttonController,
   buttonTemplate: "button_print.ListView.Buttons",
});
