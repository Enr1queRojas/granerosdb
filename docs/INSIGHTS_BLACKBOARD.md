# INSIGHTS_BLACKBOARD

This document serves as the technical log of approaches, data patterns discovered, transformation logic, and business insights. It acts as the "source of truth" for technical decisions throughout the project lifecycle.

## 1. Discovery Findings
**Environment details identified:**
- **Database Engine**: Microsoft SQL Server Express Edition (64-bit) v16.0.4240.
- **Host Platform**: Windows Server 2019 Datacenter.
- **Target Database**: `granerosguerra_copiaenrique`.
- **Connection Insight**: The DB is hosted on a remote IP (52.249.30.165), not localhost. It uses SQL Server Authentication.

*Pending structural extraction (Tables, Columns).*

## 2. Entity Mapping (Facts & Dimensions)
### Dimension Tables (Catalogs)
- **Primary Pattern**: Prefix `CATALOGO_*_DATA` with `CODIGO` as the Primary Key (Type: `nvarchar`).
- **Core Entities**:
  - `CATALOGO_CLIENTES_DATA`, `CATALOGO_PROVEEDORES_DATA`, `CATALOGO_PRODUCTORES_DATA`
  - `CATALOGO_PRODUCTOS_DATA`, `CATALOGO_INSUMOS_DATA`
  - `CATALOGO_BANCOS_DATA`, `CATALOGO_TRANSPORTISTAS_DATA`, `CATALOGO_CONTADORES_DATA`
- **Other Lookups**: `TEMPORADAS_DATA`, `DESTINOS_CLIENTES`, `PROPIEDADES_DATA`, `LOGIN_ACCESS_DATA`

### Fact Tables (Transactions)
- **Primary Pattern**: Suffix `_DATA` with `ID` as the Primary Key (Type: `bigint`). Denormalized structures containing fields like `ESTADO`, `RESPONSABLE`, `TIPODOC`, `FECHA`, `FOLIO`.
- **Core Sales & Receivables**: `CREDITO_DATA`, `CONTADO_DATA`, `COBRANZA_DATA`, `DEV_VENTA_DATA`
- **Core Purchases & Payables**: `COMPRAS_DATA`, `PAGO_PROVEEDOR_DATA`, `PAGO_PRODUCTO_ALMACEN_DATA`
- **Logistics & Ops**: `TRANSPORTE_DATA`, `MANIOBRAS_DATA`, `BOLETA_ENTRADA_DATA`, `CRIBA_DATA`, `PROCESOS_DATA`
- **Finance & Expenses**: `GASTOS_DATA`, `RENTAS_DATA`, `TRANSFERENCIAS_BANCOS_DATA`, `PRESTAMO_DATA`
- **Temp / Bulk Tables**: `CARGA_MASIVA_*` tables used for temporary integration storage.

## 3. Dark Data, Anomalies & Transformation Needs
- **Referential Integrity**: Missing explicit SQL Foreign Key constraints. Relationships mapping `CLIENTE` to `CATALOGO_CLIENTES_DATA.CODIGO` exist via application logic, not database constraints.
  - *Data Integrity Risk*: High risk of orphaned records due to application-level referential integrity. We need to perform "Left Join Audit" to find Fact rows without matching Dim rows.
- **Naming Conventions**: Spaces in column names exist in several tables (e.g., `FORMA DE PAGO`, `CONCEPTO DIVERSO`, `BANCO ORIGEN`). 
  - *Syntax Alert*: All SQL queries must use square brackets `[ ]` for column names (e.g., `[FORMA DE PAGO]`).
- **Nullability**: Critical numeric columns like `TOTAL` and `BULTOS` are set to `Nullable: YES`. 
  - *Null Strategy*: Global policy for `TOTAL` and `BULTOS`: `ISNULL(column, 0)` in MSSQL or `COALESCE` in Python.
- **Auditing Columns**: Extensive use of `INSERTION_DATE`, `MODIFIED_DATE`, and `NOTE_DATE` for auditing in fact tables.

## 3. Transformation Logic & Design Decisions
*Log of applied data cleaning rules, pipeline architecture logic, and justification for specific transformations.*

## 4. Business Insights & EDA Notes

### 4.1 EDA - Data Quality & Sanity Check
- **Target Fact Tables Analyzed**: `CREDITO_DATA` (16.4K rows), `CONTADO_DATA` (11.5K rows), `COMPRAS_DATA`.
- **NULL Distribution**: 0% NULLs found in the crucial `TOTAL` column across the top transactional tables. Data completion on billing amounts is excellent.
- **Referential Integrity Audit**: Validated the application-level orphaned record risk. 
  - `CREDITO_DATA -> CLIENTES`: 10 orphaned Txns.
  - `CREDITO_DATA -> PRODUCTOS`: 1 orphaned Txn.
  - `CONTADO_DATA -> CLIENTES`: 2 orphaned Txns.
  - *Mitigation Plan*: Extremely low percentage, but must be dropped or mapped to `Unknown` during Gold Layer ETL to prevent grouping errors.

### 4.2 EDA - Transactional Volume & Velocity
- **Velocity Analysis (`CREDITO_DATA`)**: The ERP is heavily top-weighted by a few products.
  - **`MAIZ`** is the dominant product, accounting for 9,526 transactions and over $383M in sales volume.
  - Other top products (`PAPELCA 2`, `SALT 25`, `SALT 45`) follow, but with significantly less volume.
  
### 4.3 EDA - Dimensional Profiling
- **Customer Cardinality**: Only 56% of registered customers are active in credit sales (227 Active out of 404 Total Customers in `CATALOGO_CLIENTES_DATA`).
- **Categorical Dominance (`ESTADO`)**: Transactions are overwhelmingly `ACTIVA` (10,925) vs `CANCELADA` (602) in `CONTADO_DATA`. Roughly ~5.2% cancellation rate.

