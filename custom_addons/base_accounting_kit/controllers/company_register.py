from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
import base64
import json
from datetime import datetime
import io


class CompanyRegistrationController(http.Controller):
    @http.route("/web/register", type="http", auth="public", website=True)
    def register_form(self, **kwargs):

        # Prepare an empty record for the form
        # register_data = request.env['company.register'].new()

        categories = request.env["company.category"].sudo().search([])
        provinces = request.env["location.province"].sudo().search([])

        return request.render(
            "base_accounting_kit.web_register_template",
            {
                # 'register_data': register_data,
                "company_category_ids": categories,
                "provinces": provinces,
            },
        )
    @http.route("/web/update/<int:code>", type="http", auth="public", website=True)
    def update_record(self, code, **kwargs):
        registration_record = request.env['company.register'].sudo().search([('update_code', '=', code)], limit=1)
        email_wizard_record = request.env['email.wizard'].sudo().search(
            [('update_code', '=', code)], 
            order='create_date desc', 
            limit=1
        )
        print("The registration record is: ", registration_record)
        print("wiz",email_wizard_record)

        revert_fields = []
        for individual_field in email_wizard_record.individual_field_ids:
            revert_fields.append(individual_field.field_code)
        for organization_field in email_wizard_record.organization_field_ids:
            revert_fields.append(organization_field.field_code)
        categories = request.env["company.category"].sudo().search([])
        provinces = request.env["location.province"].sudo().search([])
        print(revert_fields)
        if registration_record:
            return request.render(
                "base_accounting_kit.web_register_update",
                {
                    "update_code": code,
                    "message": "The code is valid.",
                    "registration_record": registration_record,
                    "company_category_ids": categories,
                    "provinces": provinces,
                    "revert_fields": revert_fields,
                },
            )
        else:
            return request.render(
                "base_accounting_kit.web_register_template",
                {
                    # 'register_data': register_data,
                    "company_category_ids": categories,
                    "provinces": provinces,
                },
            )

    @http.route(
        "/company/register",
        type="http",
        auth="public",
        cors="*",
        methods=["POST"],
        csrf=False,
        website=True,
    )
    def register_company(self, **post):
        
        owner_citizenship_front = request.httprequest.files.get(
            "owner_citizenship_front"
        )
        owner_citizenship_back = request.httprequest.files.get("owner_citizenship_back")
        login_bg_img_company = request.httprequest.files.get("login_bg_img_company")
        login_bg_img_individual = request.httprequest.files.get(
            "login_bg_img_individual"
        )
        client_fullname = ""

        def encode_file(file):
            if file:
                return base64.b64encode(file.read())
            return False

        values = {
            "tax_id": post.get("tax_id"),
            # 'total_amount':post.get('tax_id'),
            # 'recent_tax_paid_year': post.get('recent_tax_paid_year') if post.get('recent_tax_paid_year') else None,
            # 'company_category_ids': post.get('company_category_ids'),
            "recent_tax_paid_year": post.get("recent_tax_paid_year"),
            # 'start_date': post.get('start_date') if post.get('start_date') else None,
            'pan_number': post.get('pan_number'),
            'company_type': post.get('company_type'),
            'registration_no': post.get('registration_no'),
            'pricing': post.get('total_amount'),
            'email': post.get('email'),
            'mobile': post.get('mobile'),
            'phone': post.get('phone'),
            'province': post.get('province'),
            'district': post.get('district'),
            'palika': post.get('palika'),
            'ward_no': post.get('ward_no'),
            'owner_citizenship_front': encode_file(owner_citizenship_front),
            'owner_citizenship_back': encode_file(owner_citizenship_back),
            'login_bg_img_company': encode_file(login_bg_img_company),
        }

        company_type = post.get("company_type")

        if company_type == "individual":
            # Additional fields for individual registration
            values.update(
                {
                    "first_name_en": post.get("first_name_en"),
                    "middle_name_en": post.get("middle_name_en"),
                    "last_name_en": post.get("last_name_en"),
                    "first_name_np": post.get("first_name_np"),
                    "middle_name_np": post.get("middle_name_np"),
                    "last_name_np": post.get("last_name_np"),
                    "gender": post.get("gender"),
                    "login_bg_img_individual": encode_file(login_bg_img_individual),
                }
            )

            client_fullname = f"{post.get('first_name_en')} { post.get('middle_name_en')} {post.get('last_name_en')}"

        elif company_type == "organization":
            # Additional fields for organization registration
            values.update(
                {
                    "organization_name_en": post.get("organization_name_en"),
                    "organization_name_np": post.get("organization_name_np"),
                    "organization_type": post.get("organization_type"),
                    "owner_name_en": post.get("owner_name_en"),
                    "owner_name_np": post.get("owner_name_np"),
                    "start_date": post.get("start_date"),
                    # Add other organization-specific fields as necessary
                }
            )
            client_fullname = f"{post.get('organization_name_en')} { post.get('organization_name_np')} {post.get('organization_type')}, {post.get('owner_name_en')}"

        print("asdfasdfsad", values)

        category_names = post.get(
            "business_second_ids"
        )  # Use getlist to get all selected values
        print("the names are:", category_names)

        order_lines = []
        invoice_lines = []
        if category_names:
            # Convert to integers if they are strings
            category_ids = [
                int(cat_id) for cat_id in category_names if cat_id.isdigit()
            ]
            print("the ids are:", category_ids)
            category_records = (
                request.env["company.category"]
                .sudo()
                .search([("id", "in", category_ids)])
            )
            print("the records are:", category_records)
            
            # default all coa category
            
            default_coa_category=request.env['company.category'].sudo().search([('code','=','1000000001')],limit=1)
            category_ids_collection=[(4, category.id) for category in category_records]
            category_ids_collection.append((4, default_coa_category.id))
            values["company_category_ids"] = category_ids_collection
            journal_lines = values["company_category_ids"]
            product = (
                http.request.env["product.product"].sudo().search([], limit=1)
            )  # Example product
            product_uom = product.uom_id.id  # Unit of measure of the product
            product_prices = (
                request.env["business.type.pricing"]
                .sudo()
                .search([("business_type", "in", category_ids)])
            )

            default_account = (
                http.request.env["account.account"].sudo().search([], limit=1)
            )
            for service in category_records:
                for pp in product_prices:
                    if service.id == pp.business_type.id:
                        try:
                            _product = (
                                request.env["product.product"]
                                .sudo()
                                .search([("default_code", "=", service.code)])
                            )
                        except Exception as e:
                            raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[_product_fetch_err]')
                        if not _product:
                            try:
                                _product= _product.create(
                                        {
                                            "name": service.name,
                                            "name_np": service.name_np,
                                            "sale_ok": False,
                                            "detailed_type": "service",
                                            "invoice_policy": "order",
                                            "list_price": pp.pricing,
                                            "standard_price": pp.pricing,
                                            "company_id": 1,
                                            "default_code": service.code,
                                        }
                                )
                            except Exception as e:
                                raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[_product_cr_err]')
                                
                        order_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_template_id": _product.id,
                                    "product_id": _product.id,
                                    # "display_type": 'line_section',
                                    "name": _product.name,
                                    "price_unit": _product.standard_price,
                                    "product_uom": product_uom,
                                    "product_uom_qty": 1.0,
                                },
                            ),
                        )

                        invoice_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": _product.id,
                                    "name": _product.name,
                                    "account_id": default_account.id,
                                    "quantity": 1,
                                    "price_unit": _product.standard_price,
                                },
                            ),
                        )
        try:
            service_payment_details = (
                request.env["lekhaplus.service.payment"]
                .sudo()
                .search(
                    [
                        ("client", "=", post.get("email")),
                        ("payment_status", "=", True),
                        ("subscription_status", "=", True),
                    ],
                    limit=1,
                )
            )
        except Exception as e:
              raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[payment_record_check_err]')
            
        if not service_payment_details:
            return request.render("base_accounting_kit.payment_not_done")

        # Bills and Quotations
        try:
            res_partner = (
                request.env["res.partner"]
                .sudo()
                .create(
                    {
                        "name": client_fullname,
                        "country_id": 167,
                        "company_id": 1,
                        "email": post.get("email"),
                        "verification_status": False,
                    }
                )
            )
        except Exception as e:
              raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[res_partner_cr_err]')
            

        try:
            quotation = (
                request.env["sale.order"]
                .sudo()
                .create(
                    {
                        "access_token": service_payment_details.transaction_id,
                        "partner_id": res_partner.id,
                        "partner_invoice_id": res_partner.id,
                        "partner_shipping_id": res_partner.id,
                        "date_order": datetime.now().date(),
                        "amount_total": service_payment_details.amount,
                        "amount_to_invoice": service_payment_details.amount,
                        "order_line": order_lines,
                        "company_id": 1,
                    }
                )
            )
        except Exception as e:
              raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[quotation_cr_err]')
           
        

        # })
        try:
            invoice = (
                request.env["account.move"]
                .sudo()
                .create(
                    {
                        "invoice_line_ids": invoice_lines,
                        "amount_residual": service_payment_details.amount,
                        "amount_residual_signed": 0,
                        "payment_state": "paid",
                        "partner_id": res_partner.id,
                        "access_token": service_payment_details.transaction_id,
                        "invoice_partner_display_name": client_fullname,
                        "date": datetime.now().date(),
                        "invoice_date": datetime.now().date(),
                        "move_type": "out_invoice",
                        # 'state':'posted',
                    }
                )
            )
        except Exception as e:
              raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[invoice_cr_err]')
           
        # invoice.action_post()

        base_url = request.httprequest.host_url
        invoice_link = (
            f"{base_url}my/invoices/{invoice.id}?access_token={invoice.access_token}"
        )
        quotation_link = (
            f"{base_url}/my/orders/{quotation.id}?access_token={quotation.access_token}"
        )
        # Bills and Quotations

        # except Exception as e:
        #     raise ValidationError(f"{_('Unexpected error occurred while processing. Please Contact the administration with reference id')} {service_payment_details.transaction_id}")
        # Create the company record
        try:
            request.env["company.register"].sudo().create(values)
        except Exception as e:
              raise ValidationError(f'{_("Could not proceed the form due to- ")} [{e}], err_cod-[company_register_cr_err]')
           

        return request.render(
            "base_accounting_kit.web_register_thank_you",
            {"invoice_link": invoice_link, "quotation_link": quotation_link},
        )  # Render a success/thank you page


