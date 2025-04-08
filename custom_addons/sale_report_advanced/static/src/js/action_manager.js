/** @odoo-module **/
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

// Create a simple UI block overlay
function showOverlay() {
    let overlay = document.createElement("div");
    overlay.id = "customOverlay";
    overlay.style.position = "fixed";
    overlay.style.top = 0;
    overlay.style.left = 0;
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    overlay.style.zIndex = 10000;
    document.body.appendChild(overlay);
}

// Remove the UI block overlay
function removeOverlay() {
    let overlay = document.getElementById("customOverlay");
    if (overlay) {
        overlay.remove();
    }
}

registry.category("ir.actions.report handlers").add("xlsx", async function (action) {
    if (action.report_type === 'xlsx') {
        showOverlay(); // Show overlay before download starts

        try {
            // Download the report
            await download({
                url: '/xlsx_reports',
                data: action.data,
            });
        } catch (error) {
            // Handle any errors that occur during the report generation
            console.error("Download error:", error);
            self.call('crash_manager', 'rpc_error', error);
        } finally {
            // Remove overlay regardless of whether an error occurred or not
            removeOverlay();
        }
    }
});
