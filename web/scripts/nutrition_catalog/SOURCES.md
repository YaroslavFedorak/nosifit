# Data sources and licences

The system product catalog (`products.json`) is built by `build_catalog.py`
from the sources below. Each product records which source row its values
come from (`source.dataset` + `source.ref`, also stored in
`nutrition_products.data_source` / `source_ref`). Raw source files are not
committed; download them from the links below to rebuild.

## ANSES-CIQUAL 2020 — French food composition table

- Source: Anses. 2020. Ciqual French food composition table.
  <https://ciqual.anses.fr/>
- Version used: Table Ciqual 2020, last updated 2020-07-07.
- Licence: Licence Ouverte / Open Licence version 2.0 (Etalab),
  <https://www.etalab.gouv.fr/licence-ouverte-open-licence>.
- Used for: products with `data_source = ciqual_2020` (`source_ref` =
  CIQUAL `alim_code`).
- Changes made: values are re-expressed per the conventions in
  `build_catalog.py` (e.g. "traces" = 0, "< x" = x/2 or 0 for pure fats,
  energy computed with EU factors when missing). Every changed value is
  listed in the product's `derived` field. These derived values are
  NosiFit's, not ANSES's.

## USDA FoodData Central — SR Legacy (April 2018)

- Source: U.S. Department of Agriculture, Agricultural Research Service.
  FoodData Central, SR Legacy, 2018. <https://fdc.nal.usda.gov/>
- Licence: CC0 1.0 (public domain); attribution given as a courtesy.
- Used for: products with `data_source = usda_sr_legacy` (`source_ref` =
  `fdc_id`). Carbohydrate is converted to available carbohydrate
  (fiber subtracted) and salt is derived from sodium; see `derived`.

## Open Food Facts — manufacturer labels

- Source: Open Food Facts contributors, <https://world.openfoodfacts.org/>.
  Each record in `label_data.json` links to its product page.
- Licence: the database is available under the Open Database License
  (ODbL) 1.0, <https://opendatacommons.org/licenses/odbl/1-0/>; individual
  contents under the Database Contents License (DbCL) 1.0,
  <https://opendatacommons.org/licenses/dbcl/1-0/>.
- Used for: products with `data_source = open_food_facts` (`source_ref` =
  barcode), nine Ukrainian staples the composition tables lack. Values are
  copied as printed on the label; `label_data.json` is the extract and,
  with those records, remains available under the ODbL.

## NosiFit recipe calculations

- `data_source = nosifit_recipe`: values calculated from the listed catalog
  ingredients (`recipes.json`). Typical home recipes are estimates
  (`verified = false`); exact blends (e.g. milk standardised to 2.5 % fat)
  are marked `verified = true`.

## Open Food Facts — barcode scans (runtime)

Products a user scans that are not in the catalog are looked up live in
Open Food Facts (`GET /api/v2/product/<barcode>`, only the fields NosiFit
needs, identified by `OFF_USER_AGENT`). After the user reviews and adds one,
it is stored as that user's own (private, editable) product with
`data_source = open_food_facts`, `source_ref` = barcode and `verified = false`.

- Licence: the same as above — database ODbL 1.0, contents DbCL 1.0. Such
  rows stay available under the ODbL; the scanner shows the attribution
  "Data: Open Food Facts, ODbL licence" with every external result.
- Changes made: values are normalized to NosiFit's per-100 g convention
  (per-serving values converted with the label's serving size, kJ → kcal,
  sodium × 2.5 → salt, drinks per 100 ml logged in ml). Implausible values
  are rejected, never clamped; missing values stay unknown. Product images
  are not requested or stored.
