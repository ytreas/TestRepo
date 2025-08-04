{
    "name": "khalti_payment",
    "author": "Bisesh Koirala",
    "version": "18.0",
    "category": "",
    'application': True,
    'sequence': 1,
    'depends': ['base','payment'],
    'data': [
        'views/payment_khalti_templates.xml',
        'data/payment_provider_data.xml',
        'views/payment_khalti_view.xml',
        'views/payment_khalti_transaction_views.xml',
        # 'views/remove_chatter.xml'
    ],
}


# providers = env['payment.provider'].search([('code', '=', 'khalti')])
# for provider in providers:
#     _logger.info(f"Syncing Khalti methods for provider: {provider.name}")
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

