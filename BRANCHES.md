# Grenar i `odoo-account`

Inventering 2026-11-17 av alla 33 grenar på `origin`. Tio lever vidare som
utgåvor, tjugotre raderas efter att deras unika moduler portats eller
klassats som döda.

Se `openspec/changes/branch-cleanup-odoo-account/` för besluten bakom.

## Levande grenar (10)

| Gren | Utgåva | Sista commit | Moduler | Not |
|---|---|---|---|---|
| `10.0` | Odoo 10 | `15f55d90` 2021-06-18 | 6 | Het `master10` fram till namnbytet |
| `12.0` | Odoo 12 | `7c27c51f` 2023-03-24 | 11 | Återställs till sin sista riktiga commit |
| `13.0` | Odoo 13 | `b2446a24` 2021-05-18 | 1 | Återställs |
| `14.0` | Odoo 14 | `edc5f89e` 2026-02-10 | 69 | Återställs |
| `16.0` | Odoo 16 | `2f9c2c58` 2025-05-27 | 29 | Återställs |
| `17.0` | Odoo 17 | `0b9f1a77` 2025-03-07 | 10 | Återställs |
| `18.0` | Odoo 18 | — | 99 | **Förlagan.** P-filerna skapas här |
| `19.0` | Odoo 19 | — | 99 | Expanderad från 18.0 |
| `20.0` | Odoo 20 | — | 99 | Expanderad från 18.0 (+`.github` CI) |
| `neonomics` | Odoo 14 | `34234c6d` 2024-01-10 | 48 | Bevaras som referens |

### Varför de fem återställs

Grenarna `12.0`, `13.0`, `14.0`, `16.0` och `17.0` har fått p-fil-synk från
18.0. Synk-commitens meddelande säger "Do not p-file sync" — men synken skrev
ändå. Resultatet: `12.0` HEAD innehöll 25 modulkataloger varav **7 helt
tomma** (bara `static/description/index.html`) och 8–14 med 18.0-kod.

| Gren | Förorenad av | Sista riktiga commit | Moduler då |
|---|---|---|---|
| `12.0` | 59 synk-commits | `7c27c51f` 2023-03-24 | 11 |
| `13.0` | 36 synk-commits | `b2446a24` 2021-05-18 | 1 |
| `14.0` | 194 synk-commits | `edc5f89e` 2026-02-10 | 69 |
| `16.0` | 268 synk-commits | `2f9c2c58` 2025-05-27 | 29 |
| `17.0` | 41 synk-commits | `0b9f1a77` 2025-03-07 | 10 |

En klon av dessa grenar från före återställningen är divergerad.

## Raderade grenar (23)

Kvarlevorna finns i git-historiken via commit-hashen nedan
(`git show <sha>:<modul>/`).

### 12.0-derivat

| Gren | Sista commit | Moduler | Unika | Klassning |
|---|---|---|---|---|
| `12.0-SFM-Multicompanyfix` | `8c095b04` 2022-03-31 | 9 | 7 | Alla döda/ersatta |
| `12.0-af` | `fc2abfcd` 2021-06-07 | 8 | 6 | Samma |
| `12.0-test` | `fc2abfcd` 2021-06-07 | 8 | 6 | Samma |
| `12to14-port` | `69389f36` 2023-06-02 | 12 | 9 | Ovan + `account_fortnox_merged` (död) |
| `Dev-12.0-Fenix-Sprint-02` | `d36b2f72` 2021-06-30 | 9 | 7 | Ovan + `bank_test_data` (död) |
| `Dev-12.0-SFM-partner_paid_invoice` | `2bec9095` 2021-04-29 | 9 | 7 | Ovan + `partner_paid_invoice` (död) |
| `account_move_attachment` | `721f4373` 2022-12-08 | 11 | 8 | Samma som 12.0 |
| `fortnox-latest-auth0` | `3b182c8c` 2023-11-07 | 11 | 8 | Samma som 12.0 |
| `fortnox-membership-upgrade` | `cafb4ab9` 2023-11-07 | 11 | 8 | Samma som 12.0 |
| `master` | `f47f991d` 2020-02-28 | 4 | 4 | Alla döda — Odoo 7/8 |

### 14.0-derivat

