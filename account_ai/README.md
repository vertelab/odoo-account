# Account AI — OKF-brygga

Domänbrygga mellan `odoo-account` och `ai_agent_core`. Lägger
`ai.okf.mixin` på `account.move` och `account.account` så att verifikatens
innehåll och kontoplanens betydelse blir sökbara OKF-koncept.

**Beroenden:** `ai_agent_core`, `account`. Inget annat — bryggan ska kunna
installeras på en ren `account`-installation, utan PDF-tolkning eller
LLM-beroenden (`account_invoice_ai` ligger medvetet utanför).

---

## Vad som indexeras

| Modell | Artifact type | Retention |
|---|---|---|
| `account.move` | `account_move` | `none`, 0 dagar |
| `account.account` | `account_account` | `accounting`, 0 dagar |

### `account.move` — kroppen är sammansatt

Den generiska `_okf_body_source()` räcker **inte** här. Den tar `name` +
HTML/Text, vilket för ett verifikat ger `"BILL/2026/11/0001"` plus
`narration` — och `narration` är företagets betalningsvillkor, identisk på
varje faktura. Kroppen överrids därför:

```
BILL/2026/11/0001
Vendor Bill
Part: Kalles AB
Datum: 2026-11-12
Belopp: 12500.00 SEK
Referens: SUP-1234

Hosting november — 6540 IT-tjänster — 10000.0
Konsultarvode — 6550 Konsultarvoden — 2500.0
```

Raderna är det egentliga innehållet: `name` är ett löpnummer, och *vad*
fakturan gäller står bara på raderna. Sektioner och noter
(`display_type in ('line_section','line_subsection','line_note')`) filtreras
bort — de är formatering.

### `narration` tas bara med när den avviker

`narration` jämförs mot `company_id.invoice_terms` efter HTML-normalisering
genom `_okf_html_to_text()`. Är de lika utelämnas den. En användare som
skrivit en **egen** not får den indexerad; 50 000 standardtexter gör det inte.

Utan denna spärr hade samtliga koncept matchat "dröjsmålsränta" och
vektorrummet hade kollapsat — kärnan mäter cosinus 0,99 för *orelaterade*
par på korta likartade texter.

### `account.account` — kroppen överrids också

`code` är ett **Char-fält** och ingår inte i mixinens generiska body (som tar
`name` + HTML/Text). Utan överridning blev kroppen `"IT-tjänster\n\nAnvänds
för molntjänster..."` — utan `6540`, vilket är det man skriver när man letar
efter ett konto. Mätt i test 2026-11-12.

Kroppen är därför `code` + `name` + `note`.

---

## Utkast indexeras

Både `draft` och `posted` indexeras. Utkast är det arbete användaren gör just
nu, och behovet ("vad är den här fakturan om?") är som störst *före*
bokföringen.

`_okf_is_ready()` implementeras **inte** — när både draft och posted släpps
igenom återstår bara `cancel` och fönstret, och båda hanteras av
`_okf_skip_reason()`.

| Tillstånd | Utfall |
|---|---|
| `draft` i fönstret | indexera |
| `posted` i fönstret | indexera |
| `cancel` | avför (`"annullerad"`), flaggan rensas |
| utanför fönstret | avför (`"utanför fönstret"`), flaggan rensas |

Fönstret prövas **före** allt annat: ett utkast från ett tidigare
räkenskapsår ska inte ligga och vänta för evigt.

---

## Indexeringsfönstret = aktuellt räkenskapsår

```python
bounds = self.company_id.compute_fiscalyear_dates(fields.Date.context_today())
return bounds['date_from'] <= (self.invoice_date or self.date) <= bounds['date_to']
```

⚠️ **Fällan som testet fångade (2026-11-12):** första versionen skickade
verifikatets *eget* datum till `compute_fiscalyear_dates()`. Den returnerar
räkenskapsåret som **innehåller** det datumet — så prövningen blev
`date_from <= date <= date_to` där `date_to` redan var beräknad ur `date`.
Alltid sant. En verifikation från 2023 ansågs ligga i fönstret.

Rätt fråga är "tillhör verifikatet det räkenskapsår som gäller **nu**?" —
alltså `date.today()`, inte verifikatets datum.

`compute_fiscalyear_dates()` finns i `account` core och läser bolagets
`fiscalyear_last_day`/`fiscalyear_last_month`, så brutet räkenskapsår
(maj–april) hanteras utan extra kod.

---

## Backfill

Menyn **Redovisning → Konfiguration → Backfill OKF**
(`account.group_account_manager`).

Wizarden söker `state in ('draft','posted')` inom intervallet (förvalt ur
bolagets aktuella räkenskapsår) och anropar `moves._set_okf_dirty()` —
mixinens publika väg, som flushar, tar radlås i stigande id-ordning och
skriver SQL.

