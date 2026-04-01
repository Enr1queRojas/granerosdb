-- ============================================================================
-- THE VITAL FEW: TOP 5 NORTH STAR KPIs (GOLD VISUALIZATION LAYER)
-- Senior Business Intelligence Strategy Consultant
-- 
-- LENS: EBITDA Growth, Leakage Detection, Working Capital Efficiency
-- DATA STANDARDS: Uses [ ], handles NULLs via COALESCE
-- ============================================================================
-- KPI 1: CM2 (Contribution Margin 2) -> Measures ultimate profitability after direct costs.
-- KPI 2: Customer Churn / Dormancy -> Measures commercial health and recurring revenue.
-- KPI 3: Criba Yield (Merma %) -> Measures operational efficiency. 1% savings = pure profit.
-- KPI 4: DSO (Days Sales Outstanding) -> Measures working capital liquidity.
-- KPI 5: Cancellation Rate -> Measures administrative leakages.
-- ============================================================================

CREATE OR ALTER VIEW [proadel].[VW_GOLD_NORTH_STAR_KPI] AS
WITH 

-- ============================================================================
-- 1. Profitability & Unit Economics (CM2 Approximation)
-- Strategic Recommendation: If average CM2 falls below 15% overall, initiate across-the-board cost-cutting.
-- ============================================================================
Gross_Margins AS (
    SELECT 
        c.[ID],
        c.[CODIGO],
        COALESCE(c.[TOTAL], 0) AS [Revenue],
        (COALESCE(c.[TOTAL], 0) - COALESCE(cmp.[IMPORTE], 0)) AS [Gross_Margin]
    FROM [proadel].[CREDITO_DATA] c
    LEFT JOIN [proadel].[COMPRAS_DATA] cmp ON c.[CODIGO] = cmp.[CODIGO]
    WHERE c.[ESTADO] = 'ACTIVA'
),

-- ============================================================================
-- 2. Commercial Strategy (Customer Dormancy Risk > 180 Days)
-- Strategic Recommendation: If Dormancy Rate > 40%, mandate the sales team to execute a win-back campaign.
-- ============================================================================
Dormancy AS (
    SELECT 
        COUNT(DISTINCT cat.[CODIGO]) AS [Total_Customers],
        COUNT(DISTINCT CASE WHEN DATEDIFF(day, CONVERT(date, c.[FECHA], 103), GETDATE()) > 180 THEN cat.[CODIGO] END) AS [Dormant_Customers]
    FROM [proadel].[CATALOGO_CLIENTES_DATA] cat
    LEFT JOIN [proadel].[CREDITO_DATA] c ON cat.[CODIGO] = c.[CLIENTE]
),

-- ============================================================================
-- 3 & 4: Operations & Financial Metrics (Cancellation Loss Rate)
-- Strategic Recommendation: If Cancellation Loss > 5%, enforce secondary authentication for deleting invoices.
-- ============================================================================
Cancellations AS (
    SELECT 
        SUM(CASE WHEN [ESTADO] = 'CANCELADA' THEN COALESCE([TOTAL], 0) ELSE 0 END) AS [Cancelled_Sales_Value],
        SUM(COALESCE([TOTAL], 0)) AS [Gross_Sales_Volume]
    FROM [proadel].[CREDITO_DATA]
)

-- ============================================================================
-- FINAL KPI AGGREGATION
-- ============================================================================
SELECT 
    (SELECT SUM([Gross_Margin]) FROM Gross_Margins) AS [Aggregate_Gross_Margin],
    
    (SELECT [Dormant_Customers] * 100.0 / NULLIF([Total_Customers], 0) FROM Dormancy) AS [Dormancy_Rate_Pct],

    (SELECT ([Cancelled_Sales_Value] * 100.0) / NULLIF([Gross_Sales_Volume], 0) FROM Cancellations) AS [Cancellation_Loss_Rate_Pct]
    
    -- Extensibility: Add DSO via COBRANZA_DATA integration and Yield via CRIBA_DATA in subsequent Gold updates.
;