| Gren | Sista commit | Moduler | Unika | Klassning |
|---|---|---|---|---|
| `14-enableBanking-2.0-hassan` | `52aacbd7` 2023-12-22 | 47 | 2 | `account_period`, `account_period_financial_report` (ersatta) |
| `14-enablebanking-2.0` | `67ff33d1` 2023-12-27 | 47 | 2 | Samma |
| `14.0-multi-userattestering` | `823a2490` 2022-05-04 | 15 | 1 | `account_period` (ersatt) |
| `14.0_before_removed_merged` | `13c92038` 2023-01-09 | 33 | 1 | `account_period` (ersatt) |
| `fintecture-2.0` | `87830cc3` 2024-02-16 | 48 | 3 | `account_fintecture` (död) |
| `forecast_wizard` | `4cedb817` 2024-02-23 | 51 | 5 | Se "Portade moduler" |
| `on_sync_redirect` | `4e3d6533` 2023-12-22 | 47 | 2 | `account_period` m.fl. (ersatt) |
| `saltedge` | `3cf0595d` 2024-02-02 | 49 | 4 | `account_saltedge`, `account_neonomics` (döda) |

### 16.0- och 18.0-derivat

| Gren | Sista commit | Moduler | Unika | Klassning |
|---|---|---|---|---|
| `16.0-attachment` | `f85d6946` 2025-05-16 | 28 | 12 | Se "Portade moduler" |
| `17.0-commercieal_partner` | `eeb4e496` 2024-06-03 | 4 | 0 | Inga unika |
| `18.0-evaluate-account_period_vrtl_minimal` | `4f298800` 2025-11-20 | 29 | 0 | Inga unika |
| `18.0fiscal_year` | `bb8d10cd` 2026-07-08 | 56 | 3 | Se "Portade moduler" + `.shazam` |
| `lijuan-18` | `7092ab43` 2025-04-17 | 14 | 1 | `account_period_vrtl_balance` (död — WIP) |

## Portade moduler

Fjorton moduler med verkligt innehåll fanns bara på grenar som raderas. De
porterades till `18.0` innan respektive gren togs bort.

| Modul | Källa | Rader kod | Vad den gör |
|---|---|---|---|
| `account_move_report` | `14.0` | 224 | Verifikationsutskrift (konto, partner, analytik, debet, kredit, moms) |
| `account_invoice_multi_currency` | `14.0` | 1314 | Faktura-PDF med totaler i flera valutor |
| `account_notice_period` | `14.0` | 154 | `notice_period_note` på betalningsvillkor, i fakturafoten |
| `account_reconciliation_widget_journal` | `14.0` | 112 | Journal- och datumfilter i avstämningswidgeten |
| `account_mis_period_wizard` | `14.0` | 150 | "Ingående balans"-jämförelse i MIS Builder |
| `account_asset_management_component` | `16.0` | 274 | Komponentavskrivning (`asset.parent`) |
| `account_asset_management_report` | `16.0` | 147 | "Depreciation Board"-pivot |
| `account_analytic_tier_validation` | `16.0` | 253 | "Cost Center Reviewers" från `analytic_distribution` |
| `account_move_type_group` | `16.0` | 209 | Behörighetsgrupper per verifikationstyp |
| `account_mis_cash_flow_extended` | `16.0` | 760 | Kassaflödesprognos |
| `account_fortnox_delivery` | `16.0` | 158 | `WayOfDelivery` till Fortnox |
| `account_export_import_invoice` | `16.0` | 289 | XML-import och XML-export av verifikationer |
| `project_tags_company` | `18.0fiscal_year` | 37 | `company_id` på `project.tags` |
| `res_config_quests` | `18.0fiscal_year` | 22 | `quests`-fält på `res.config.settings` |

### `project_tags_company` och `res_config_quests` raderades av misstag

Båda skapades i `339cbbf1` (2026-06-25) och raderades i `5945a858`
(2026-09-25) — en commit med ämnet *"chore(assets): remove junk images and fix
module descriptions"*. Utöver 137 bildfiler tog den två hela moduler.

De fanns bara på `18.0fiscal_year`, som grenade ut vid `f9d1c571` (2026-07-07)
— före städningen. Därför kunde de återfinnas och portas.

## 12.0:s åtta unika moduler