⚠️ **Varför inte en migration:** Odoo initierar en ny Boolean-kolumn till
`NULL`, inte `False` (`_init_column`: `necessary = (value is not None) if
field.type != 'boolean' else value`). En domän på `[('okf_dirty','=',True)]`
fångar därför **inte** historiken, och en bred `UPDATE ... SET okf_dirty =
TRUE` skriver förbi både flush och låsordning. Mätt i `luke18_test`
2026-11-12: samtliga 24 verifikat hade `okf_dirty = TRUE` och 0 stod som
`NULL` — men bara för att `create()`-hooken satt dem; kolumnen hade aldrig
fått ett DB-default.

En `post_init_hook` vore dessutom en tidsinställd bomb på en kunddatabas med
100 000 verifikat.

---

## Kö-begränsning

| Modell | Indexerbar | Prioriterad |
|---|---|---|
| `account.move` | ja | **nej** |
| `account.account` | ja | **ja** |

`account.move` prioriteras inte: `_okf_priority_indexable()` garanterar en
andel varje cron-varv, och att ge den till verifikaten svälter
`user_mail_ai.mail` (som driver ett interaktivt sökfält). Fönstret gör kön
*ändlig*, och det är den riktiga lösningen.

`account.account` prioriteras: ~300–1 500 rader, ändras sällan, och är vad
AI-kategoriseringen faktiskt frågar efter.

### Mätt i `luke18_test` 2026-11-12

| Mått | Värde |
|---|---|
| Verifikat totalt | 24 |
| — varav `posted` | 23 |
| — varav `draft` | 1 |
| I fönstret (kalenderår 2026) | 22 (21 posted + 1 draft) |
| `okf_dirty = TRUE` efter testkörning | 24 |
| `okf_dirty = NULL` | 0 |

Cron-kvoten är `per_model = max(1, cap // 4)`. Med `cap = 500` blir det 125
per modell och varv, och `spare = 0` när fler än 4 modeller är registrerade —
modeller sent i rotationen får noll det varvet. Med ett räkenskapsårs
verifikat (~20 000 i en medelstor kunddatabas) tar tömningen ~160 varv ≈ 13
timmar, inte 1 600 varv (5,5 dygn) som utan fönster.

---

## ⚠️ Installation låser skrivningar

`okf_dirty` läggs av mixinen med `index=True`. `CREATE INDEX` **utan**
`CONCURRENTLY` låser skrivningar på `account.move` under modulinstallationen.

| Radantal i `account.move` | Åtgärd |
|---|---|
| < 100 000 | Installation direkt — indexet byggs på sekunder |
| ≥ 100 000 | Gör det i underhållsfönster |

Indexet ägs av `ai_agent_core` (mixinens fält), inte av denna brygga — men
det är denna modul som först lägger fältet på `account.move`.

---

## Kända begränsningar

**Stale vid direkt `line.write()`.** `write()`-hooken i mixinen tänder bara
på fält som finns på **posten själv** (`if dirty_fields & set(vals)`). Att
ändra en radetikett via `move.write({'invoice_line_ids': ...})` täcks (det är
den vanliga UI-vägen), men en bar `line.write()` på `account.move.line`
tänder ingen flagga — konceptet fortsätter säga det gamla.

Accepterat: att hooka `account.move.line.write` vore ny kod i en brygga som
ska deklarera ett kontrakt, och den skulle tända vid varje radskrivning
inklusive avstämning och betalningskoppling. Fångas av att verifikatets
`write_date` ändras vid nästa redigering.

**`title` för bokförda verifikat** blir `BILL/2026/11/0001` — kärnan använder
`display_name` och kapar till 120 tecken. Utkast får `"Draft Bill (SUP-1234)"`
eftersom `_get_move_display_name()` lägger på `ref` när `name` är `/`.
`summary` bär beskrivningen; `title` är identiteten.

**Sökning sker på body, inte summary.** Radtexten ligger i konceptets
`source_text` — som tillsammans med `summary` och `title` bygger
`search_vector` (GIN, svensk stemming). `_okf_search('Hosting november')`
hittar fakturan; `concept.summary` innehåller den inte.

---

## Felsökning

| Problem | Orsak | Åtgärd |
|---|---|---|
| Inga koncept skapas | Posterna utanför fönstret | Kör backfill för rätt intervall |
| Konceptet säger gammalt radinnehåll | Direkt `line.write()` | Redigera verifikatet, eller kör backfill |
| Alla koncept matchar "betalningsvillkor" | `narration`-jämförelsen slog fel | Kontrollera att `company_id.invoice_terms` är satt |
| `_okf_in_window()` alltid True | Skickar verifikatets datum istället för idag | Se avsnittet om fönstret ovan |

Debug: **OKF**-valet i skalbaggen (debug-läge) på ett verifikat eller konto
visar `okf_body`, `okf_summary`, `okf_links` och konceptet.