### 4.4 EDA - Outlier Detection (Statistical Fencing)
- **Results (`TOTAL` in `CREDITO_DATA`)**: 
  - Q1: $0.00, Q3: $44,824.60
  - Upper Fence (IQR * 1.5): $112,061.50
- **Outliers Detected**: 1,273 transactions exceed the upper fence. This indicates highly skewed transaction volumes (e.g. bulk vs retail). The Gold Pipeline must include a "Bulk/Outlier" dimension flag.

## 5. Consultancy Framework & Engineering Standards

### 5.1 Business Intelligence Pillars
- **A. Profitability & Margin**: Map Sales vs Costs to target "Stars" vs "Dogs". Calculate true contribution margin.
- **B. Operational Efficiency**: Track "Merma" (Criba effect). Analyze cost-per-ton in logistics auditing.
- **C. Commercial Strategy**: Focus on the 44% customer dormancy recovery strategy. Identify concentration risk.
- **D. Financial Health**: Calculate DSO (Days Sales Outstanding) matching Credito to Cobranza. Audit 5.2% cancellation rate.

### 5.2 Engineering Standards (Gold Layer Pipeline)
- **Syntax Rule**: Use `[Column Name]` for all identifiers to handle spaces.
- **Null Safety**: `COALESCE([COLUMN], 0)` for all numeric variables (TOTAL, BULTOS, PESO).
- **Orphan Guarding**: Map unbound `CODIGO` fact records via Left Join to `999` (UNKNOWN) to preserve transactional EBITDA volume.

## 6. Phase 2.1: Strategic Deep Dive Execution Log
- Verified massive `MAIZ` dominance ($383M volume heavily skewed).
- Outlier fence strictly set at `$112,061.50`.
- 5.2% transaction cancellation rate requires administrative audit (`ESTADO = 'CANCELADA'`).
- Script generation underway for OPEX mapping, top 5 product unit margin (Sales vs Purchases), and Gold Fact Sales schema standardizing `IS_BULK_OUTLIER` flag mapping.

## 7. Phase 2.2: Profitability Engine Execution Log
**Task A: Unit Margin Spread**
- `MAIZ` is an absolute "Star" commodity. WAC is $4.76, Avg Sale is $8.59, yielding a **44.63% Margin** on $405M of revenue. It easily clears the 8% risk threshold.
- Other tracking products maintain healthy positive margins (8.3% - 15.7%).
**Task B: OPEX Distribution & Leakage**
- **Dark Expense Audit**: `[CONCEPTO DIVERSO]` and Unmapped OPEX is only $130k (0.06% of Total OPEX). Accounting discipline is extremely strong; re-categorization is NOT urgently needed.
- **Efficiency Metric**: OPEX represents **40.06%** of Total Revenue evaluated ($215M OPEX / $537M Rev). This is high for agribusiness commodities. 
- *Strategic Recommendation for `[DESTINO]`*: We must pivot the Gold Layer to map OPEX purely grouped by `[DESTINO]` (Cost Center/Location) vs Revenue grouped by location. This location-based profitability view will isolate which specific branches are dragging the EBITDA down.
**Task C: Gold Financial Architecture**
- Schema successfully generated for `GOLD_FINANCIAL_PERFORMANCE`.

## 8. Phase 3: The KPI Selection Framework & Gold View
Filtered down the universe of possibilities to the "Vital Few" utilizing Actionability, Sensitivity, and Data Reliability scores:

1. **CM2 (Contribution Margin 2)**: Core Profitability. Includes COGS and Transport overrides. `[Strategic Recommendation: Pivot focus immediately if CM2 dips negative on MAIZ volume.]`
2. **Customer Churn/Dormancy**: Commercial Health. Tracking the 44% metric. `[Strategic Recommendation: If Dormancy > 40%, trigger automated reactivation discounts/calls.]`
3. **Criba Output / Yield (Merma %)**: Ops Efficiency. `[Strategic Recommendation: Correlate merma loss % directly to specific Proveedores to negotiate down buying prices.]`
4. **DSO (Days Sales Outstanding)**: Financial Liquidity. `[Strategic Recommendation: If DSO > 45 days, enforce a cash-only policy for frequent late-payers.]`
5. **Administrative Cancellation Rate**: Operations. Tracking the 5.2% anomaly. `[Strategic Recommendation: If Cancellation Loss > 5% of gross volume, audit individual users in LOGIN_ACCESS_DATA for abuse.]`

## 9. Phase 4: Data Storytelling & The "Missing Link"
- **Visual Hierarchy Mapped**: EBITDA Guard (Waterfall), Velocity Heatmap, Leakage Monitor (Gauges), Commercial Recovery (Treemap).
- **CRITICAL DATA GAP DISCOVERED**: The ERP captures `[DESTINO]` (Location/Cost Center) in OPEX (`GASTOS_DATA`) but **FAILS** to capture it in Revenue (`CREDITO_DATA` / `CONTADO_DATA`).
  - *Strategic Impact*: We cannot currently calculate true EBITDA per location out-of-the-box. The `GOLD_KPI_DASHBOARD_DATA` script will fail upon execution because `S.[DESTINO]` does not exist.
  - *Strategic Recommendation*: We must either: 1) Map `CLIENTE` to a specific region via a catalog update, 2) Apportion OPEX to total sales volume proportionally, or 3) Mandate an immediate software update to the ERP to capture `DESTINO` (Sucursal) at the point of sale.
