odoo.define('droggol_theme_common.widgets.abstract_widget', function (require) {
'use strict';

var Widget = require('web.Widget');

return Widget.extend({

    xmlDependencies: [],
    /**
     * @constructor
     * @param {Object} options: useful parameters such as productIDs, domain etc.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = options;
        this.setValue(options);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get values based on the current configuration.
     *
     * @abstract
     */
    getValues: function () {},
    /**
     *
     * Set default values.
     *
     * @abstract
     */
    setValue: function (options) {},
});

});
