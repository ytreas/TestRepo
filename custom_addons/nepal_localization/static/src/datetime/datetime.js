/** @odoo-module **/

import { Component, onWillRender, useState, useRef, onError, onMounted, onInput } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import {
    areDatesEqual,
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
    today,
    momentToLuxon,
    moment,
    readonly,
    name,
    id
} from "@web/core/l10n/dates";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ensureArray } from "@web/core/utils/arrays";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "@web/views/standard_view_props";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
// import { dateField } from "@web/views/fields/datetime/datetime_field";
const { DateTime } = luxon;
import { mount } from '@odoo/owl';

/**
 * @typedef {luxon_bs.DateTime} DateTime
 *
 * @typedef {import("@web/views/standard_field_props").StandardFieldProps & {
 *  endDateField?: string;
 *  maxDate?: string;
 *  minDate?: string;
 *  placeholder?: string;
 *  required?: boolean;
 *  rounding?: number;
 *  startDateField?: string;
 *  warnFuture?: boolean;
 * }} DateTimeFieldProps
 *
 * @typedef {import("@web/core/datetime/datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

// Function to generate a unique ID
function generateUniqueId(key) {
    return key +'_' + Math.random().toString(36).substr(2, 9);
}

export class DateTimeFieldBS extends DateTimeField {
        constructor(parent, props)
        {
            super(...arguments);
            // Add your extra properties here
            if (this.props.corresponding_field==undefined)
                this.props.corresponding_field = '';

            if (this.props.alwaysRange==undefined)
                this.props.alwaysRange = false;
        };
        
        static components = 
        {
            DateTimeField,
        };

        static props = {
            ...standardFieldProps,
            ...DateTimeField.props,
            endDateField: { type: String, optional: true },
            maxDate: { type: String, optional: true },
            minDate: { type: String, optional: true },
            corresponding_field: { type: String, optional: true },
            alwaysRange: { type: Boolean, optional: true },
            placeholder: { type: String, optional: true },
            required: { type: Boolean, optional: true },
            rounding: { type: Number, optional: true },
            startDateField: { type: String, optional: true },
            warnFuture: { type: Boolean, optional: true },
            id: { type: String, optional: true },
            name: { type: String, optional: true },
            readonly: { type: Boolean, optional: true },

            
     };

    static template = "nepal_localization.DateTimeField";

    setup() 
    {

        //defalult
        DateTimeField.props.alwaysRange= this.props.alwaysRange;
        DateTimeField.props.corresponding_field= this.props.corresponding_field;

        super.setup();

        console.log(this.props)
        
        
        this.state2 = useState({
            key: '',
            ad_date: '',
            bs_date: '',
            id: this.props.id,
            new_id: generateUniqueId(this.props.name+"aa"),
            type : this.field.type,
            field: this.field,
            corresponding_field: '',
            alwaysRange: false,
            readonly: false,
            name: this.props.name,
            record : this.props.record,


            // Nepali Time Picker
            b_hour:this.getTime('hour'),
            b_minute:this.getTime('minute'),



        });

        console.log('hour',this.state2.b_hour);
        console.log('minutes',this.state2.b_minute);
        
        

        this.field['corresponding_field'] = this.props.corresponding_field

        if (this.props.corresponding_field!=undefined && this.props.corresponding_field !='')
        {
            this.field[this.props.corresponding_field] = this.props.corresponding_field

            const newField = 
            {
                change_default: false,
                name: this.props.corresponding_field,
                readonly: false,
                required: true,
                searchable: true,
                sortable: true,
                store: true,
                string: "Nepali Date",
                type: "string",
                value: null // Initialize value if needed
            };
            // Assuming props.record is an object
             if (this.props.record) 
             {
                 this.props.record.fields[this.props.corresponding_field] = newField;
                 this.props.record[this.props.corresponding_field] = newField;
             }
        }

        this.inputel = useRef("nepali-datepicker")
        let bs_dict={},ad_dict=false,temp,ad,bs,new_ad,key,new_dict;
        this.state2.key = this.props.name

        //bs_dict = this.getRecordValue().c
        ad_dict = this.getRecordValue().c

        this.time = ''
        this.props.record.update = (changes, { save } = {})=>{
            if(!changes)
                return
            
            // if (changes.hasOwnProperty('type')== false)
            //     return

            let key = Object.keys(changes)[0]
            if(String(this.props.record.fields[key].type).includes('date'))
            {
                let ad_dict = Object.values(changes)[0].c
                let same_dates = true;
                if(this.props.record.data[key] && ad_dict!=undefined)
                    Object.keys(ad_dict).forEach(k=>{
                        if(this.props.record.data[key].c!=undefined && this.props.record.data[key].c!=null && ad_dict[k]!=this.props.record.data[key].c[k])
                            same_dates = false
                    })
                else
                    same_dates = false

                if(same_dates)
                    return

                if(ad_dict==undefined)
                {
                    //new_id
                     //document.getElementById(key+'aa').value ="";
                     //document.getElementById(this.state2.new_id).value="";

                    //document.getElementById(this.state2.id).value ="";
                    //document.getElementById(this.state2.new_id).value="";
                    return
                }

                if(this.props.record.fields[key].type == 'datetime')
                    this.time = ` ${ad_dict['hour']}:${ad_dict['minute']}:${ad_dict['second']}`
                try
                {
                    ad_dict = 
                    {
                        'year':ad_dict['year'],
                        'month':ad_dict['month'],
                        'day':ad_dict['day'],
                    }
                    bs_dict = NepaliFunctions.AD2BS(ad_dict)
                }
                catch
                {
                    return
                }
                
                if(this.props.record.fields[key].type == 'datetime')
                {
                     //document.getElementById(key+ generateUniqueId('aa')).value = Object.values(bs_dict).join('/') + this.time;

                    //if (Object.values(changes)[2]!=undefined && Object.values(changes)[2].new_id !=null)
                    if (this.props.record.fields[key]!=null && this.props.record.fields[key].new_id !=null )
                    {
                        document.getElementById(this.props.record.fields[key].new_id).value = Object.values(bs_dict).join('/') + this.time;
                    }
                    else
                    {
                        document.getElementById(this.state2.new_id).value = Object.values(bs_dict).join('/') + this.time;
                    }

                    this.state2.bs_date = Object.values(bs_dict).join('/') + this.time;
                    this.state2.ad_date = Object.values(ad_dict).join('/') + this.time;
                    if(this.props.record.fields[key].corresponding_field){
                        changes[this.props.record.fields[key].corresponding_field] = Object.values(bs_dict).join('/') + this.time;
                    }
                }
                else if (this.props.record.fields[key].type == 'date')
                {
                    //document.getElementById(key+generateUniqueId('aa')).value = Object.values(bs_dict).join('/');
                    //if (Object.values(changes)[2]!=undefined && Object.values(changes)[2].new_id !=null)
                    if (this.props.record.fields[key]!=null && this.props.record.fields[key].new_id !=undefined )
                    {
                        document.getElementById(this.props.record.fields[key].new_id).value = Object.values(bs_dict).join('/');
                    }
                    else
                    {
                        document.getElementById(this.state2.new_id).value = Object.values(bs_dict).join('/');
                    }

                    this.state2.bs_date = Object.values(bs_dict).join('/');
                    this.state2.ad_date = Object.values(ad_dict).join('/');
                    
                    if(this.props.record.fields[key].corresponding_field)
                    {
                        //this.props.record.fields[this.props.record.fields[key].corresponding_field].value=Object.values(bs_dict).join('/');
                        //changes[this.props.record.fields[key].corresponding_field] = this.props.record.fields[this.props.record.fields[key].corresponding_field];

                            // const newField = 
                            // {
                            //     change_default: false,
                            //     name: this.props.record.fields[key].corresponding_field,
                            //     readonly: false,
                            //     required: true,
                            //     searchable: true,
                            //     sortable: true,
                            //     store: true,
                            //     string: "Nepali Date",
                            //     type: "string",
                            //     value: Object.values(bs_dict).join('/') 
                            // };

                            // Initialize value if needed
                        //changes[this.props.record.fields[key].corresponding_field] = newField;
                        changes[this.props.record.fields[key].corresponding_field] = Object.values(bs_dict).join('/');
                    }
                }
            }
            if (this.props.record.model._urgentSave) {
                return this.props.record._update(changes, { save: false }); // save is already scheduled
            }
            return this.props.record.model.mutex.exec(async () => {
                await this.props.record._update(changes, { withoutOnchange: save });
                if (save) {
                    return this.props.record._save();
                }
            });
        }

        if(ad_dict)
        {
                if(this.state2.type == 'datetime'){
                    this.time = ` ${ad_dict['hour']}:${ad_dict['minute']}:${ad_dict['second']}`
                }
                bs_dict = NepaliFunctions.AD2BS(ad_dict)

                if(this.state2.type == 'date'){
                    this.state2.ad_date = Object.values(ad_dict).slice(0,3).join('/');
                    this.state2.bs_date = Object.values(bs_dict).slice(0,3).join('/');
                }
                else if(this.state2.type == 'datetime'){
                    this.state2.ad_date = Object.values(ad_dict).slice(0,3).join('/') + this.time;
                    this.state2.bs_date = Object.values(bs_dict).slice(0,3).join('/') + this.time;
                }
                ad_dict = new Date(this.state2.ad_date);
                ad_dict = luxon.DateTime.fromJSDate(ad_dict);
                this.new_dict ={}
                this.new_dict[this.state2.key] = ad_dict
                if(this.props.corresponding_field){
                    this.new_dict[this.props.corresponding_field]=this.state2.bs_date;
                }
            }

        let err = false;
        onError((e) => {
            this.err=true;
            console.log(e);
        });

        onMounted(() => {
            // handling the nonscrolling behaviour of the datepicker
            if(err){
                return;
            }

            if (this.props.id && document.getElementById(this.props.id)!=null)
                {

                    var old_id = this.props.id;
                    this.props.id =generateUniqueId(this.props.id);
                    this.state2.id =this.props.id;

                    this.props.record.fields[this.props.name].new_id = this.state2.new_id;

                    document.getElementById(old_id).id = this.props.id;
                }

            
            if(!document.getElementById(this.state2.id)){
                return
            }

            if (document.getElementById(this.state2.id).value=='' &&
            this.props.required!=undefined && this.props.required == true)
            {
                var _ad_Date = new Date().toISOString().slice(0, 10);
                var _temp_ad =  _ad_Date.slice(5,7)+'/'+ _ad_Date.slice(8,11)  +'/' + _ad_Date.slice(0,4);
                
                try
                {
                    ad_dict = {
                        'year':_ad_Date.slice(0,4),
                        'month':_ad_Date.slice(5,7),
                        'day':_ad_Date.slice(8,11),
                    }

                    bs_dict = NepaliFunctions.AD2BS(ad_dict)
                    this.state2.ad_date =_temp_ad;

                    bs_dict =  bs_dict.year +'/'+ bs_dict.month +'/' + bs_dict.day;
                    bs_dict = bs_dict.replaceAll('-', '/');
                    this.state2.bs_date =bs_dict;

                    new_ad = new Date(this.state2.ad_date);
                    ad_dict = luxon.DateTime.fromJSDate(new_ad);

                    new_dict ={}
                    new_dict[this.state2.key]=ad_dict
                }
                catch{}

                document.getElementById(this.state2.id).value =_temp_ad;
                document.getElementById(this.state2.new_id).value = this.state2.bs_date;
            }

            //****************** */
            if (document.getElementById(this.state2.id).value !=='' 
                && document.getElementById(this.state2.new_id).value =='' 
                && this.props.required!=undefined && this.props.required == true 
                && this.state2.bs_date != '')
            {
                var _ad_Date_temp = NepaliFunctions.BS2AD(bs_dict);
                _ad_Date_temp = _ad_Date_temp.year +'/'+ _ad_Date_temp.month +'/'+ _ad_Date_temp.day;

                new_ad = new Date(_ad_Date_temp);
                ad_dict =luxon.DateTime.fromJSDate(new_ad);
                new_dict ={}
                new_dict[this.state2.key]=ad_dict
            }
            //******************** */

            if(this.props.corresponding_field)
            {
                document.getElementById(this.state2.new_id).value = this.state2.bs_date;

                if (new_dict!=undefined)
                    new_dict[this.props.corresponding_field]=this.state2.bs_date;
            }

            if (new_dict!=undefined)
                this.props.record.update(new_dict);

            document.getElementById(this.props.id).value=this.state2.ad_date;
            let first_click= {},curr_top={};
            first_click[this.props.id] = true;

            const on_o_content_scroll=(e)=>{
                if(document.getElementById('ndp-nepali-box'))
                {
                    document.getElementById('ndp-nepali-box').classList.add('d-none');
                    document.getElementsByClassName('o_content')[0].removeEventListener('scroll',on_o_content_scroll)
                }
            }

            //*************************/
            this.inputel.el.nepaliDatePicker({
                ndpYear: true,
                ndpMonth: true,
                onChange: (ev)=>{

                    this.new_dict ={}

                    if(this.field.type=='date'){
                        this.state2.ad_date = ev.ad.slice(0,4)+'/'+ev.ad.slice(5,7)+'/'+ev.ad.slice(8,11);
                        this.state2.bs_date = ev.bs.replaceAll('-','/');
                    }else{
                        this.state2.ad_date = ev.ad.slice(0,4)+'/'+ev.ad.slice(5,7)+'/'+ev.ad.slice(8,11)+this.time;
                        this.state2.bs_date = ev.bs.replaceAll('-','/')+ this.time;
                    }

                    let ad_dict = {},bs_dict= {},temp;
                    ad = ev.ad.slice(0,4)+'/'+ev.ad.slice(5,7)+'/'+ev.ad.slice(8,11);
                    temp = ad.split('/');
                    
                    ad_dict["year"] = Number(temp[0]);
                    ad_dict["month"] = Number(temp[1]);
                    ad_dict["day"] = Number(temp[2]);

                    temp = this.state2.bs_date.split('/');
                    bs_dict["year"] = Number(temp[0]);
                    bs_dict["month"] = Number(temp[1]);
                    bs_dict["day"] = Number(temp[2]);

                    this.state2.bs_date.split('/');
                    new_ad = new Date(this.state2.ad_date);
                    ad_dict =luxon.DateTime.fromJSDate(new_ad);
                    new_dict ={}
                    new_dict[this.state2.key]=ad_dict
                    
                    if(this.props.corresponding_field)
                    {
                        new_dict[this.props.corresponding_field]= bs_dict; //this.state2.bs_date;
                        /////new_dict[this.state2]=this.state2;
                    }
                    this.props.record.update(new_dict);
                }
            });
        });
    }

    getTime(type){
        let b_date=new Date();
        if (type.length){
            return type=='hour'?b_date.getHours():b_date.getMinutes();
        }
    }
}

