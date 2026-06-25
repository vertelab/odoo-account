# Plan: Klistermodul account_invoice_ai_3way_match

## Context

Två moduler finns idag som fungerar oberoende av varandra:

**`account_invoice_ai`** — AI-skannar PDF:er och mail, skapar leverantörsfakturor.
- `_process_file_content()` → AI → JSON → `_create_vendor_bill()`
- `match_purchase_order()` — letar inköpsorder via referens i PDF-texten, men **anropas endast i mailflödet** (`match_purchase_order=True`). **PDF-importen** (`account_invoice_import.py`) anropar `_process_file_content()` med `match_purchase_order=False`.

**`account_3way_match_ce`** — 3-vägsmatchning: inköpsorder vs inleverans vs faktura.
- `account.move.line.can_be_paid` — beror på `purchase_line_id` (jämför `qty_invoiced` vs `qty_received`).
- `account.move.release_to_pay` — aggregerar radstatus till yes/no/exception.
- **Kräver att fakturarader är kopplade till inköpsorderrader** för att fungera.

### Problemet

När `account_invoice_ai` skapar fakturor från PDF-import kopplas de **aldrig** till inköpsorder — `match_purchase_order` anropas inte. Därmed fungerar 3-vägsmatchningen inte alls för AI-skannade fakturor.

### Mål

En klistermodul `account_invoice_ai_3way_match` som:
- Auto-installerar om både `account_invoice_ai` + `account_3way_match_ce` finns
- Efter AI:n skapat en faktura: försöker hitta matchande inköpsorder och koppla rader
- Gör så att AI-skannade fakturor får korrekt `release_to_pay`-status

## Approach

Klistermodulen ska **inte** ändra någon befintlig modul. Den ska:

1. **Auto-installera** (`'auto_install': True`) med depends på båda modulerna
2. **Override:a `_process_file_content()`** på `ai.quest` — efter anrop till `super()`, kör `_try_match_purchase_order()`
3. **`_try_match_purchase_order(move_id, partner_id, invoice_data)`**:
   - Hitta öppna inköpsorder för partnern (ej fullt fakturerade)
   - För varje fakturarad, försök matcha mot PO-rader via:
     - `product_id` (om redan satt av `_invoice_lines`)
     - `_find_product()` på radens namn (återanvänd från `account_invoice_ai`)
     - Beskrivning/likhet
   - Sätt `purchase_line_id` på matchade fakturarader
   - Logga varning för omatchade rader
4. **Trigger omräkning** av `release_to_pay` efter koppling

## Files to create

```
account_invoice_ai_3way_match/
├── __init__.py
├── __manifest__.py
└── models/
    ├── __init__.py
    └── ai_quest.py        # override _process_file_content
```

## Reuse

| Vad | Var |
|-----|-----|
| `_find_product()` | `account_invoice_ai/models/ai_quest.py:198` — redan implementerad |
| `_guess_account_from_name()` | `account_invoice_ai/models/ai_quest.py:237` |
| `can_be_paid` / `release_to_pay` | `account_3way_match_ce/models/account_invoice.py` — triggas automatiskt vid `purchase_line_id`-sättning |
| `purchase_line_id` på `account.move.line` | Odoo core — standardfält |
| `find_partner_purchase_order()` | `account_invoice_ai/models/ai_quest.py` — söker PO via ref i text |

## Steps

- [ ] 1. Skapa modulstruktur: `__manifest__.py`, `__init__.py`, `models/__init__.py`, `models/ai_quest.py`
- [ ] 2. `__manifest__.py`: `'depends': ['account_invoice_ai', 'account_3way_match_ce']`, `'auto_install': True`
- [ ] 3. I `models/ai_quest.py`: ärv `ai.quest`, override `_process_file_content()`
  - Anropa `super()._process_file_content()` först (skapar fakturan)
  - Om `move_id` skapades: anropa `_try_match_purchase_order()`
- [ ] 4. Implementera `_try_match_purchase_order(self, move_id, partner_id)`:
  - Hitta PO:er för partnern med `invoice_status != 'invoiced'` och `state in ('purchase', 'done')`
  - För varje fakturarad utan `purchase_line_id`:
    - Om `product_id` finns på raden → matcha mot PO-rader med samma produkt
    - Annars → använd `_find_product(rad.name)` för att hitta produkt
    - Sätt `purchase_line_id` vid exakt produktmatch eller enda kandidat
  - Logga resultat (antal matchade / omatchade rader)
