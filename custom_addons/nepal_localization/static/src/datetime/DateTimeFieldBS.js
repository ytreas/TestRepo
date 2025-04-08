// // Import necessary libraries
// // import { DateTimeField } from "@odoo/odoo";
// import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
// // import nepaliDate from "nepali-datetime";

// export class DateTimeFieldBS extends DateTimeField {
//     setup() 
//     {
//         debugger;
        
//         super.setup();
//         this._convertToNepaliDate();
//     }

//     _convertToNepaliDate() {
//         // Assuming this.props.value contains the English date
//         let englishDate = this.props.value;
//         let nepaliDate = nepaliDate.englishToNepali(englishDate);
//         // Update the state or props accordingly to display the Nepali date
//         this.props.value = nepaliDate.format('YYYY-MM-DD');
//     }

//     _convertToEnglishDate(nepaliDate) 
//     {
//         debugger;

//         // let englishDate = nepaliDate.nepaliToEnglish(nepaliDate);
//         // return englishDate.format('YYYY-MM-DD');
//     }

//     _onInputChange(event) {
//         debugger;
//         // Override input change to convert Nepali date back to English
//         let nepaliDate = event.target.value;
//         // let englishDate = this._convertToEnglishDate(nepaliDate);
//         // this.props.value = englishDate;
//         // this._updateModel(englishDate);
//     }

//     _updateModel(value) {
//         // Update the model with the converted English date
//         this.props.updateValue(value);
//     }

//     // Render method if needed to customize the rendering
//     render() {
//         return (
//             <input
//                 type="text"
//                 value={this.props.value}
//                 onInput={this._onInputChange.bind(this)}
//             />
//         );
//     }
// }

// // Register the custom component
 
