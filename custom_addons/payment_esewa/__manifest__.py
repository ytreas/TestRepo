{
    "name": "esewa_payment",
    "author": "Bisesh Koirala",
    "version": "18.0",
    "category": "",
    'application': True,
    'sequence': 1,
    'depends': ['base','payment'],
    'data': [
        'views/payment_esewa_templates.xml',
        'data/payment_provider_data.xml',
        'views/payment_esewa_view.xml',
        'views/payment_esewa_transaction_views.xml'
    ],
}


# providers = env['payment.provider'].search([('code', '=', 'esewa')])
# for provider in providers:
#     _logger.info(f"Syncing Esewa methods for provider: {provider.name}")
#     methods = provider._get_supported_payment_methods()
#     for method in methods:
#         existing_method = env['payment.method'].search([('code', '=', method['code'])], limit=1)
#         if not existing_method:
#             env['payment.method'].create({
#                 'name': method['name'],
#                 'code': method['code'],
#             })
#             _logger.info(f"Created payment method: {method['name']} ({method['code']})")
#         else:
#             _logger.info(f"ℹPayment method already exists: {method['name']} ({method['code']})")