const START_DATE_FIELD_OPTION = "start_date_field";
const END_DATE_FIELD_OPTION = "end_date_field";

export const dateFieldBS = {
    component: DateTimeFieldBS,
    displayName: _t("Date for BS"),
    supportedOptions: [
        {
            label: _t("Earliest Boolean date"),
            name: "readonly",
            type: "boolean",
            help: _t(`Displays a warning icon if the input dates are in the future.`),
        },
        {
            label: _t("Earliest string date"),
            name: "id",
            type: "string",
            help: _t(`Displays a warning icon if the input dates are in the future.`),
        },
        {
            label: _t("Earliest accepted date"),
            name: "min_date",
            type: "string",
            help: _t(`ISO-formatted date (e.g. "2018-12-31") or "today".`),
        },
        {
            label: _t("Latest accepted date"),
            name: "max_date",
            type: "string",
            help: _t(`ISO-formatted date (e.g. "2018-12-31") or "today".`),
        },
        {
            label: _t("Warning for future dates"),
            name: "warn_future",
            type: "boolean",
            help: _t(`Displays a warning icon if the input dates are in the future.`),
        },
        {
            label: _t("Corresponding BS field"),
            name: "corresponding_field",
            type: "string",
            help: _t(`Stores the BS date into the given field(Should be char field).`),
        },
    ],
    supportedTypes: ["date"],
    extractProps: ({ attrs, options }, dynamicInfo) => ({
        ...standardFieldProps,
        endDateField: options[END_DATE_FIELD_OPTION] || undefined,
        maxDate: options.max_date || undefined,
        minDate: options.min_date || undefined,
        corresponding_field: options.corresponding_field || undefined,
        alwaysRange: archParseBoolean(options.always_range) || undefined,
        placeholder: attrs.placeholder || undefined,
        required: dynamicInfo.required || undefined,
        rounding: options.rounding && parseInt(options.rounding, 10) || undefined,
        startDateField: options[START_DATE_FIELD_OPTION] || undefined,
        warnFuture: archParseBoolean(options.warn_future) || undefined,
    })
};