| Modul | Klassning | Ersättare / motivering |
|---|---|---|
| `account_fortnox_config` | Ersatt | 18.0:s `account_fortnox` (OAuth flyttad till `res.company`) |
| `account_invoice_qr` | Död | QR-koden är en platshållare — koden innehåller strängen `"Bild på qr-kod!"`, ingen QR-generering |
| `account_move_attachment` | Död | Modellen är tom (bara `_name` och `_inherit`) |
| `account_period` | Ersatt | 18.0:s `account_fiscal_year_vrtl` — se "Kända luckor" |
| `account_subscription` | Ersatt | OCA `account_move_template` (18.0) har samma koncept: mall → verifikation |
| `currency_rate_update_seb` | Död | Skrapar `seb.se/pow/apps/Valutakurser/avista_tot.asp`, en URL som inte finns |
| `currency_rate_update_swea` | Död | Riksbankens SWEA-SOAP är nedlagd |
| `multi_company_dependent_attribute_res_partner` | Död | Beror på `company_dependent_attribute`, som inte finns i något repo |

## Döda moduler som inte portades

| Modul | Källa | Motivering |
|---|---|---|
| `account_fortnox_merged` | `12to14-port` | Gammal merge; ersatt av `account_fortnox` |
| `bank_test_data` | `Dev-12.0-Fenix-Sprint-02` | Ren testdata (PG/BG-banker) |
| `partner_paid_invoice` | `Dev-12.0-SFM-partner_paid_invoice` | 12.0-API (`@api.multi`), kräver omskrivning |
| `account_fintecture` | `fintecture-2.0` | Open banking-API; Enable Banking valdes |
| `account_saltedge` | `saltedge` | Open banking-API; Enable Banking valdes |
| `account_neonomics` | `neonomics`, `saltedge` | Tomt scaffold: `'name': ''`, `'depends': []`, modellen utkommenterad |
| `account_period_vrtl_balance` | `lijuan-18` | WIP: bara kundfakturor, ingen kontohänsyn |
| `account_financial_report_webkit_extras` | `master` | OpenERP 7/8 (`__openerp__.py`) |
| `account_financial_report_webkit_xls_extras` | `master` | OpenERP 7/8 |
| `account_invoice_follower` | `master` | OpenERP 7/8 |
| `account_invoice_round` | `master` | OpenERP 7/8; Odoo 18 har `account_cash_rounding` |
| `upload_voucher_pro` | `master10` | Beror på `project_issue_account` (Odoo 8) |
| `account_invoice_qr` (10.0) | `master10` | Samma platshållare som i 12.0 |
| `currency_rate_update_seb` (10.0) | `master10` | Samma döda URL |
| `currency_rate_update_swea` (10.0) | `master10` | Samma nedlagda SOAP |

## Kända luckor

Saker som inte är grenfrågor men som upptäcktes vid inventeringen.

### `account_move_tier_validation` existerar inte

Verifierat 2026-11-17:

```
git log --all --oneline -- account_move_tier_validation/              → 0
find /usr/share -maxdepth 3 -type d -name account_move_tier_validation → 0
grep -c account_move_tier_validation oca.repo                         → 0
alla 33 grenar, git ls-tree -d                                       → 0
```

Fyra moduler i 18.0 beror på den och är därför `installable: False`:
`account_move_tier_validation_implement`, `_control`, `_report`,
`tier_all_validations_required`. `account_analytic_tier_validation` portades
med `base_tier_validation` som direkt bas i stället.

### Öppningsperioden — stängd 2026-11-17

`account_period_vrtl` (avvecklad) hade `special` — en period som fick
överlappa den första månadsperioden, avsedd för ingående balans.
`account_fiscal_year_vrtl` hade ingen sådan. Fältet, undantaget i
`_check_no_overlap`/`_check_dates` och `create_opening_period()` är nu i
ersättaren. Se `account_period_vrtl/README-AVECKLING.md`.

### `account_inexchange` är blockerad

`installable: False`. Orsak: `account_invoice_ubl` → `base_ubl` →
`pdf_helper/models/helper.py:6` importerar `PyPDF2.utils`, som togs bort i
PyPDF2 3.0. `pdf_helper` är en OCA-modul.

### `account_fiscal_year_mis` är blockerad i praktiken

`installable: True` men beror på `account_fiscal_year_closing`, som finns i
`OCA/account-closing` (rad 8 i `oca.repo`) men inte är klonad till
`/usr/share/odooext-OCA-account-closing`.

### `base_tier_validation_report` finns inte i OCA 18.0

Fanns i `OCA/server-ux` 16.0, borta i 18.0. Blockerar de fyra tier-modulerna
ytterligare.
