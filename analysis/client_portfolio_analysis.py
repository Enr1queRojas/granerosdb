"""
================================================================================
ANÁLISIS ESTRATÉGICO DE CARTERA DE CLIENTES
McKinsey & Company — Framework de Consultoría Financiera
================================================================================
Genera un reporte HTML interactivo con análisis exhaustivo de la cartera:
  - Concentración de ingresos (Pareto/ABC)
  - Segmentación estratégica (Matriz de valor)
  - Riesgo de dormancia y churn
  - Comportamiento de pago y cobranza
  - Ciclo de vida y adquisición
  - Recomendaciones estratégicas accionables

Ejecución: python analysis/client_portfolio_analysis.py
Salida:    reports/McKinsey_Client_Portfolio_Analysis.html
================================================================================
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_client_data():
    """Carga y prepara los datos de clientes desde el Excel."""
    print("[1/7] Cargando datos de clientes...")
    xlsx_path = PROJECT_ROOT / "data" / "Clientes.xlsx"
    if not xlsx_path.exists():
        print(f"ERROR: No se encontró {xlsx_path}")
        sys.exit(1)

    df = pd.read_excel(xlsx_path)
    df["NOMBRE"] = df["NOMBRE"].fillna("SIN NOMBRE")

    # Clasificación de actividad basada en recency
    conditions = [
        df["recency_days"].isna(),
        df["recency_days"] <= 90,
        df["recency_days"] <= 180,
        df["recency_days"] <= 365,
        df["recency_days"] > 365,
    ]
    labels = ["Sin Compras", "Activo", "En Riesgo", "Dormido", "Perdido"]
    df["segmento_actividad"] = np.select(conditions, labels, default="Sin Compras")

    # ABC classification
    df_sorted = df.sort_values("total_purchases", ascending=False).copy()
    total_rev = df_sorted["total_purchases"].sum()
    if total_rev > 0:
        df_sorted["cum_pct"] = df_sorted["total_purchases"].cumsum() / total_rev * 100
        df_sorted["abc"] = np.where(
            df_sorted["cum_pct"] <= 80, "A",
            np.where(df_sorted["cum_pct"] <= 95, "B", "C")
        )
    else:
        df_sorted["cum_pct"] = 0
        df_sorted["abc"] = "C"

    # Cuadrante estratégico (Revenue vs Frequency)
    med_rev = df_sorted.loc[df_sorted["total_purchases"] > 0, "total_purchases"].median()
    med_freq = df_sorted.loc[df_sorted["credit_count"] > 0, "credit_count"].median()
    if pd.isna(med_rev):
        med_rev = 0
    if pd.isna(med_freq):
        med_freq = 0

    def classify_quadrant(row):
        high_rev = row["total_purchases"] >= med_rev
        high_freq = row["credit_count"] >= med_freq
        if row["total_purchases"] == 0 and row["credit_count"] == 0:
            return "Inactivo"
        if high_rev and high_freq:
            return "⭐ Estrella"
        if high_rev and not high_freq:
            return "🐋 Ballena"
        if not high_rev and high_freq:
            return "📈 Oportunidad"
        return "⚠️ Bajo Valor"

    df_sorted["cuadrante"] = df_sorted.apply(classify_quadrant, axis=1)

    print(f"    → {len(df_sorted)} clientes cargados")
    return df_sorted, total_rev, med_rev, med_freq


# ─────────────────────────────────────────────────────────────────────────────
# 2. ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def compute_kpis(df, total_rev):
    """Calcula KPIs ejecutivos."""
    print("[2/7] Calculando KPIs ejecutivos...")
    total_clients = len(df)
    active_clients = len(df[df["segmento_actividad"] == "Activo"])
    dormant_pct = len(df[df["segmento_actividad"].isin(["Dormido", "Perdido"])]) / total_clients * 100
    at_risk = len(df[df["segmento_actividad"] == "En Riesgo"])
    avg_client_value = df.loc[df["total_purchases"] > 0, "total_purchases"].mean()
    collection_eff = (df["total_payments"].sum() / df["total_purchases"].sum() * 100) if df["total_purchases"].sum() > 0 else 0
    top10_share = df.nlargest(10, "total_purchases")["total_purchases"].sum() / total_rev * 100 if total_rev > 0 else 0

    # HHI Index
    if total_rev > 0:
        shares = df["total_purchases"] / total_rev * 100
        hhi = (shares ** 2).sum()
    else:
        hhi = 0

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "dormant_pct": dormant_pct,
        "at_risk": at_risk,
        "total_portfolio": total_rev,
        "avg_client_value": avg_client_value if not pd.isna(avg_client_value) else 0,
        "collection_eff": collection_eff,
        "top10_share": top10_share,
        "hhi": hhi,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "teal": "#00d4aa",
    "coral": "#ff6b6b",
    "cyan": "#45b7d1",
    "mint": "#4ecdc4",
    "gold": "#ffd93d",
    "purple": "#6c5ce7",
    "navy": "#0a1628",
    "card": "rgba(255,255,255,0.04)",
    "grid": "rgba(255,255,255,0.08)",
    "text": "#c8d6e5",
}

_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
)
_DEFAULT_AXIS = dict(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])

def layout(**overrides):
    """Merge base layout with per-chart overrides without duplicate-key errors."""
    base = dict(_BASE_LAYOUT)
    # Apply default axes only if not overridden
    if "xaxis" not in overrides:
        base["xaxis"] = dict(_DEFAULT_AXIS)
    if "yaxis" not in overrides:
        base["yaxis"] = dict(_DEFAULT_AXIS)
    if "margin" not in overrides:
        base["margin"] = dict(l=60, r=30, t=50, b=50)
    base.update(overrides)
    return base


def build_pareto_chart(df):
    """Curva de Pareto — concentración de ingresos."""
    print("[3/7] Generando gráficos de concentración...")
    df_active = df[df["total_purchases"] > 0].sort_values("total_purchases", ascending=False).reset_index(drop=True)
    n = len(df_active)
    df_active["client_pct"] = (np.arange(1, n + 1)) / n * 100
    total = df_active["total_purchases"].sum()
    df_active["cum_rev_pct"] = df_active["total_purchases"].cumsum() / total * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_active["client_pct"], y=df_active["total_purchases"],
        marker_color=COLORS["teal"], opacity=0.5, name="Ingreso por Cliente",
        hovertemplate="Cliente %{x:.0f}%<br>Ingreso: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df_active["client_pct"], y=df_active["cum_rev_pct"],
        mode="lines", line=dict(color=COLORS["coral"], width=3),
        name="% Acumulado", yaxis="y2",
        hovertemplate="%{x:.0f}% de clientes = %{y:.1f}% de ingresos<extra></extra>"
    ))
    # 80/20 reference lines
    fig.add_hline(y=80, line_dash="dash", line_color=COLORS["gold"], opacity=0.5,
                  annotation_text="80% de ingresos", yref="y2")
    fig.add_vline(x=20, line_dash="dash", line_color=COLORS["gold"], opacity=0.5,
                  annotation_text="20% de clientes")

    fig.update_layout(**layout(
        title="Curva de Pareto — Concentración de Ingresos",
        xaxis_title="% de Clientes (ordenados por ingreso)",
        yaxis_title="Ingreso por Cliente (MXN)",
        yaxis2=dict(title="% Acumulado", overlaying="y", side="right",
                    range=[0, 105], gridcolor=COLORS["grid"]),
        legend=dict(x=0.6, y=0.3, bgcolor="rgba(0,0,0,0.3)"),
        height=450,
    ))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_top15_chart(df):
    """Top 15 clientes por ingreso."""
    top = df.nlargest(15, "total_purchases").iloc[::-1]
    colors = [COLORS["teal"] if abc == "A" else COLORS["cyan"] for abc in top["abc"]]

    fig = go.Figure(go.Bar(
        y=top["NOMBRE"].str[:25], x=top["total_purchases"],
        orientation="h", marker_color=colors,
        text=top["total_purchases"].apply(lambda x: f"${x:,.0f}"),
        textposition="outside", textfont=dict(size=11),
        hovertemplate="%{y}<br>Ingreso: $%{x:,.0f}<br>Transacciones: %{customdata[0]}<extra></extra>",
        customdata=top[["credit_count"]].values,
    ))
    fig.update_layout(**layout(
        title="Top 15 Clientes por Ingreso Total",
        xaxis_title="Ingreso Total (MXN)",
        height=500,
        margin=dict(l=200, r=80, t=50, b=50),
    ))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_abc_pie(df):
    """Distribución ABC."""
    abc_counts = df.groupby("abc").agg(
        clientes=("CODIGO", "count"),
        ingreso=("total_purchases", "sum")
    ).reindex(["A", "B", "C"]).fillna(0)

    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]],
                        subplot_titles=("Por Número de Clientes", "Por Volumen de Ingreso"))

    fig.add_trace(go.Pie(
        labels=["A — Estratégicos", "B — Tácticos", "C — Cola Larga"],
        values=abc_counts["clientes"].values,
        marker=dict(colors=[COLORS["teal"], COLORS["cyan"], COLORS["grid"]]),
        hole=0.55, textinfo="label+percent", textfont=dict(size=11),
    ), row=1, col=1)

    fig.add_trace(go.Pie(
        labels=["A — Estratégicos", "B — Tácticos", "C — Cola Larga"],
        values=abc_counts["ingreso"].values,
        marker=dict(colors=[COLORS["teal"], COLORS["cyan"], COLORS["grid"]]),
        hole=0.55, textinfo="label+percent", textfont=dict(size=11),
    ), row=1, col=2)

    fig.update_layout(**layout(
        title="Clasificación ABC — Segmentación de Cartera",
        height=400,
        showlegend=False,
    ))
    return fig.to_html(full_html=False, include_plotlyjs=False), abc_counts


def build_quadrant_chart(df, med_rev, med_freq):
    """Matriz de segmentación estratégica."""
    print("[4/7] Generando matriz de segmentación...")
    df_active = df[df["total_purchases"] > 0].copy()
    color_map = {
        "⭐ Estrella": COLORS["gold"],
        "🐋 Ballena": COLORS["purple"],
        "📈 Oportunidad": COLORS["cyan"],
        "⚠️ Bajo Valor": COLORS["coral"],
        "Inactivo": COLORS["grid"],
    }

    fig = go.Figure()
    for seg, color in color_map.items():
        mask = df_active["cuadrante"] == seg
        subset = df_active[mask]
        if len(subset) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=subset["credit_count"], y=subset["total_purchases"],
            mode="markers", name=seg,
            marker=dict(
                size=np.clip(subset["total_purchases"] / subset["total_purchases"].max() * 40 + 6, 6, 50),
                color=color, opacity=0.7, line=dict(width=1, color="white")
            ),
            text=subset["NOMBRE"].str[:20],
            hovertemplate="%{text}<br>Ingreso: $%{y:,.0f}<br>Transacciones: %{x}<extra></extra>",
        ))

    # Quadrant lines
    fig.add_hline(y=med_rev, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig.add_vline(x=med_freq, line_dash="dash", line_color="rgba(255,255,255,0.3)")

    fig.update_layout(**layout(
        title="Matriz de Segmentación Estratégica (Ingreso vs Frecuencia)",
        xaxis_title="Número de Transacciones",
        yaxis_title="Ingreso Total (MXN)",
        xaxis=dict(type="log", gridcolor=COLORS["grid"]),
        yaxis=dict(type="log", gridcolor=COLORS["grid"]),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.5)"),
        height=500,
    ))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_dormancy_charts(df):
    """Análisis de dormancia y churn."""
    print("[5/7] Analizando dormancia y riesgo de churn...")
    seg_counts = df["segmento_actividad"].value_counts()
    seg_rev = df.groupby("segmento_actividad")["total_purchases"].sum()

    color_map = {
        "Activo": COLORS["teal"],
        "En Riesgo": COLORS["gold"],
        "Dormido": COLORS["coral"],
        "Perdido": "#8b0000",
        "Sin Compras": COLORS["grid"],
    }
    order = ["Activo", "En Riesgo", "Dormido", "Perdido", "Sin Compras"]

    # Stacked bar: count + revenue
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Distribución de Clientes", "Ingreso en Riesgo (MXN)"))

    for seg in order:
        cnt = seg_counts.get(seg, 0)
        rev = seg_rev.get(seg, 0)
        fig.add_trace(go.Bar(
            x=[seg], y=[cnt], name=seg, marker_color=color_map.get(seg, "gray"),
            text=[f"{cnt}"], textposition="outside",
            hovertemplate=f"{seg}<br>Clientes: {cnt}<extra></extra>",
            showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=[seg], y=[rev], name=seg, marker_color=color_map.get(seg, "gray"),
            text=[f"${rev:,.0f}"], textposition="outside", textfont=dict(size=10),
            hovertemplate=f"{seg}<br>Ingreso: ${rev:,.0f}<extra></extra>",
            showlegend=False,
        ), row=1, col=2)

    fig.update_layout(**layout(
        title="Análisis de Dormancia — Clientes e Ingreso en Riesgo",
        height=420, showlegend=True,
        legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)"),
        barmode="group",
    ))

    # Treemap de dormidos/perdidos con valor
    # Plotly Treemap requires every parent to also exist as a label (with parent="")
    dormant = df[df["segmento_actividad"].isin(["Dormido", "Perdido", "En Riesgo"])]
    dormant = dormant[dormant["total_purchases"] > 0].nlargest(30, "total_purchases").copy()
    dormant["_nombre_trunc"] = dormant["NOMBRE"].str[:22]

    # Build 3-level hierarchy: "" → segment → client
    seg_groups = dormant["segmento_actividad"].unique().tolist()

    tree_labels  = ["Cartera en Riesgo"]                          # root
    tree_parents = [""]                                            # root has no parent
    tree_values  = [0]                                             # root value (0 = auto-sum)
    tree_colors  = [COLORS["teal"]]

    for seg in seg_groups:
        seg_total = dormant.loc[dormant["segmento_actividad"] == seg, "total_purchases"].sum()
        tree_labels.append(seg)
        tree_parents.append("Cartera en Riesgo")
        tree_values.append(seg_total)
        tree_colors.append(color_map.get(seg, COLORS["coral"]))

    for _, row in dormant.iterrows():
        tree_labels.append(row["_nombre_trunc"])
        tree_parents.append(row["segmento_actividad"])
        tree_values.append(row["total_purchases"])
        tree_colors.append(color_map.get(row["segmento_actividad"], COLORS["coral"]))

    fig2 = go.Figure(go.Treemap(
        labels=tree_labels,
        parents=tree_parents,
        values=tree_values,
        texttemplate="%{label}<br><b>$%{value:,.0f}</b>",
        hovertemplate="%{label}<br>Ingreso: $%{value:,.0f}<extra></extra>",
        marker=dict(
            colors=tree_colors,
            line=dict(width=2, color=COLORS["navy"]),
        ),
        pathbar=dict(visible=True),
    ))
    fig2.update_layout(**layout(
        title="Mapa de Recuperación — Top 30 Clientes Dormidos/En Riesgo por Valor",
        height=520,
    ))

    return (fig.to_html(full_html=False, include_plotlyjs=False),
            fig2.to_html(full_html=False, include_plotlyjs=False),
            seg_counts, seg_rev)


def build_payment_charts(df):
    """Análisis de comportamiento de pago."""
    print("[6/7] Analizando comportamiento de cobro...")
    df_active = df[df["total_purchases"] > 0].copy()
    df_active["collection_ratio"] = np.where(
        df_active["total_purchases"] > 0,
        df_active["total_payments"] / df_active["total_purchases"],
        0
    )

    # Scatter: purchases vs payments colored by ratio
    fig = go.Figure(go.Scatter(
        x=df_active["total_purchases"],
        y=df_active["total_payments"],
        mode="markers",
        marker=dict(
            size=8, color=df_active["collection_ratio"],
            colorscale=[[0, COLORS["coral"]], [0.5, COLORS["gold"]], [1, COLORS["teal"]]],
            cmin=0, cmax=1.2,
            colorbar=dict(title="Ratio Cobro", tickformat=".0%"),
            opacity=0.7, line=dict(width=0.5, color="white"),
        ),
        text=df_active["NOMBRE"].str[:20],
        hovertemplate="%{text}<br>Compras: $%{x:,.0f}<br>Pagos: $%{y:,.0f}<br>Ratio: %{marker.color:.0%}<extra></extra>",
    ))
    # Perfect payment line
    max_val = max(df_active["total_purchases"].max(), df_active["total_payments"].max())
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val], mode="lines",
        line=dict(dash="dash", color="rgba(255,255,255,0.3)", width=1),
        name="Cobro Perfecto (1:1)", showlegend=True,
    ))

    fig.update_layout(**layout(
        title="Eficiencia de Cobranza — Compras vs Pagos por Cliente",
        xaxis_title="Total Compras (MXN)", yaxis_title="Total Pagos (MXN)",
        xaxis=dict(type="log", gridcolor=COLORS["grid"]),
        yaxis=dict(type="log", gridcolor=COLORS["grid"]),
        height=480,
    ))

    # Credit utilization histogram
    df_credit = df_active[df_active["LIMITE_DE_CREDITO"] > 0].copy()
    df_credit["util_pct"] = df_credit["TOTAL_CREDITO"] / df_credit["LIMITE_DE_CREDITO"] * 100

    fig2 = go.Figure(go.Histogram(
        x=df_credit["util_pct"].clip(0, 300),
        nbinsx=40, marker_color=COLORS["cyan"], opacity=0.7,
        hovertemplate="Utilización: %{x:.0f}%<br>Clientes: %{y}<extra></extra>",
    ))
    fig2.add_vline(x=100, line_dash="dash", line_color=COLORS["coral"],
                   annotation_text="Límite 100%", annotation_font_color=COLORS["coral"])

    fig2.update_layout(**layout(
        title="Distribución de Utilización de Crédito",
        xaxis_title="Utilización de Crédito (%)", yaxis_title="Número de Clientes",
        height=380,
    ))

    return (fig.to_html(full_html=False, include_plotlyjs=False),
            fig2.to_html(full_html=False, include_plotlyjs=False))


def build_lifecycle_charts(df):
    """Análisis de ciclo de vida."""
    print("[7/7] Analizando ciclo de vida de clientes...")
    df_tenure = df[df["tenure_months"].notna() & (df["tenure_months"] > 0)].copy()

    # Tenure vs monthly rate
    fig = go.Figure(go.Scatter(
        x=df_tenure["tenure_months"],
        y=df_tenure["monthly_purchase_rate"],
        mode="markers",
        marker=dict(
            size=np.clip(df_tenure["total_purchases"] / df_tenure["total_purchases"].max() * 30 + 5, 5, 40),
            color=df_tenure["total_purchases"],
            colorscale=[[0, COLORS["grid"]], [0.3, COLORS["cyan"]], [1, COLORS["teal"]]],
            colorbar=dict(title="Ingreso Total"),
            opacity=0.7,
        ),
        text=df_tenure["NOMBRE"].str[:20],
        hovertemplate="%{text}<br>Antigüedad: %{x:.0f} meses<br>Compra/mes: $%{y:,.0f}<br>Total: $%{marker.color:,.0f}<extra></extra>",
    ))
    fig.update_layout(**layout(
        title="Ciclo de Vida — Antigüedad vs Tasa de Compra Mensual",
        xaxis_title="Antigüedad (meses)",
        yaxis_title="Compra Mensual Promedio (MXN)",
        yaxis=dict(type="log", gridcolor=COLORS["grid"]),
        height=460,
    ))

    # Acquisition timeline
    df_acq = df[df["first_purchase_date"].notna()].copy()
    df_acq["month"] = df_acq["first_purchase_date"].dt.to_period("M").astype(str)
    acq_by_month = df_acq.groupby("month").size().reset_index(name="nuevos_clientes")

    fig2 = go.Figure(go.Bar(
        x=acq_by_month["month"], y=acq_by_month["nuevos_clientes"],
        marker_color=COLORS["mint"], opacity=0.8,
        hovertemplate="%{x}<br>Nuevos clientes: %{y}<extra></extra>",
    ))
    fig2.update_layout(**layout(
        title="Timeline de Adquisición de Clientes",
        xaxis_title="Mes", yaxis_title="Nuevos Clientes",
        height=350,
    ))

    return (fig.to_html(full_html=False, include_plotlyjs=False),
            fig2.to_html(full_html=False, include_plotlyjs=False))


# ─────────────────────────────────────────────────────────────────────────────
# 4. HTML REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def fmt_money(val):
    """Format MXN currency."""
    if val >= 1_000_000:
        return f"${val/1_000_000:,.1f}M"
    if val >= 1_000:
        return f"${val/1_000:,.0f}K"
    return f"${val:,.0f}"


def build_recommendations(kpis, df, seg_counts, seg_rev):
    """Genera recomendaciones estratégicas basadas en datos."""
    dormant_rev = seg_rev.get("Dormido", 0) + seg_rev.get("Perdido", 0)
    at_risk_rev = seg_rev.get("En Riesgo", 0)
    top10_clients = df.nlargest(10, "total_purchases")
    low_collection = df[(df["total_purchases"] > 0) & (df["payment_purchase_ratio"] < 0.5)]
    low_coll_value = low_collection["total_purchases"].sum()

    recs = [
        {
            "icon": "🎯",
            "title": "Programa de Reactivación de Clientes Dormidos",
            "finding": f"{seg_counts.get('Dormido', 0) + seg_counts.get('Perdido', 0)} clientes dormidos/perdidos representan {fmt_money(dormant_rev)} en ingreso histórico.",
            "impact": f"Recuperación estimada del 15-25% = {fmt_money(dormant_rev * 0.20)} en ingresos incrementales.",
            "horizon": "0-3 meses",
            "effort": "Medio",
        },
        {
            "icon": "⚡",
            "title": "Blindaje de Clientes Estrella (Retención Top 10)",
            "finding": f"Los 10 clientes principales concentran el {kpis['top10_share']:.0f}% del ingreso total ({fmt_money(top10_clients['total_purchases'].sum())}).",
            "impact": "Reducir riesgo de concentración. Perder 1 cliente top = pérdida de ~{:.0f}% del ingreso.".format(kpis['top10_share'] / 10),
            "horizon": "Inmediato (continuo)",
            "effort": "Bajo",
        },
        {
            "icon": "💰",
            "title": "Aceleración de Cobranza — Cartera Morosa",
            "finding": f"{len(low_collection)} clientes con ratio de cobro < 50% representan {fmt_money(low_coll_value)} en ventas con cobro deficiente.",
            "impact": f"Mejora de flujo de caja estimada: {fmt_money(low_coll_value * 0.30)}.",
            "horizon": "0-6 meses",
            "effort": "Medio-Alto",
        },
        {
            "icon": "📈",
            "title": "Programa de Upselling para Clientes B → A",
            "finding": f"{len(df[df['abc'] == 'B'])} clientes 'B' (tácticos) compran regularmente pero no alcanzan volumen A.",
            "impact": "Incremento del ticket promedio 20-30% en este segmento generaría ~{} adicionales.".format(
                fmt_money(df[df['abc'] == 'B']['total_purchases'].sum() * 0.25)
            ),
            "horizon": "3-6 meses",
            "effort": "Medio",
        },
        {
            "icon": "🛡️",
            "title": "Intervención Preventiva — Clientes En Riesgo",
            "finding": f"{seg_counts.get('En Riesgo', 0)} clientes en riesgo de churn con {fmt_money(at_risk_rev)} en ingreso histórico.",
            "impact": f"Evitar la fuga retendría {fmt_money(at_risk_rev * 0.60)} anuales.",
            "horizon": "Inmediato",
            "effort": "Bajo",
        },
        {
            "icon": "📊",
            "title": "Diversificación de Cartera — Reducir HHI",
            "finding": f"Índice HHI de {kpis['hhi']:.0f} puntos indica concentración {'alta' if kpis['hhi'] > 2500 else 'moderada' if kpis['hhi'] > 1500 else 'baja'}.",
            "impact": "Reducir dependencia de clientes individuales para estabilizar ingresos ante volatilidad.",
            "horizon": "6-12 meses",
            "effort": "Alto",
        },
    ]
    return recs


def generate_html_report(kpis, charts, recs, abc_counts, seg_counts, seg_rev):
    """Genera el reporte HTML completo."""
    now = datetime.now().strftime("%d de %B de %Y, %H:%M hrs")

    kpi_cards_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-value">{kpis['total_clients']}</div>
            <div class="kpi-label">Clientes Registrados</div>
        </div>
        <div class="kpi-card accent-green">
            <div class="kpi-value">{kpis['active_clients']}</div>
            <div class="kpi-label">Clientes Activos (&lt;90 días)</div>
        </div>
        <div class="kpi-card accent-red">
            <div class="kpi-value">{kpis['dormant_pct']:.1f}%</div>
            <div class="kpi-label">Tasa de Dormancia</div>
        </div>
        <div class="kpi-card accent-gold">
            <div class="kpi-value">{kpis['at_risk']}</div>
            <div class="kpi-label">Clientes En Riesgo</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{fmt_money(kpis['total_portfolio'])}</div>
            <div class="kpi-label">Valor Total del Portafolio</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{fmt_money(kpis['avg_client_value'])}</div>
            <div class="kpi-label">Valor Promedio por Cliente</div>
        </div>
        <div class="kpi-card accent-green">
            <div class="kpi-value">{kpis['collection_eff']:.1f}%</div>
            <div class="kpi-label">Eficiencia de Cobranza</div>
        </div>
        <div class="kpi-card accent-red">
            <div class="kpi-value">{kpis['top10_share']:.0f}%</div>
            <div class="kpi-label">Concentración Top 10</div>
        </div>
    </div>
    """

    recs_html = ""
    for r in recs:
        recs_html += f"""
        <div class="rec-card">
            <div class="rec-header">
                <span class="rec-icon">{r['icon']}</span>
                <h3>{r['title']}</h3>
            </div>
            <div class="rec-body">
                <div class="rec-row"><span class="rec-tag">Hallazgo</span> {r['finding']}</div>
                <div class="rec-row"><span class="rec-tag tag-green">Impacto</span> {r['impact']}</div>
                <div class="rec-meta">
                    <span>⏱️ {r['horizon']}</span>
                    <span>💪 Esfuerzo: {r['effort']}</span>
                </div>
            </div>
        </div>
        """

    abc_table = ""
    for seg in ["A", "B", "C"]:
        cnt = abc_counts.loc[seg, "clientes"] if seg in abc_counts.index else 0
        rev = abc_counts.loc[seg, "ingreso"] if seg in abc_counts.index else 0
        labels = {"A": "Estratégicos", "B": "Tácticos", "C": "Cola Larga"}
        abc_table += f"<tr><td><span class='abc-badge abc-{seg.lower()}'>{seg}</span> {labels[seg]}</td><td>{int(cnt)}</td><td>{fmt_money(rev)}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis Estratégico de Cartera de Clientes — Graneros Guerra</title>
    <meta name="description" content="Reporte de consultoría estratégica: análisis de cartera de clientes con segmentación ABC, análisis de dormancia, eficiencia de cobranza y recomendaciones accionables.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        :root {{
            --navy: #0a1628;
            --navy-light: #0f2035;
            --navy-card: #111d30;
            --teal: #00d4aa;
            --coral: #ff6b6b;
            --cyan: #45b7d1;
            --mint: #4ecdc4;
            --gold: #ffd93d;
            --purple: #6c5ce7;
            --text: #c8d6e5;
            --text-light: #8395a7;
            --text-white: #f5f6fa;
        }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--navy);
            color: var(--text);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        /* ── NAV ───────────────────────────────── */
        .top-nav {{
            position: sticky; top: 0; z-index: 100;
            background: rgba(10, 22, 40, 0.85);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 0.8rem 2rem;
            display: flex; align-items: center; gap: 2rem;
            overflow-x: auto;
        }}
        .top-nav a {{
            color: var(--text-light); text-decoration: none;
            font-size: 0.82rem; font-weight: 500;
            letter-spacing: 0.02em; white-space: nowrap;
            transition: color 0.2s;
        }}
        .top-nav a:hover {{ color: var(--teal); }}
        .nav-brand {{
            color: var(--text-white) !important;
            font-family: 'Playfair Display', serif;
            font-size: 1.05rem !important; font-weight: 700 !important;
        }}

        /* ── HEADER ────────────────────────────── */
        .hero {{
            text-align: center;
            padding: 4rem 2rem 2rem;
            background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 50%, rgba(0,212,170,0.05) 100%);
            border-bottom: 1px solid rgba(0,212,170,0.15);
        }}
        .hero h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 2.4rem; color: var(--text-white);
            margin-bottom: 0.5rem;
        }}
        .hero .subtitle {{
            color: var(--teal); font-size: 0.95rem;
            font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase;
        }}
        .hero .date {{ color: var(--text-light); font-size: 0.85rem; margin-top: 0.5rem; }}

        /* ── CONTAINER ─────────────────────────── */
        .container {{ max-width: 1280px; margin: 0 auto; padding: 2rem 1.5rem; }}

        /* ── SECTIONS ──────────────────────────── */
        .section {{
            margin-bottom: 3rem;
            animation: fadeIn 0.6s ease-out;
        }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .section-header {{
            display: flex; align-items: center; gap: 1rem;
            margin-bottom: 1.5rem; padding-bottom: 0.8rem;
            border-bottom: 2px solid rgba(0,212,170,0.2);
        }}
        .section-number {{
            background: linear-gradient(135deg, var(--teal), var(--cyan));
            color: var(--navy); font-weight: 700; font-size: 0.85rem;
            width: 32px; height: 32px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0;
        }}
        .section-header h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem; color: var(--text-white);
        }}

        /* ── CARDS ─────────────────────────────── */
        .card {{
            background: var(--navy-card);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px; padding: 1.5rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
        }}

        /* ── KPI GRID ──────────────────────────── */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem; margin-bottom: 2rem;
        }}
        .kpi-card {{
            background: var(--navy-card);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 14px; padding: 1.5rem 1.2rem;
            text-align: center;
            border-top: 3px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, border-color 0.3s;
        }}
        .kpi-card:hover {{ transform: translateY(-3px); }}
        .kpi-card.accent-green {{ border-top-color: var(--teal); }}
        .kpi-card.accent-red {{ border-top-color: var(--coral); }}
        .kpi-card.accent-gold {{ border-top-color: var(--gold); }}
        .kpi-value {{
            font-size: 2rem; font-weight: 700;
            color: var(--text-white);
            line-height: 1.1; margin-bottom: 0.3rem;
        }}
        .kpi-label {{
            font-size: 0.78rem; color: var(--text-light);
            text-transform: uppercase; letter-spacing: 0.05em;
        }}

        /* ── ABC TABLE ─────────────────────────── */
        .data-table {{
            width: 100%; border-collapse: collapse; margin: 1rem 0;
        }}
        .data-table th, .data-table td {{
            padding: 0.8rem 1rem; text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .data-table th {{
            color: var(--text-light); font-size: 0.75rem;
            text-transform: uppercase; letter-spacing: 0.08em;
        }}
        .abc-badge {{
            display: inline-block; width: 24px; height: 24px;
            border-radius: 6px; text-align: center; line-height: 24px;
            font-weight: 700; font-size: 0.8rem; margin-right: 0.5rem;
        }}
        .abc-a {{ background: var(--teal); color: var(--navy); }}
        .abc-b {{ background: var(--cyan); color: var(--navy); }}
        .abc-c {{ background: rgba(255,255,255,0.15); color: var(--text); }}

        /* ── RECOMMENDATIONS ───────────────────── */
        .rec-card {{
            background: var(--navy-card);
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 4px solid var(--teal);
            border-radius: 0 14px 14px 0;
            padding: 1.5rem; margin-bottom: 1rem;
            transition: border-color 0.3s, transform 0.2s;
        }}
        .rec-card:hover {{ border-left-color: var(--gold); transform: translateX(4px); }}
        .rec-card:nth-child(3) {{ border-left-color: var(--coral); }}
        .rec-card:nth-child(3):hover {{ border-left-color: var(--gold); }}
        .rec-header {{
            display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.8rem;
        }}
        .rec-icon {{ font-size: 1.5rem; }}
        .rec-header h3 {{ font-size: 1.05rem; color: var(--text-white); font-weight: 600; }}
        .rec-body {{ padding-left: 2.3rem; }}
        .rec-row {{ margin-bottom: 0.5rem; font-size: 0.9rem; }}
        .rec-tag {{
            display: inline-block; padding: 0.15rem 0.5rem;
            border-radius: 4px; font-size: 0.72rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.05em;
            background: rgba(69, 183, 209, 0.15); color: var(--cyan);
            margin-right: 0.5rem;
        }}
        .rec-tag.tag-green {{ background: rgba(0,212,170,0.15); color: var(--teal); }}
        .rec-meta {{
            display: flex; gap: 2rem; margin-top: 0.8rem;
            font-size: 0.82rem; color: var(--text-light);
        }}

        /* ── CHART WRAPPER ─────────────────────── */
        .chart-wrapper {{
            background: var(--navy-card);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px; padding: 1rem;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}

        /* ── INSIGHT CALLOUT ───────────────────── */
        .insight {{
            background: rgba(0,212,170,0.06);
            border-left: 3px solid var(--teal);
            padding: 1rem 1.2rem; border-radius: 0 10px 10px 0;
            margin: 1rem 0; font-size: 0.9rem;
        }}
        .insight strong {{ color: var(--teal); }}
        .insight.warning {{
            background: rgba(255,107,107,0.06);
            border-left-color: var(--coral);
        }}
        .insight.warning strong {{ color: var(--coral); }}

        /* ── FOOTER ────────────────────────────── */
        .footer {{
            text-align: center; padding: 2rem;
            border-top: 1px solid rgba(255,255,255,0.06);
            color: var(--text-light); font-size: 0.8rem;
        }}

        /* ── RESPONSIVE ────────────────────────── */
        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 1.6rem; }}
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .container {{ padding: 1rem; }}
            .rec-body {{ padding-left: 0; }}
        }}
    </style>
