# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "DAFA Bank Test Data",
    "version": "12.0.1.0.1",
    "author": "Vertel AB",
    "license": "AGPL-3",
    "website": "https://vertel.se/",
    "description": """
        This module adds testdata to be used in the KVL and STOM-projects. 
        The source of the data is here: https://confluence.ams.se/pages/viewpage.action?pageId=76597519
    """,
    "category": "Tools",
    "depends": [
        "base",
        "contacts",
        "partner_test_data",
    ],
    "external_dependencies": [],
    "data": [
        'data/bank_data.xml',
    ],
    "application": True,
    "installable": True,
}
