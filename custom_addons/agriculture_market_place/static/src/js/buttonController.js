/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks"; 
import { listView } from '@web/views/list/list_view';

export class buttonController extends ListController {
   setup() {
         super.setup();
         this.rpc = useService("rpc");
         this.orm = useService("orm");
         console.log('Context during setup', this.props.context);
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
      OnTestClick() {
         this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'amp.daily.price.wizard',
            name:'Daily Price Report',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
         });
      }
      OnTestClickB() {
         this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'daily.arrival.entry',
            name:'Daily Arrival Entry Report',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_id: false,
      });
   }


   async firstprint() {
      const report_type =  this.props.context.report_type ?? null;
      const date_from =  this.props.context.date_from ?? null;
      const date_to =  this.props.context.date_to ?? null;
      const commodity =  this.props.context.commodity ?? null;
      const date =  this.props.context.date ?? null;
      
      try{  
         // const params = await this.orm.call("daily.arrival.entry", "print_report", [], {context});
         // const params = await this.orm.call("daily.arrival.entry", "print_reportd",[], {
         //    report_type: report_type,
         //    date_from: date_from,
         //    date_to: date_to,
         //    commodity: commodity,
         //    view_report_type: "normal",
         // });
   
         
         let url = '/report/pdf/'
         const params = [];

         if (report_type) {
             params.push(`report_type=${encodeURIComponent(report_type)}`);
         }
         if (date_from && date_from !== 'false') {
             params.push(`date_from=${encodeURIComponent(date_from)}`);
         }
         if (date_to && date_to !== 'false') {
             params.push(`date_to=${encodeURIComponent(date_to)}`);
         }
         if (commodity && commodity !== 'false') {
             params.push(`commodity=${encodeURIComponent(commodity)}`);
         }
         if (date && date !== 'false') {
            params.push(`date=${encodeURIComponent(date)}`);
        }
 
         // Join the parameters with '&' and append to the URL
         if (params.length > 0) {
             url += '?' + params.join('&');
         }
       
         console.log("Url ",url);
         const response = await fetch(url, { method: 'GET' });

         console.log("Response ",response);

         if (response.ok) {
            // Download the file
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = 'report.pdf';  
            document.body.appendChild(a);
            a.click();
            a.remove();
         } else {
               console.error('Failed to generate report:', response.statusText);
         }

         // window.open(url, '_blank'); 

         }catch (error) {
            console.error('RPC call failed:', error);
         }
      }
   }
   

registry.category("views").add("button_in_tree", {
   ...listView,
   Controller: buttonController,
   buttonTemplate: "button_sale.ListView.Buttons",
});
registry.category("views").add("button_in_tree_bs", {
   ...listView,
   Controller: buttonController,
   buttonTemplate: "button_sale.ListView.ButtonsB",
});

registry.category("views").add("firstprint", {
   ...listView,
   Controller: buttonController,
   buttonTemplate: "firstprint",
});
