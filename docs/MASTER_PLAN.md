# MASTER_PLAN

## Objective
Lead the end-to-end exploration, modeling, and visualization of a small ERP database.

## Phases & Checklists

### Phase 1: Discovery & Inventory (The "Unbiased" Audit)
- [x] Receive database schema or DDL from the user. (Engine info received)
- [x] Analyze schema, tables, and views without pre-existing bias.
- [x] Inventory facts vs. dimensions.
- [x] Map PK/FK relationships. (Note: No explicit DB-level FKs exist)
- [x] Identify "Dark Data".
- [x] Log initial findings in INSIGHTS_BLACKBOARD.md.

### Phase 2: Professional EDA & Master Plan
- [x] 1. Data Quality & Integrity Audit: Null Distribution & Referential Integrity.
- [x] 2. Transactional Volume & Seasonality: Time-Series Decomposition & Velocity Analysis.
- [x] 3. Dimensional Profiling: Cardinality Check & Categorical Dominance.
- [x] 4. Outlier Detection: Statistical Fencing (IQR).

### Phase 2.1 & 2.2: Strategic Deep Dive & Profitability Engine
- [x] Evaluate COMPRAS_DATA and GASTOS_DATA for OPEX and Unit Margin analysis.
- [x] Apply 4 Lenses: Profitability, Ops Efficiency, Commercial Strategy, Financial Health.
- [x] Generate Strategic SQL modularly (Task A: Margin, Task B: OPEX, Task C: Gold Schema).

### Phase 3: The KPI Selection & Visualization Layer
- [x] Multidimensional Metric Inventory (Commercial, Profitability, Operations, Financial).
- [x] KPI Selection Framework Filter (Actionability, Sensitivity, Data Reliability).
- [x] Build Top 5 North Star SQL Boilerplate (`gold_kpi_layer.sql`).

### Phase 4: Data Storytelling & Visualization Strategy
- [x] Build "EBITDA Guard" Waterfall (Gross -> Net via OPEX/COGS).
- [x] Build "Maiz Velocity" Heatmap (Volume vs Margin %).
- [x] Build "Leakage Monitor" Gauges (Criba Yield, Cancellation Rate).
- [x] Build "Commercial Recovery" Treemap (Dormancy Hit List).
- [x] Resolve Data Linkage Gap (`DESTINO` mapping for Location-based EBITDA).

## Current Status
- **Phases 1, 2, 2.1, 2.2, 3**: 🟢 Completed. EDA, OPEX, Margin Baselines, and North Star KPIs processed.
- **Phase 4: Viz Strategy**: 🟢 Completed. Strategic Dashboard Design Framework logged in Spanish consulting report.