</head>
<body>

<nav class="top-nav">
    <a href="#" class="nav-brand">Graneros Guerra</a>
    <a href="#resumen">Resumen</a>
    <a href="#concentracion">Concentración</a>
    <a href="#segmentacion">Segmentación</a>
    <a href="#dormancia">Dormancia</a>
    <a href="#cobranza">Cobranza</a>
    <a href="#ciclo">Ciclo de Vida</a>
    <a href="#recomendaciones">Plan de Acción</a>
</nav>

<header class="hero">
    <div class="subtitle">Consultoría Estratégica — Análisis de Cartera</div>
    <h1>Diagnóstico Financiero de Clientes</h1>
    <div class="date">Generado el {now}</div>
</header>

<main class="container">

    <!-- SECTION 1: Executive Summary -->
    <section class="section" id="resumen">
        <div class="section-header">
            <div class="section-number">1</div>
            <h2>Resumen Ejecutivo</h2>
        </div>
        {kpi_cards_html}
        <div class="insight warning">
            <strong>Alerta de concentración:</strong> El {kpis['top10_share']:.0f}% del ingreso proviene de solo 10 clientes.
            El índice HHI es {kpis['hhi']:.0f} — {'riesgo alto de concentración' if kpis['hhi'] > 2500 else 'concentración moderada' if kpis['hhi'] > 1500 else 'concentración aceptable'}.
        </div>
    </section>

    <!-- SECTION 2: Revenue Concentration -->
    <section class="section" id="concentracion">
        <div class="section-header">
            <div class="section-number">2</div>
            <h2>Concentración de Ingresos</h2>
        </div>
        <div class="chart-wrapper">{charts['pareto']}</div>
        <div class="card">
            <h3 style="color:var(--text-white);margin-bottom:1rem;">Clasificación ABC</h3>
            <table class="data-table">
                <thead><tr><th>Segmento</th><th>Clientes</th><th>Ingreso</th></tr></thead>
                <tbody>{abc_table}</tbody>
            </table>
        </div>
        <div class="chart-wrapper">{charts['abc_pie']}</div>
        <div class="chart-wrapper">{charts['top15']}</div>
        <div class="insight">
            <strong>Hallazgo clave:</strong> La distribución Pareto confirma una alta dependencia en un pequeño grupo de clientes.
            Los clientes tipo A deben recibir atención preferencial y planes de retención personalizados.
        </div>
    </section>

    <!-- SECTION 3: Strategic Segmentation -->
    <section class="section" id="segmentacion">
        <div class="section-header">
            <div class="section-number">3</div>
            <h2>Matriz de Segmentación Estratégica</h2>
        </div>
        <div class="chart-wrapper">{charts['quadrant']}</div>
        <div class="insight">
            <strong>Lectura estratégica:</strong>
            Los clientes ⭐ <em>Estrella</em> (alto ingreso + alta frecuencia) son el activo más valioso — proteger a toda costa.
            Los 🐋 <em>Ballena</em> (alto ingreso + baja frecuencia) son oportunidades de regularización.
            Los 📈 <em>Oportunidad</em> (baja facturación + alta frecuencia) tienen potencial de upselling inmediato.
        </div>
    </section>

    <!-- SECTION 4: Dormancy -->
    <section class="section" id="dormancia">
        <div class="section-header">
            <div class="section-number">4</div>
            <h2>Análisis de Dormancia y Riesgo de Churn</h2>
        </div>
        <div class="chart-wrapper">{charts['dormancy_bars']}</div>
        <div class="chart-wrapper">{charts['dormancy_treemap']}</div>
        <div class="insight warning">
            <strong>Ingreso en riesgo:</strong> Los clientes En Riesgo + Dormidos + Perdidos acumulan
            {fmt_money(seg_rev.get('En Riesgo', 0) + seg_rev.get('Dormido', 0) + seg_rev.get('Perdido', 0))}
            en ingreso histórico. Un programa de reactivación agresivo podría recuperar entre 15-25% de este valor.
        </div>
    </section>

    <!-- SECTION 5: Collections -->
    <section class="section" id="cobranza">
        <div class="section-header">
            <div class="section-number">5</div>
            <h2>Comportamiento de Pago y Eficiencia de Cobranza</h2>
        </div>
        <div class="chart-wrapper">{charts['payment_scatter']}</div>
        <div class="chart-wrapper">{charts['credit_util']}</div>
        <div class="insight">
            <strong>Eficiencia de cobranza global:</strong> {kpis['collection_eff']:.1f}%.
            Los clientes por debajo de la línea diagonal 1:1 representan cartera morosa que requiere intervención inmediata del equipo de cobranza.
        </div>
    </section>

    <!-- SECTION 6: Lifecycle -->
    <section class="section" id="ciclo">
        <div class="section-header">
            <div class="section-number">6</div>
            <h2>Ciclo de Vida y Adquisición de Clientes</h2>
        </div>
        <div class="chart-wrapper">{charts['lifecycle']}</div>
        <div class="chart-wrapper">{charts['acquisition']}</div>
    </section>

    <!-- SECTION 7: Recommendations -->
    <section class="section" id="recomendaciones">
        <div class="section-header">
            <div class="section-number">7</div>
            <h2>Plan de Acción Estratégico</h2>
        </div>
        <p style="margin-bottom:1.5rem;color:var(--text-light);">
            Las siguientes iniciativas están ordenadas por impacto estimado y facilidad de implementación.
            Cada recomendación está respaldada por hallazgos cuantitativos del análisis.
        </p>
        {recs_html}
    </section>