- [ ] 5. Testa: installera modulen (auto-install), skapa en PO, skanna en matchande PDF
- [ ] 6. Verifiera att `release_to_pay` sätts korrekt efter inleverans

## Flöde med attest och betalorder

Det tänkta flödet där attest (godkännande) och betalorder passar in:

```
1. AI scannar PDF          → leverantörsfaktura (utkast)
2. Klistermodul            → kopplar fakturarader till inköpsorderrader
3. Varumottagning          → inleverans registreras på inköpsordern
4. 3-vägsmatchning         → release_to_pay = yes / no / exception
5. ATTESTS (granskning)    → ansvarig person granskar & godkänner fakturan
6. Bokför fakturan         → postad (state = posted)
7. Betalorder              → fakturan inkluderas i betalningsfil till bank
```

Attesten placeras **efter** 3-vägsmatchningen men **före** bokföring:
- Granskaren ser release_to_pay-status (yes/no/exception)
- Är status "yes" → fakturan är OK att godkänna
- Är status "exception" → differens mellan beställt/levererat/fakturerat — granskaren måste utreda
- Är status "no" → inget levererat än — bör ej godkännas

Detta följer Odoos standardflöde: draft → attested → posted → payment.
`release_to_pay` blir ett beslutsstöd för attestanten.

## Testdata: Nordic Supplies AB / TechComponents

För att verifiera klistermodulen skapas testdata baserat på faktura INV-2024-0187
från loggen (`scalinq-ddata`).

### Leverantör (finns redan i loggen)
```
TechComponents Europe AB
Storgatan 15, 602 34 Norrköping
vat: ??? (AI:n hittade inte — får skapas manuellt)
```

### Inköpsorder PO-2024-0042
```python
# Produkter att skapa (om de inte finns):
products = [
    {'name': 'Intel Core i7-13700K Processor',   'default_code': 'CPU-I7-13700',  'standard_price': 3500},
    {'name': 'ASUS Z790-PRO WiFi Moderkort',      'default_code': 'MB-Z790-PRO',   'standard_price': 2900},
    {'name': 'Corsair Vengeance DDR5 32GB (2x16GB)', 'default_code': 'RAM-DDR5-32GB', 'standard_price': 1100},
    {'name': 'Samsung 990 Pro 2TB NVMe M.2 SSD',  'default_code': 'SSD-2TB-NVM',   'standard_price': 1600},
    {'name': 'Corsair RM850x 850W Gold PSU',      'default_code': 'PSU-850W-GLD',  'standard_price': 1300},
]

# PO rader med orderkvantiteter (enligt fakturan):
po_lines = [
    ('CPU-I7-13700',  10, 3895.00),
    ('MB-Z790-PRO',   10, 3295.00),
    ('RAM-DDR5-32GB', 18, 1295.00),
    ('SSD-2TB-NVM',   15, 1895.00),
    ('PSU-850W-GLD',  10, 1495.00),
]
```

### Inleverans (delvis — bara 3 av 5 produkter)
```python
# Simulerar att vissa produkter levererats, andra inte:
receipts = [
    ('CPU-I7-13700',  10),   # full leverans
    ('MB-Z790-PRO',   10),   # full leverans
    ('RAM-DDR5-32GB', 18),   # full leverans
    ('SSD-2TB-NVM',    0),   # ej levererad
    ('PSU-850W-GLD',   0),   # ej levererad
]
# Förväntat release_to_pay: exception (3 rader yes, 2 rader no)
```

### Verifieringssteg
1. Skapa produkterna ovan
2. Skapa partner "TechComponents Europe AB"
3. Skapa inköpsorder PO-2024-0042 med 5 rader
4. Bekräfta inköpsordern
5. Registrera inleverans för 3 av 5 produkter
6. Ladda upp PDF-fakturan via account_invoice_ai
7. Klistermodulen ska koppla fakturarader till PO-rader
8. `release_to_pay` ska bli `exception` (SSD och PSU ej levererade)
9. Efter komplett inleverans av resterande → `release_to_pay` = `yes`
10. Attest → posta → betalorder

## Verification

1. Installera `account_3way_match_ce` → modulen ska auto-installera om `account_invoice_ai` redan finns
2. Skapa en inköpsorder med 2 produkter, bekräfta
3. Ladda upp en PDF-faktura via `account_invoice_ai` för samma leverantör med matchande produkter
4. Kontrollera att fakturaraderna får `purchase_line_id` satt
5. Kontrollera `release_to_pay`:
   - Ingen inleverans → `no`
   - Inleverans av alla rader → `yes`
   - Delvis inleverans → `exception`
