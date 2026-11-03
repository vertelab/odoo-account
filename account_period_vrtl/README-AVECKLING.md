# Avveckling av `account_period_vrtl` → `account_fiscal_year_vrtl`

**Status:** genomförd i staging (`sfa18-test` / Komits staging). **Inte genomförd i production.**

**Dokumenterad:** 2026-11-03

---

## Bakgrund

`account_period_vrtl` är DEPRECATED sedan 2026-10-30 (commit `0561682`) och
ersätts av `account_fiscal_year_vrtl` + OCA `account_fiscal_year` +
`l10n_se_account_fiscal_year`.

Modulerna **kan inte vara laddade samtidigt** — de äger samma modellnamn:

| Modell | `account_period_vrtl` | `account_fiscal_year_vrtl` |
|---|---|---|
| `account.period` | egen modell | delegerad från `date.range` |
| `account.fiscalyear` | egen modell | — (ersatt av OCA `account.fiscal.year`) |
| `account.move.period_id` | definierar | **tar bort** |
| `account.move.line.fiscalyear_id` | definierar (→ `account.fiscalyear`) | **tar bort** |

Att ha båda på `addons_path` räcker för konflikt: Python-filerna laddas i
modulgrafen även när modulen är `uninstalled`.

---

## Symptom som uppstod (staging 2026-11-03)

Felen flyttade sig mellan olika core-moduler eftersom de rapporteras på den vy
som råkar valideras först. Alla var symtom på samma sak.

### 1. `Field "module_account_period_vrtl" does not exist`

```
Field "module_account_period_vrtl" does not exist in model "res.config.settings"
while parsing .../project_timesheet_holidays/views/res_config_settings_views.xml:4
```

senare samma fel men rapporterat på `sale_management`.

**Orsak:** en kvarlämnad `ir.ui.view` i databasen refererade
`module_account_period_vrtl`. Fältet skapas aldrig av Odoo när modulen är
**installerad** (bara för `uninstalled` + `installable`).

Den skyldiga vyn:

```
ir_ui_view.id = 3831
xmlid          = l10n_se_extended.res_config_settings_view_form_swedish_accounting
arch_db        innehöll <field name="module_account_period_vrtl"/> i blocket
                 "Period & Closing" / setting id="account_period_vrtl_setting"
```

Koden på disk (`l10n_se_extended/models/res_config_settings.py`) deklarerar
`module_account_fiscal_year_vrtl` — vyn i DB var alltså äldre än koden.
`l10n_se_extended`s manifest laddar **ingen** settings-vy, så vyn kunde aldrig
uppdateras. Klassisk limbo.

**Åtgärd:** vyn raderades ur databasen.

### 2. `ValueError: Wrong value for account.move.line.fiscalyear_id`

```
ValueError: Wrong value for account.move.line.fiscalyear_id: account.fiscal.year()
```

**Orsak:** `account_period_vrtl/models/account_move_line.py` deklarerar

```python
fiscalyear_id = fields.Many2one(
    comodel_name='account.fiscalyear',
    related='move_id.period_id.fiscalyear_id',
    store=True, readonly=True)
```

men `period_id` har tagits bort från `account.move` av
`account_fiscal_year_vrtl`, och `account.fiscalyear` existerar inte längre.
Typkrock → `ValueError` under `init_models`.

### 3. `UniqueViolation` på `date_range_type_date_range_type_uniq`

```
duplicate key value violates unique constraint "date_range_type_date_range_type_uniq"
Key (name, company_id)=({"en_US": "Fiscal Year"}, 1) already exists
while parsing .../l10n_se_date_ranges/data/date_range_type_data.xml:4
```

**Orsak:** `l10n_se_date_ranges` är **ersatt** av `l10n_se_account_fiscal_year`
(se `l10n_se_account_fiscal_year/hooks.py`). Båda var installerade och ägde
samma fyra `date.range.type`-poster.

**Åtgärd:** `l10n_se_date_ranges` avinstallerades. Xmlid:na ägs nu korrekt av
`l10n_se_account_fiscal_year`:

```
l10n_se_account_fiscal_year | date_range_type_fiscalyear | 1 | Fiscal Year
l10n_se_account_fiscal_year | date_range_type_month      | 3 | Month
l10n_se_account_fiscal_year | date_range_type_quarter    | 2 | Quarter
l10n_se_account_fiscal_year | date_range_type_week       | 4 | Week
```

---

## Vad som genomfördes i staging

1. Den kvarlämnade settings-vyn (id 3831) raderades ur databasen
2. `l10n_se_date_ranges` avinstallerades
3. Uppgraderingen gick igenom
4. `account_fiscal_year_vrtl` installerades

### Verifierat läge efter uppgradering (staging)

| Tabell | Rader |
|---|---|
| `date_range` | 138 |
| `date_range_type` | 4 |
| `account_fiscal_year` | 0 |
| `account_period` | 0 |
| `account_fiscalyear` (gamla) | 0 |

`date_range`-posterna genererades av
`l10n_se_account_fiscal_year._generate_swedish_date_ranges` (förra/innevarande/
nästa år). Men `account.period` är tom — delegering (`_inherits`) skapar inte
automatiskt `account.period` för befintliga `date.range`.

---

## Kvar att göra i staging

