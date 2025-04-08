{
    "name": "Nepali Date Localization",
    "author": "Shangrila Informatics",
    "version": "1.0",
    "category": "",
    'application': True,
    'sequence': 1,
    'depends': [
        'base',
        'web',
        'mail'
    ],
    'data': [
        # '/nepal_localization/static/src/save_discard.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            '/nepal_localization/static/src/datetime/nepaliDatePicker.js',
        ],
        'web.assets_backend': [
            '/nepal_localization/static/src/datetime/nepaliDatePicker.js',
            '/nepal_localization/static/src/datetime/nepaliDatePicker.css',
            '/nepal_localization/static/src/datetime/datetime.js',
            '/nepal_localization/static/src/datetime/datetime.xml',
        ]
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}