</main>

<footer class="footer">
    <p>Análisis Estratégico de Cartera — Graneros Guerra &copy; {datetime.now().year}</p>
    <p>Generado automáticamente por el Motor de Inteligencia Financiera</p>
</footer>

</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# 5. MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  ANÁLISIS ESTRATÉGICO DE CARTERA DE CLIENTES")
    print("  Framework de Consultoría Financiera")
    print("=" * 70)

    # Load data
    df, total_rev, med_rev, med_freq = load_client_data()

    # Compute KPIs
    kpis = compute_kpis(df, total_rev)

    # Build all charts
    pareto_html = build_pareto_chart(df)
    top15_html = build_top15_chart(df)
    abc_pie_html, abc_counts = build_abc_pie(df)
    quadrant_html = build_quadrant_chart(df, med_rev, med_freq)
    dormancy_bars_html, dormancy_tree_html, seg_counts, seg_rev = build_dormancy_charts(df)
    payment_html, credit_html = build_payment_charts(df)
    lifecycle_html, acquisition_html = build_lifecycle_charts(df)

    charts = {
        "pareto": pareto_html,
        "top15": top15_html,
        "abc_pie": abc_pie_html,
        "quadrant": quadrant_html,
        "dormancy_bars": dormancy_bars_html,
        "dormancy_treemap": dormancy_tree_html,
        "payment_scatter": payment_html,
        "credit_util": credit_html,
        "lifecycle": lifecycle_html,
        "acquisition": acquisition_html,
    }

    # Build recommendations
    recs = build_recommendations(kpis, df, seg_counts, seg_rev)

    # Generate HTML
    print("\nGenerando reporte HTML...")
    html = generate_html_report(kpis, charts, recs, abc_counts, seg_counts, seg_rev)

    # Write output
    output_dir = PROJECT_ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "McKinsey_Client_Portfolio_Analysis.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"  ✅ Reporte generado exitosamente:")
    print(f"  📄 {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
