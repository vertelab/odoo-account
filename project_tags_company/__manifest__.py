{
    "name": "Project Tags Company",
    "version": "1.0",
    "summary": "Add company_id to project.tags",
    "category": "Technical",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/project_tags_company",
    "license": "LGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds a company on project tags, so each company has its own tag list, and a multi-company rule.",
    "depends": [
        "project"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "data": [
        "security/ir_rule.xml"
    ]
}
