.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
Account: Tagetik Fields
=========================

Tagetik reporting fields on the chart of accounts and on journal items.

* Fields:
	- Tagetik Code
	- Tagetik Text

The fields are declared on ``account.account`` and read through to
``account.move.line`` (stored) and ``account.move`` (unstored). The field
names match the ones the retired Linserv module ``account_tagetik_fields``
used, so the values already stored in the database survive the swap.

Installation
============

Install the module. Existing Tagetik values on accounts are picked up as
they are: no migration step is needed.

Configuration
=============

Usage
=====

Known issues / Roadmap
======================

Changelog
======================

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/vertelab/odoo-account/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Vertel Sverige AB

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://vertel.se/logo.png
   :alt: Vertel Sverige AB
   :target: https://vertel.se

This module is maintained by Vertel Sverige AB.

To contribute to this module, please visit https://vertel.se