export const dateTimeFieldBS = {
    ...dateFieldBS,
    displayName: _t("Date & Time"),
    supportedOptions: [
        ...dateFieldBS.supportedOptions,
        {
            label: _t("Time interval"),
            name: "rounding",
            type: "number",
            default: 5,
            help: _t(
                `Control the number of minutes in the time selection. E.g. set it to 15 to work in quarters.`
            ),
        },
    ],
    supportedTypes: ["datetime"],
};

export const dateRangeFieldBS = {
    ...dateTimeFieldBS,
    displayName: _t("Date Range"),
    supportedOptions: [
        ...dateTimeFieldBS.supportedOptions,
        {
            label: _t("Start date field"),
            name: START_DATE_FIELD_OPTION,
            type: "field",
            availableTypes: ["date", "datetime"],
        },
        {
            label: _t("End date field"),
            name: END_DATE_FIELD_OPTION,
            type: "field",
            availableTypes: ["date", "datetime"],
        },
        {
            label: _t("Always range"),
            name: "always_range",
            type: "boolean",
            default: false,
            help: _t(
                `Set to true the full range input has to be display by default, even if empty.`
            ),
        },
    ],
    supportedTypes: ["date", "datetime"],
};

registry.category('fields').content.date[1]=dateFieldBS;
registry.category('fields').content.daterange[1]=dateRangeFieldBS;
registry.category('fields').content.datetime[1]=dateTimeFieldBS;

/*
registry
    .category("fields")
    .add("bs_date", dateField);
    .add("bs_daterange", dateRangeField)
    .add("bs_datetime", dateTimeField);
*/