class CompanyAPI(http.Controller):

    @http.route(
        "/api/company/register",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def api_register_company(self, **kwargs):
        try:
            values = {
                "organization_name_en": kwargs.get("organization_name_en"),
                "organization_name_np": kwargs.get("organization_name_np"),
                "organization_type": kwargs.get("organization_type"),
                "owner_name_np": kwargs.get("owner_name_np"),
                "owner_name_en": kwargs.get("owner_name_en"),
                "pan_number": kwargs.get("pan_number"),
                "email": kwargs.get("email"),
                "mobile": kwargs.get("mobile"),
                "phone": kwargs.get("phone"),
                "province": kwargs.get("province"),
                "district": kwargs.get("district"),
                "palika": kwargs.get("palika"),
                "ward_no": kwargs.get("ward_no"),
                "owner_citizenship_front": (
                    base64.b64decode(kwargs.get("owner_citizenship_front"))
                    if kwargs.get("owner_citizenship_front")
                    else False
                ),
                "owner_citizenship_back": (
                    base64.b64decode(kwargs.get("owner_citizenship_back"))
                    if kwargs.get("owner_citizenship_back")
                    else False
                ),
                "login_bg_img_company": (
                    base64.b64decode(kwargs.get("login_bg_img_company"))
                    if kwargs.get("login_bg_img_company")
                    else False
                ),
            }

            company_registration = request.env["company.register"].sudo().create(values)
            return {
                "status": "success",
                "message": "Company registered successfully",
                "company_id": company_registration.id,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @http.route(
        "/district/<int:province_id>",
        type="http",
        auth="public",
        cors="*",
        methods=["GET"],
        csrf=False,
    )
    def get_districts(self, province_id):
        print("here is the province id: ", province_id)
        districts = (
            request.env["location.district"]
            .sudo()
            .search([("province_name.id", "=", province_id)])
        )
        print("The districts are: ", districts)

        # Prepare the JSON response
        district_data = [
            {"id": district.id, "name": district.district_name_np}
            for district in districts
        ]

        # Create a JSON response
        response_data = {
            "districts": district_data,
        }

        return http.Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    @http.route(
        "/palika/<int:district_id>",
        type="http",
        cors="*",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_palikas(self, district_id):
        print("here is the district id: ", district_id)
        palikas = (
            request.env["location.palika"]
            .sudo()
            .search([("district_name.id", "=", district_id)])
        )
        print("The palikas are: ", palikas)

        # Prepare the JSON response
        palika_data = [
            {"id": palika.id, "name": palika.palika_name_np} for palika in palikas
        ]

        # Create a JSON response
        response_data = {
            "palikas": palika_data,
        }

        return http.Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"},
        )


class PricingController(http.Controller):

    @http.route("/pricing", type="http", auth="public", methods=["GET"], csrf=False)
    def get_pricing(self):
        ids = request.httprequest.args.get("ids")
        if ids:
            ids = list(map(int, ids.split(",")))
            prices = (
                request.env["business.type.pricing"]
                .sudo()
                .search([("business_type.id", "in", ids)])
                .mapped("pricing")
            )
            return request.make_response(
                json.dumps({"pricing": prices}),
                headers={"Content-Type": "application/json"},
            )
        return request.make_response(
            json.dumps({"pricing": []}), headers={"Content-Type": "application/json"}
        )
    @http.route("/pricing_name", type="http", auth="public", methods=["GET"], csrf=False)
    def get_pricing_name(self):
        ids = request.httprequest.args.get("ids")
        print("Received IDs: %s", ids)  # Log received IDs

        if not ids or ids.strip() == "":
            # If `ids` is empty or just commas, return an error
            print("No valid IDs provided.")
            return request.make_response(
                json.dumps({"error": "No valid IDs provided"}), 
                status=400,
                headers={"Content-Type": "application/json"}
            )

        try:
            # Split the IDs string and filter out any empty strings before converting to integers
            ids = [int(i) for i in ids.split(",") if i.strip()]
            print("Parsed IDs: %s", ids)  # Log parsed IDs

            # Search for the pricing records based on the provided IDs
            pricing_records = request.env["business.type.pricing"].sudo().search([("business_type.id", "in", ids)])
            print("Pricing Records Found: %s", pricing_records)  # Log found records

            # Map the pricing details
            prices = pricing_records.mapped(lambda p: {"id": p.business_type.id, "name": p.business_type.name_np, "pricing": p.pricing})
            print("Mapped Prices: %s", prices)  # Log the mapped prices

            # Return the response in JSON format
            return request.make_response(
                json.dumps({"pricing": prices}),
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            print("Error processing request: %s", str(e))  # Log any error
            return request.make_response(
                json.dumps({"error": "Internal Server Error"}), 
                status=500,
                headers={"Content-Type": "application/json"}
            )
        
    @http.route(
    "/company/update",
    type="http",
    auth="public",
    cors="*",
    methods=["POST"],
    csrf=False,
    website=True,
    )
    def update_company(self, **post):
        print("This is the post:", post)

        # Find the record by 'update_code'
        update_code = post.get("update_code")
        if not update_code:
            raise ValidationError("Update code is required to find the record.")

        company = request.env["company.register"].sudo().search([("update_code", "=", update_code)], limit=1)
        
        if not company:
            raise ValidationError(f"No company found with update code: {update_code}")

        # Prepare fields to update
        fields_to_check = [
            "tax_id", "first_name_en", "middle_name_en", "last_name_en", 
            "first_name_np", "middle_name_np", "last_name_np", 
            "organization_name_en", "organization_name_np", 
            "owner_name_en", "owner_name_np", "gender", 
            "recent_tax_paid_year", "pan_number", "company_type", 
            "registration_no", "email", "mobile", "phone", "ward_no"
        ]

        # Collect only changed values
        values_to_update = {}
        unchanged_fields = []

        # Check and compare the province, district, and palika
        province_id = post.get("province")
        district_id = post.get("district")
        palika_id = post.get("palika")

        if province_id:
            province = request.env["location.province"].sudo().search([("id", "=", int(province_id))], limit=1)
            if not province:
                raise ValidationError(f"No province found with ID: {province_id}")
            if company.province.id != province.id:
                values_to_update["province"] = province.id

        if district_id:
            district = request.env["location.district"].sudo().search([("id", "=", int(district_id))], limit=1)
            if not district:
                raise ValidationError(f"No district found with ID: {district_id}")
            if company.district.id != district.id:
                values_to_update["district"] = district.id

        if palika_id:
            palika = request.env["location.palika"].sudo().search([("id", "=", int(palika_id))], limit=1)
            if not palika:
                raise ValidationError(f"No palika found with ID: {palika_id}")
            if company.palika.id != palika.id:
                values_to_update["palika"] = palika.id
        
        login_bg_img_company = request.httprequest.files.get("login_bg_img_company")
        login_bg_img_individual = request.httprequest.files.get("login_bg_img_individual")
        owner_citizenship_front = request.httprequest.files.get("owner_citizenship_front")
        owner_citizenship_back = request.httprequest.files.get("owner_citizenship_back")
        def encode_file(file):
            if file:
                return base64.b64encode(file.read())
            return False
        if login_bg_img_company:
            values_to_update["login_bg_img_company"] = encode_file(login_bg_img_company)
        if login_bg_img_individual:
            values_to_update["login_bg_img_individual"] = encode_file(login_bg_img_individual)
        if owner_citizenship_front:
            values_to_update["owner_citizenship_front"] = encode_file(owner_citizenship_front)
        if owner_citizenship_back:
            values_to_update["owner_citizenship_back"] = encode_file(owner_citizenship_back)
        # Check other fields for changes
        for field in fields_to_check:
            new_value = post.get(field)
            old_value = getattr(company, field, None)
            
            if str(new_value) != str(old_value):  # Compare values as strings to avoid type mismatches
                values_to_update[field] = new_value
            else:
                unchanged_fields.append(field)

        # Update company if there are changes
        if values_to_update:
            company.sudo().write(values_to_update)
            company.state = "resubmit"
            print("Updated fields:", values_to_update)
        else:
            print("No fields were changed.")

        print("Unchanged fields:", unchanged_fields)
        
        return request.render("base_accounting_kit.web_update_thank_you")  # Render a success/thank you page 
    
class DuplicateCheckController(http.Controller):

    @http.route('/check_duplicate', type="http", auth="public", methods=["POST"], csrf=False)
    def check_duplicate(self, **kwargs):
        value = kwargs.get('value')
        field = kwargs.get('field')
        model = kwargs.get('model')

        FIELD_LABELS = {
            'organization_name_en': 'Organization Name (English)',
            'organization_name_np': 'Organization Name (Nepali)'
        }

        # Check if the field has a custom label; fall back to a generic label
        friendly_field_name = FIELD_LABELS.get(field, field.replace("_", " ").capitalize())

        if not value or not field or not model:
            return request.make_response(
                json.dumps({'success': False, 'message': 'Invalid input: Missing required parameters.'}),
                headers={'Content-Type': 'application/json'},
                status=400
            )

        try:
            # Search for duplicates in the specified model
            Model = request.env[model].sudo()
            count = Model.search_count([(field, '=', value)])
            print("Count:", count)
            if count > 0:

                return request.make_response(
                json.dumps({
                    'success': True,
                    'duplicate': True,
                    'message': f'{friendly_field_name} already exists.'
                }),
                headers={'Content-Type': 'application/json'},
                status=200
                )
            else:
                return request.make_response(
                    json.dumps({'success': True, 'duplicate': False, 'message': 'No duplicate found.'}),
                    headers={'Content-Type': 'application/json'},
                    status=200
                )
        except Exception as e:
            return request.make_response(
                json.dumps({'success': False, 'error': str(e), 'message': 'An error occurred while checking for duplicates.'}),
                headers={'Content-Type': 'application/json'},
                status=500
            )