- [ ] Skapa fiscal year + perioder via ORM (se nedan)
- [ ] Avinstallera `account_period_vrtl`
- [ ] Verifiera att `account.fiscalyear` är borta ur registret
- [ ] Sätt `installable = False` i `account_period_vrtl/__manifest__.py` i
      `sfa-ce-18-addons-lib` (Komits kopia har fortfarande `True`)

---

## Produktion — ännu EJ genomfört

### Utgångsläge

`account_fiscalyear` och `account.fiscal.year` är **båda tomma** i production.
Modulen har alltså aldrig använts för räkenskapsår → **inget att migrera**.

Det gör avvecklingen säker, men det innebär också att räkenskapsår och perioder
måste skapas på nytt i den nya modellen.

### Två modeller existerar parallellt

| Modell | Modul | Roll |
|---|---|---|
| `account.fiscal.year` | OCA `account_fiscal_year` | **ny** — behåll |
| `account.fiscalyear` | `account_period_vrtl` | **gammal** — försvinner vid avinstallation |

### Rekommenderad ordning för production

```
1. BACKUP
   pg_dump -Fc <db> > /srv/backup/<db>_pre_period_vrtl_$(date +%F).dump

2. Kontrollera modulläget
   SELECT name, state FROM ir_module_module
   WHERE name IN ('account_period_vrtl','account_fiscal_year_vrtl',
                  'l10n_se_account_fiscal_year','l10n_se_date_ranges',
                  'l10n_se_sie','l10n_se_tax_account','l10n_se_tax_report');

3. Kontrollera kvarlämnade vyer som refererar period-fält
   SELECT v.id, v.name, d.module, d.name AS xmlid
   FROM ir_ui_view v
   LEFT JOIN ir_model_data d ON d.model = 'ir.ui.view' AND d.res_id = v.id
   WHERE v.arch_db::text LIKE '%module_account_period_vrtl%'
      OR v.arch_db::text LIKE '%period_closing_date%';

   → radera de som inte längre har stöd i koden

4. Avinstallera l10n_se_date_ranges (om installerad — ersatt av
   l10n_se_account_fiscal_year)

5. Installera account_fiscal_year_vrtl
   → post_init_hook _migrate_from_account_period_vrtl körs.
     Hooken kräver att account_period_vrtl ÄR installerad vid körningen,
     annars returnerar den tidigt utan att migrera.

6. Verifiera
   SELECT count(*) FROM account_fiscal_year;
   SELECT count(*) FROM account_period;

7. Avinstallera account_period_vrtl

8. Sätt 'installable': False i account_period_vrtl/__manifest__.py
   ⚠ GÖR DETTA FÖRST EFTER STEG 7.
   installable=False medan modulen är installerad kraschar registry-bygget
   (se commit 57fba22 — /web/login gav RemoteDisconnected på dina).
```

### Skapa räkenskapsår i nya modellen (ORM)

`account.fiscal.year` har `create_period(interval=1)` som skapar både
fiscal year och månadsperioder (12 st `date.range` + 12 st `account.period`):

```python
fy = env['account.fiscal.year'].create({
    'name': '2026',
    'date_from': '2026-01-01',
    'date_to': '2026-12-31',
    'company_id': 1,
})
fy.create_period(interval=1)
```

**Använd ORM, inte SQL** — `create_period` sätter delegering (`_inherits`),
`mail.thread`-tracking och triggar `_check_dates` / `_check_no_overlap`.

⚠ `create_period` skapar **nya** `date.range` med namn `M{yymm}`. Om året redan
har ranges från `l10n_se_account_fiscal_year` blir det dubbletter. Kontrollera:

```python
env['date.range'].search_count([
    ('date_start', '>=', '2026-01-01'),
    ('date_start', '<=', '2026-12-31'),
])
```

Är det redan 12+ ranges för året: koppla befintliga `date.range` till
`account.period` istället för att skapa nya.

---

## Fällor att komma ihåg

1. **`installable = False` + installerad modul = registry-krasch.**
   Flaggan får bara sättas i samma deploy som avinstallationen.

2. **Modulens `state` styr inte vilka Python-filer som laddas** — bara
   `installable` och närvaro på `addons_path`. Därför kan en `uninstalled`
   modul krascha registret.

3. **Vyradering i manifestet raderar inte vyn i databasen.** `ir.ui.view` och
   dess `ir.model.data`-xmlid ligger kvar och laddas vid uppgradering. Det är
   detta som ger "limbo"-felen som flyttar sig mellan core-moduler.

4. **Tracebacken pekar på fel modul.** Felet rapporteras på den vy som
   valideras först i grafen, inte på den vy som äger den felande referensen.

5. **`module_*`-fält skapas bara för `uninstalled` + `installable` moduler.**
   En installerad modul har inget `module_<name>`-fält — en vy som refererar
   det kraschar.

6. **`l10n_se_date_ranges` är ersatt** av `l10n_se_account_fiscal_year`. Båda
   installerade = `UniqueViolation` på `date_range_type_date_range_type_uniq`.

---

## Referenser

- Commit `0561682` — `account_fiscal_year_vrtl` porterad till Odoo 18
- Commit `baddafe` — Odoo-14 → Odoo-18-port av fiscal year-modulerna
- Commit `57fba22` — `installable = False` kraschade registryt på `dina`
- Commit `abdc363` — ursprunglig avveckling av `account_period_vrtl`
- `l10n_se_account_fiscal_year/hooks.py` — `_pre_init_adopt_legacy_types`
- `account_fiscal_year_vrtl/hooks.py` — `_migrate_from_account_period_vrtl`
