"""
E-COMMERCE ANALYTICS DASHBOARD
Built with Streamlit

HOW TO RUN:
streamlit run overall.py

PREREQUISITES:
pip install streamlit pandas plotly numpy
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="E-Commerce Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 36px;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 20px 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .kpi-label {
        font-size: 14px;
        color: #666;
        font-weight: 500;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
    .positive-change {
        color: #00cc00;
        font-weight: bold;
    }
    .negative-change {
        color: #ff3333;
        font-weight: bold;
    }
    .insight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# DATA LOADING FUNCTIONS
# ==============================================================================

@st.cache_data
def load_data():
    """
    Loads all aggregated CSV files with error handling and column normalization.
    Renames columns to match dashboard expectations.
    """
    data = {}
    try:
        # 1. DAILY BUSINESS METRICS
        data['daily_metrics'] = pd.read_csv('aggregated_data/daily_business_metrics.csv')
        data['daily_metrics']['date'] = pd.to_datetime(data['daily_metrics']['date'])
        data['daily_metrics'] = data['daily_metrics'].rename(columns={'net_revenue': 'total_revenue'})

        # 2. SESSION ATTRIBUTION
        data['session_attribution'] = pd.read_csv('aggregated_data/session_attribution.csv')
        data['session_attribution']['date'] = pd.to_datetime(data['session_attribution']['date'])
        data['session_attribution'] = data['session_attribution'].rename(columns={'net_revenue': 'revenue'})

        # 3. SESSION FUNNEL
        data['session_funnel'] = pd.read_csv('aggregated_data/session_funnel.csv')
        data['session_funnel']['date'] = pd.to_datetime(data['session_funnel']['date'])
        data['session_funnel'] = data['session_funnel'].rename(columns={
            'had_cart_view': 'had_add_to_cart',
            'had_thank_you': 'had_order'
        })

        # 4. PRODUCT PERFORMANCE
        data['product_performance'] = pd.read_csv('aggregated_data/product_performance_daily.csv')
        data['product_performance']['date'] = pd.to_datetime(data['product_performance']['date'])

        # 5. USER LIFETIME METRICS
        data['user_lifetime'] = pd.read_csv('aggregated_data/user_lifetime_metrics.csv')
        data['user_lifetime']['first_order_date'] = pd.to_datetime(data['user_lifetime']['first_order_date'])
        data['user_lifetime']['last_order_date'] = pd.to_datetime(data['user_lifetime']['last_order_date'])

        # 6. PAGE ENGAGEMENT
        data['page_engagement'] = pd.read_csv('aggregated_data/page_engagement_metrics.csv')
        data['page_engagement']['date'] = pd.to_datetime(data['page_engagement']['date'])

        # 7. COUPON PERFORMANCE
        data['coupon_performance'] = pd.read_csv('aggregated_data/coupon_performance.csv')
        data['coupon_performance']['date'] = pd.to_datetime(data['coupon_performance']['date'])

        return data

    except FileNotFoundError as e:
        st.error(f"❌ Data file not found: {e}")
        st.info("Please ensure aggregated data files are in 'aggregated_data/' folder")
        return None
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def format_number(num, decimals=0, prefix='', suffix=''):
    if pd.isna(num):
        return "N/A"
    if abs(num) >= 1_000_000_000:
        formatted = f"{num/1_000_000_000:.{decimals}f}B"
    elif abs(num) >= 1_000_000:
        formatted = f"{num/1_000_000:.{decimals}f}M"
    elif abs(num) >= 1_000:
        formatted = f"{num/1_000:.{decimals}f}K"
    else:
        formatted = f"{num:.{decimals}f}"
    return f"{prefix}{formatted}{suffix}"

def calculate_change(current, previous):
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def trend_label(monthly_series):
    """Return ⬆ increasing / ➖ flat / ⬇ decreasing based on first vs last half average"""
    if len(monthly_series) < 2:
        return "➖ flat"
    mid = len(monthly_series) // 2
    first_half = monthly_series.iloc[:mid].mean()
    second_half = monthly_series.iloc[mid:].mean()
    pct = calculate_change(second_half, first_half)
    if pct > 5:
        return "⬆ increasing"
    elif pct < -5:
        return "⬇ decreasing"
    else:
        return "➖ flat"

def get_month_name(month_num):
    import calendar
    return calendar.month_abbr[month_num]

def add_month_col(df):
    """Add year and month columns to a date-indexed dataframe"""
    df = df.copy()
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.strftime('%b')
    df['year_month'] = df['date'].dt.to_period('M').astype(str)
    return df

def create_metric_card(label, value, change=None, prefix='', suffix=''):
    formatted_value = format_number(value, decimals=2, prefix=prefix, suffix=suffix)
    if change is not None:
        change_class = 'positive-change' if change > 0 else 'negative-change'
        change_symbol = '▲' if change > 0 else '▼'
        return f"""
        <div class="metric-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{formatted_value}</div>
            <div class="{change_class}">{change_symbol} {abs(change):.1f}% vs prev period</div>
        </div>
        """
    else:
        return f"""
        <div class="metric-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{formatted_value}</div>
        </div>
        """

# ==============================================================================
# SIDEBAR FILTERS
# ==============================================================================

def render_sidebar(data):
    """Render sidebar with Yearly / Monthly global filters"""
    st.sidebar.title("🎛️ Filters")
    st.sidebar.subheader("📅 Time Filter")

    min_date = data['daily_metrics']['date'].min().date()
    max_date = data['daily_metrics']['date'].max().date()

    # Primary filter: Yearly or Monthly
    view_mode = st.sidebar.radio(
        "View Mode",
        ["📅 Yearly (2025)", "🗓️ Monthly"],
        index=0
    )

    if view_mode == "📅 Yearly (2025)":
        start_date = pd.Timestamp("2025-01-01")
        end_date   = pd.Timestamp("2025-12-31")
        selected_month = None
    else:
        month_options = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        selected_month_name = st.sidebar.selectbox(
            "Select Month (2025)",
            list(month_options.keys()),
            index=0
        )
        selected_month = month_options[selected_month_name]
        import calendar
        last_day = calendar.monthrange(2025, selected_month)[1]
        start_date = pd.Timestamp(f"2025-{selected_month:02d}-01")
        end_date   = pd.Timestamp(f"2025-{selected_month:02d}-{last_day:02d}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Additional Filters")

    products = sorted(data['product_performance']['product_name'].unique())
    selected_products = st.sidebar.multiselect(
        "Filter by Products",
        options=products,
        default=None,
        help="Leave empty to show all products"
    )

    if 'utm_source' in data['session_attribution'].columns:
        sources = sorted(data['session_attribution']['utm_source'].dropna().unique())
        selected_sources = st.sidebar.multiselect(
            "Filter by Traffic Source",
            options=sources,
            default=None,
            help="Leave empty to show all sources"
        )
    else:
        selected_sources = None

    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Data range: {min_date} to {max_date}")

    return {
        'start_date': start_date,
        'end_date': end_date,
        'view_mode': view_mode,
        'selected_month': selected_month,
        'products': selected_products if selected_products else None,
        'sources': selected_sources if selected_sources else None
    }

# ==============================================================================
# PAGE 1: EXECUTIVE SUMMARY
# ==============================================================================

def page_executive_summary(data, filters):
    """Executive Summary — Yearly KPIs + Monthly breakdowns"""

    st.markdown('<div class="main-header">📊 Executive Summary</div>', unsafe_allow_html=True)
    st.markdown("### High-level business metrics at a glance")

    # Full year data for yearly KPIs
    df_year = data['daily_metrics'][
        (data['daily_metrics']['date'] >= pd.Timestamp("2025-01-01")) &
        (data['daily_metrics']['date'] <= pd.Timestamp("2025-12-31"))
    ].copy()

    # Filtered data (respects monthly filter)
    df = data['daily_metrics'][
        (data['daily_metrics']['date'] >= filters['start_date']) &
        (data['daily_metrics']['date'] <= filters['end_date'])
    ].copy()

    if df_year.empty:
        st.warning("No data available for 2025")
        return

    df_year = add_month_col(df_year)

    # ── YEARLY TOP KPIs ────────────────────────────────────────────────────────
    yearly_revenue    = df_year['total_revenue'].sum()
    yearly_orders     = df_year['total_orders'].sum()
    yearly_sessions   = df_year['total_sessions'].sum()
    yearly_aov        = yearly_revenue / yearly_orders if yearly_orders > 0 else 0
    yearly_conv       = (yearly_orders / yearly_sessions * 100) if yearly_sessions > 0 else 0

    st.markdown("---")
    st.markdown("### 📌 2025 Yearly KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Revenue (2025)", f"${yearly_revenue:,.0f}")
    with col2:
        st.metric("🛍️ Orders (2025)", f"{yearly_orders:,}")
    with col3:
        st.metric("📈 Conversion Rate", f"{yearly_conv:.2f}%")
    with col4:
        st.metric("💵 Avg Order Value", f"${yearly_aov:.2f}")

    # ── MONTHLY AGGREGATION ────────────────────────────────────────────────────
    monthly = df_year.groupby(['year', 'month', 'month_name']).agg(
        revenue=('total_revenue', 'sum'),
        orders=('total_orders', 'sum'),
        sessions=('total_sessions', 'sum'),
        new_customers=('new_customers', 'sum') if 'new_customers' in df_year.columns else ('total_orders', 'count'),
        repeat_customers=('repeat_customers', 'sum') if 'repeat_customers' in df_year.columns else ('total_orders', 'count'),
    ).reset_index().sort_values('month')

    monthly['aov']         = (monthly['revenue'] / monthly['orders']).fillna(0)
    monthly['conv_rate']   = (monthly['orders']  / monthly['sessions'] * 100).fillna(0)
    monthly['month_label'] = monthly['month'].apply(lambda x: get_month_name(x))

    yearly_avg_revenue = monthly['revenue'].mean()

    # ── 1. REVENUE INSIGHTS ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("1️⃣ Revenue Insights")

    peak_month   = monthly.loc[monthly['revenue'].idxmax()]
    lowest_month = monthly.loc[monthly['revenue'].idxmin()]
    jan_rev      = monthly[monthly['month'] == 1]['revenue'].values[0] if 1 in monthly['month'].values else 0
    dec_rev      = monthly[monthly['month'] == 12]['revenue'].values[0] if 12 in monthly['month'].values else 0
    jan_to_dec_growth = calculate_change(dec_rev, jan_rev)
    above_avg_months  = monthly[monthly['revenue'] > yearly_avg_revenue]['month_label'].tolist()
    rev_trend         = trend_label(monthly['revenue'])

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            monthly, x='month_label', y='revenue',
            title='Monthly Revenue (2025)',
            labels={'revenue': 'Revenue ($)', 'month_label': 'Month'},
            color='revenue', color_continuous_scale='Blues',
            text=monthly['revenue'].apply(lambda x: f"${x/1000:.0f}K")
        )
        fig.add_hline(y=yearly_avg_revenue, line_dash="dash", line_color="red",
                      annotation_text=f"Yearly Avg ${yearly_avg_revenue/1000:.0f}K",
                      annotation_position="top right")
        fig.update_traces(textposition='outside')
        fig.update_layout(height=400, showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📊 Revenue Breakdown**")
        st.metric("🏆 Peak Month", peak_month['month_label'], f"${peak_month['revenue']:,.0f}")
        st.metric("📉 Lowest Month", lowest_month['month_label'], f"${lowest_month['revenue']:,.0f}")
        st.metric("📈 Jan → Dec Growth", f"{jan_to_dec_growth:+.1f}%")
        st.markdown(f"**Trend:** {rev_trend}")
        st.markdown(f"**Above-avg months:** {', '.join(above_avg_months) if above_avg_months else 'None'}")

        # Narrative insight
        q1_rev = monthly[monthly['month'].isin([1,2,3])]['revenue'].sum()
        q4_rev = monthly[monthly['month'].isin([10,11,12])]['revenue'].sum()
        q4_vs_q1 = calculate_change(q4_rev, q1_rev)
        st.info(f"""
        **💡 Insight**
        Revenue is **{rev_trend.split()[1]}**, with Q4 {'outperforming' if q4_vs_q1 > 0 else 'underperforming'} Q1 by **{abs(q4_vs_q1):.1f}%**.
        Peak: **{peak_month['month_label']}** | Lowest: **{lowest_month['month_label']}**
        """)

    # ── 2. CUSTOMER TYPE ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("2️⃣ Customer Type Breakdown")

    if 'new_customers' in df_year.columns and 'repeat_customers' in df_year.columns:
        total_new    = df_year['new_customers'].sum()
        total_repeat = df_year['repeat_customers'].sum()
        total_cust   = total_new + total_repeat

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("🆕 New Customers (2025)",    f"{total_new:,}",    f"{total_new/total_cust*100:.1f}%" if total_cust > 0 else "")
            st.metric("🔄 Returning Customers",     f"{total_repeat:,}", f"{total_repeat/total_cust*100:.1f}%" if total_cust > 0 else "")

            # Best new acquisition month
            best_new_month = monthly.loc[monthly['new_customers'].idxmax(), 'month_label'] if 'new_customers' in monthly.columns else "N/A"
            st.info(f"**📅 Best New Acquisition Month:** {best_new_month}")

        with col2:
            fig = px.bar(
                monthly, x='month_label',
                y=['new_customers', 'repeat_customers'],
                title='Monthly New vs Returning Customers',
                barmode='stack',
                labels={'value': 'Customers', 'month_label': 'Month', 'variable': 'Type'},
                color_discrete_map={'new_customers': '#ff7f0e', 'repeat_customers': '#2ca02c'}
            )
            fig.update_layout(height=350, plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("New/Repeat customer breakdown not available in daily_metrics.")

    # ── 3. CONVERSION RATE TREND ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("3️⃣ Conversion Rate Trend")

    peak_conv_month   = monthly.loc[monthly['conv_rate'].idxmax()]
    lowest_conv_month = monthly.loc[monthly['conv_rate'].idxmin()]
    conv_trend        = trend_label(monthly['conv_rate'])

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.line(
            monthly, x='month_label', y='conv_rate',
            title='Monthly Conversion Rate (2025)',
            labels={'conv_rate': 'Conversion Rate (%)', 'month_label': 'Month'},
            markers=True
        )
        fig.add_hline(y=3.0, line_dash="dash", line_color="red",
                      annotation_text="Industry Avg (3%)", annotation_position="top right")
        fig.update_traces(line_color='#2ca02c', line_width=2)
        fig.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("🏆 Highest Conv Month", peak_conv_month['month_label'],   f"{peak_conv_month['conv_rate']:.2f}%")
        st.metric("📉 Lowest Conv Month",  lowest_conv_month['month_label'], f"{lowest_conv_month['conv_rate']:.2f}%")
        st.markdown(f"**Trend:** {conv_trend}")
        st.info(f"""
        **💡 Insight**
        Conversion is **{conv_trend.split()[1]}**.
        Best month: **{peak_conv_month['month_label']}** ({peak_conv_month['conv_rate']:.2f}%)
        Worst month: **{lowest_conv_month['month_label']}** ({lowest_conv_month['conv_rate']:.2f}%)
        """)

    # ── 4. AOV TREND ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("4️⃣ Average Order Value Trend")

    peak_aov_month   = monthly.loc[monthly['aov'].idxmax()]
    lowest_aov_month = monthly.loc[monthly['aov'].idxmin()]
    aov_trend        = trend_label(monthly['aov'])

    # Check discount data for AOV impact
    df_coupon_year = data['coupon_performance'][
        data['coupon_performance']['date'].dt.year == 2025
    ].copy()

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.line(
            monthly, x='month_label', y='aov',
            title='Monthly Average Order Value (2025)',
            labels={'aov': 'AOV ($)', 'month_label': 'Month'},
            markers=True
        )
        fig.update_traces(line_color='#d62728', line_width=2)
        fig.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("🏆 Highest AOV Month", peak_aov_month['month_label'],   f"${peak_aov_month['aov']:.2f}")
        st.metric("📉 Lowest AOV Month",  lowest_aov_month['month_label'], f"${lowest_aov_month['aov']:.2f}")
        st.markdown(f"**Trend:** {aov_trend}")

        if not df_coupon_year.empty:
            coupon_orders    = df_coupon_year[df_coupon_year['discount_coupon_code'] != 'NO_COUPON']['usage_count'].sum()
            no_coupon_orders = df_coupon_year[df_coupon_year['discount_coupon_code'] == 'NO_COUPON']['usage_count'].sum()
            total_c          = coupon_orders + no_coupon_orders
            st.info(f"""
            **💡 Insight**
            AOV trend is **{aov_trend.split()[1]}**.
            {coupon_orders/total_c*100:.1f}% of orders used discount coupons.
            Discounts may be suppressing AOV in high-usage months.
            """)

    # ── MONTHLY SUMMARY TABLE ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Monthly Summary Table (2025)")

    summary_table = monthly[['month_label', 'revenue', 'orders', 'sessions', 'aov', 'conv_rate']].copy()
    summary_table.columns = ['Month', 'Revenue ($)', 'Orders', 'Sessions', 'AOV ($)', 'Conv Rate (%)']
    st.dataframe(
        summary_table.style.format({
            'Revenue ($)':   '${:,.0f}',
            'Orders':        '{:,}',
            'Sessions':      '{:,}',
            'AOV ($)':       '${:.2f}',
            'Conv Rate (%)': '{:.2f}%'
        }).background_gradient(subset=['Revenue ($)'], cmap='Blues'),
        use_container_width=True,
        height=460
    )

# ==============================================================================
# PAGE 2: CONVERSION FUNNEL
# ==============================================================================

def page_conversion_funnel(data, filters):
    """Conversion Funnel — Yearly totals + Monthly breakdown"""

    st.markdown('<div class="main-header">🔄 Conversion Funnel Analysis</div>', unsafe_allow_html=True)
    st.markdown("### Track user journey from visit to purchase")

    # Full year funnel
    df_year = data['session_funnel'][
        (data['session_funnel']['date'] >= pd.Timestamp("2025-01-01")) &
        (data['session_funnel']['date'] <= pd.Timestamp("2025-12-31"))
    ].copy()

    # Filtered (monthly or yearly)
    df = data['session_funnel'][
        (data['session_funnel']['date'] >= filters['start_date']) &
        (data['session_funnel']['date'] <= filters['end_date'])
    ].copy()

    if df.empty:
        st.warning("No funnel data available for selected period")
        return

    # ── YEARLY FUNNEL KPIs ─────────────────────────────────────────────────────
    df_year = add_month_col(df_year)

    def funnel_rates(dff):
        total   = len(dff)
        cat_v   = dff['had_category_view'].sum()   if 'had_category_view'   in dff.columns else 0
        prod_v  = dff['had_product_view'].sum()
        cart_a  = dff['had_add_to_cart'].sum()
        checkout= dff['had_checkout_payment'].sum() if 'had_checkout_payment' in dff.columns else 0
        purch   = dff['had_order'].sum()
        return total, cat_v, prod_v, cart_a, checkout, purch

    total_y, cat_y, prod_y, cart_y, check_y, purch_y = funnel_rates(df_year)

    st.markdown("---")
    st.markdown("### 📌 2025 Yearly Funnel KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👁️ Total Sessions",    f"{total_y:,}")
    with col2:
        st.metric("📦 Product Views",     f"{prod_y:,}",  f"{prod_y/total_y*100:.1f}% of sessions" if total_y > 0 else "")
    with col3:
        st.metric("🛒 Cart Adds",         f"{cart_y:,}",  f"{cart_y/total_y*100:.1f}% of sessions" if total_y > 0 else "")
    with col4:
        st.metric("✅ Purchases",         f"{purch_y:,}", f"{purch_y/total_y*100:.1f}% of sessions" if total_y > 0 else "")

    # ── YEARLY FUNNEL CHART ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Full Funnel (2025 Yearly)")

    col1, col2 = st.columns([2, 1])
    with col1:
        funnel_stages = ['Sessions', 'Category Views', 'Product Views', 'Add to Cart', 'Checkout', 'Purchase']
        funnel_counts = [total_y, cat_y, prod_y, cart_y, check_y, purch_y]

        fig = go.Figure(go.Funnel(
            y=funnel_stages,
            x=funnel_counts,
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(color=['#3498db','#5dade2','#2ecc71','#f39c12','#e67e22','#e74c3c'])
        ))
        fig.update_layout(title='2025 Yearly Conversion Funnel', height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📈 Step Conversion Rates**")
        if total_y > 0:
            st.metric("Sessions → Product View",  f"{prod_y/total_y*100:.1f}%")
            st.metric("Product View → Cart",       f"{cart_y/prod_y*100:.1f}%"  if prod_y > 0 else "N/A")
            st.metric("Cart → Checkout",           f"{check_y/cart_y*100:.1f}%" if cart_y > 0 else "N/A")
            st.metric("Checkout → Purchase",       f"{purch_y/check_y*100:.1f}%" if check_y > 0 else "N/A")
            st.metric("Overall (Session→Purchase)",f"{purch_y/total_y*100:.1f}%")

    # ── MONTHLY FUNNEL BREAKDOWN ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Funnel Breakdown")

    monthly_funnel = df_year.groupby(['year','month']).agg(
        sessions       = ('session_id',       'count'),
        product_views  = ('had_product_view',  'sum'),
        cart_adds      = ('had_add_to_cart',   'sum'),
        purchases      = ('had_order',         'sum'),
    ).reset_index().sort_values('month')

    monthly_funnel['month_label']  = monthly_funnel['month'].apply(get_month_name)
    monthly_funnel['prod_rate']    = (monthly_funnel['product_views'] / monthly_funnel['sessions'] * 100).round(2)
    monthly_funnel['cart_rate']    = (monthly_funnel['cart_adds']     / monthly_funnel['sessions'] * 100).round(2)
    monthly_funnel['conv_rate']    = (monthly_funnel['purchases']     / monthly_funnel['sessions'] * 100).round(2)
    monthly_funnel['cart_to_purch']= (monthly_funnel['purchases']     / monthly_funnel['cart_adds'] * 100).fillna(0).round(2)

    best_month  = monthly_funnel.loc[monthly_funnel['conv_rate'].idxmax()]
    worst_month = monthly_funnel.loc[monthly_funnel['conv_rate'].idxmin()]
    funnel_trend = trend_label(monthly_funnel['conv_rate'])

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.line(
            monthly_funnel, x='month_label',
            y=['prod_rate', 'cart_rate', 'conv_rate'],
            title='Monthly Funnel Conversion Rates (%)',
            labels={'value': 'Rate (%)', 'month_label': 'Month', 'variable': 'Stage'},
            markers=True,
            color_discrete_map={
                'prod_rate': '#3498db',
                'cart_rate': '#f39c12',
                'conv_rate': '#2ecc71'
            }
        )
        fig.update_layout(height=380, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("🏆 Best Month",  best_month['month_label'],  f"{best_month['conv_rate']:.2f}% conv")
        st.metric("📉 Worst Month", worst_month['month_label'], f"{worst_month['conv_rate']:.2f}% conv")
        st.markdown(f"**Funnel Trend:** {funnel_trend}")
        st.info(f"""
        **💡 Insight**
        Funnel is **{funnel_trend.split()[1]}**.
        Best performing month: **{best_month['month_label']}**
        Worst performing month: **{worst_month['month_label']}**
        Focus on improving cart→purchase rate ({monthly_funnel['cart_to_purch'].mean():.1f}% avg).
        """)

    # ── TIME METRICS ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⏱️ Time Metrics")

    col1, col2 = st.columns(2)
    with col1:
        avg_time_to_cart = df[df['time_to_cart_minutes'].notna()]['time_to_cart_minutes'].mean()
        st.markdown(f"**⏰ Avg Time to Add to Cart:** `{avg_time_to_cart:.1f}` min")
        fig = px.histogram(
            df[df['time_to_cart_minutes'].notna()],
            x='time_to_cart_minutes', nbins=30,
            title='Distribution of Time to Cart',
            labels={'time_to_cart_minutes': 'Minutes'}
        )
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        avg_time_to_purchase = df[df['time_to_order_minutes'].notna()]['time_to_order_minutes'].mean()
        st.markdown(f"**⏰ Avg Time to Purchase:** `{avg_time_to_purchase:.1f}` min")
        fig = px.histogram(
            df[df['time_to_order_minutes'].notna()],
            x='time_to_order_minutes', nbins=30,
            title='Distribution of Time to Purchase',
            labels={'time_to_order_minutes': 'Minutes'}
        )
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Monthly time metric variation
    st.markdown("---")
    st.subheader("📅 Monthly Time-to-Purchase Variation")

    df_year_time = df_year.copy()
    monthly_time = df_year_time[df_year_time['time_to_order_minutes'].notna()].groupby('month').agg(
        avg_time_to_order=('time_to_order_minutes', 'mean')
    ).reset_index()
    monthly_time['month_label'] = monthly_time['month'].apply(get_month_name)

    fig = px.bar(
        monthly_time, x='month_label', y='avg_time_to_order',
        title='Avg Time to Purchase by Month (minutes)',
        labels={'avg_time_to_order': 'Minutes', 'month_label': 'Month'},
        color='avg_time_to_order', color_continuous_scale='RdYlGn_r'
    )
    fig.update_layout(height=350, showlegend=False, plot_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True)

    # ── FUNNEL BY DEVICE TYPE ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📱 Funnel by Device Type")

    df_with_device = df.merge(
        data['session_attribution'][['session_id', 'device_type']],
        on='session_id', how='left'
    )

    if 'device_type' in df_with_device.columns:
        device_funnel = df_with_device.groupby('device_type').agg({
            'session_id':       'count',
            'had_product_view': 'sum',
            'had_add_to_cart':  'sum',
            'had_order':        'sum'
        }).reset_index()
        device_funnel.columns = ['Device', 'Sessions', 'Product Views', 'Cart Adds', 'Purchases']
        device_funnel['Product View Rate'] = (device_funnel['Product Views'] / device_funnel['Sessions'] * 100).round(2)
        device_funnel['Cart Rate']         = (device_funnel['Cart Adds']     / device_funnel['Sessions'] * 100).round(2)
        device_funnel['Conversion Rate']   = (device_funnel['Purchases']     / device_funnel['Sessions'] * 100).round(2)

        fig = px.bar(
            device_funnel, x='Device',
            y=['Product View Rate', 'Cart Rate', 'Conversion Rate'],
            title='Conversion Rates by Device Type',
            barmode='group',
            labels={'value': 'Rate (%)', 'variable': 'Funnel Stage'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            device_funnel.style.format({
                'Sessions': '{:,}', 'Product Views': '{:,}',
                'Cart Adds': '{:,}', 'Purchases': '{:,}',
                'Product View Rate': '{:.2f}%',
                'Cart Rate': '{:.2f}%',
                'Conversion Rate': '{:.2f}%'
            }),
            use_container_width=True
        )

    # ── RECOMMENDATIONS ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 Optimization Recommendations")

    prod_rate_y = prod_y / total_y * 100 if total_y > 0 else 0
    cart_to_purch_y = purch_y / cart_y * 100 if cart_y > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        if prod_rate_y < 50:
            st.error(f"**⚠️ Low Product View Rate ({prod_rate_y:.1f}%)**\n\n- Poor navigation\n- Unclear value proposition\n\n**Fix:** Improve homepage clarity, add featured products")
        else:
            st.success(f"**✅ Good Product View Rate ({prod_rate_y:.1f}%)**\n\nUsers are finding products successfully")
    with col2:
        if cart_to_purch_y < 30:
            st.error(f"**⚠️ Low Cart→Purchase ({cart_to_purch_y:.1f}%)**\n\n- Checkout friction\n- Hidden shipping costs\n\n**Fix:** Simplify checkout, show costs upfront")
        else:
            st.success(f"**✅ Good Cart→Purchase ({cart_to_purch_y:.1f}%)**\n\nCheckout is working well")
    with col3:
        if avg_time_to_purchase > 30:
            st.warning(f"**⏰ Long Journey ({avg_time_to_purchase:.0f} min)**\n\n- High consideration products\n\n**Fix:** Add comparison tools, reviews")
        else:
            st.success(f"**⚡ Quick Journey ({avg_time_to_purchase:.0f} min)**\n\nUsers decide fast")

# ==============================================================================
# PAGE 3: PRODUCT PERFORMANCE
# ==============================================================================

def page_product_performance(data, filters):
    """Product Performance — Yearly Top 10 + Monthly trends"""

    st.markdown('<div class="main-header">📦 Product Performance</div>', unsafe_allow_html=True)
    st.markdown("### Analyze product sales and identify opportunities")

    # Full year product data
    df_year = data['product_performance'][
        data['product_performance']['date'].dt.year == 2025
    ].copy()
    df_year = add_month_col(df_year)

    # Filtered data
    df = data['product_performance'][
        (data['product_performance']['date'] >= filters['start_date']) &
        (data['product_performance']['date'] <= filters['end_date'])
    ].copy()
    if filters['products']:
        df = df[df['product_name'].isin(filters['products'])]
    if df.empty:
        st.warning("No product data available for selected filters")
        return

    # Yearly product summary
    yearly_product = df_year.groupby('product_name').agg({
        'total_revenue':       'sum',
        'total_quantity_sold': 'sum',
        'times_purchased':     'sum',
        'times_added_to_cart': 'sum',
        'cart_to_purchase_rate': 'mean'
    }).reset_index().sort_values('total_revenue', ascending=False)

    # ── YEARLY TOP KPIs ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 2025 Yearly Product KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Revenue",     f"${yearly_product['total_revenue'].sum():,.0f}")
    with col2:
        st.metric("📦 Units Sold",        f"{yearly_product['total_quantity_sold'].sum():,.0f}")
    with col3:
        st.metric("🏷️ Active Products",  f"{len(yearly_product):,}")
    with col4:
        st.metric("🎯 Avg Cart→Purchase", f"{yearly_product['cart_to_purchase_rate'].mean():.1f}%")

    # ── TOP 10 YEARLY ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🏆 Top 10 Products — 2025 Yearly")

    top10 = yearly_product.head(10)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            top10, y='product_name', x='total_revenue', orientation='h',
            title='Top 10 by Revenue',
            labels={'total_revenue': 'Revenue ($)', 'product_name': 'Product'},
            color='total_revenue', color_continuous_scale='Blues'
        )
        fig.update_layout(height=450, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            top10, y='product_name', x='total_quantity_sold', orientation='h',
            title='Top 10 by Units Sold',
            labels={'total_quantity_sold': 'Units Sold', 'product_name': 'Product'},
            color='total_quantity_sold', color_continuous_scale='Greens'
        )
        fig.update_layout(height=450, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # ── MONTHLY SALES TREND PER PRODUCT ───────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Monthly Sales Trend by Product")

    top_products_list = yearly_product.head(6)['product_name'].tolist()
    monthly_product = df_year.groupby(['month', 'product_name']).agg(
        revenue  = ('total_revenue', 'sum'),
        quantity = ('total_quantity_sold', 'sum')
    ).reset_index()
    monthly_product['month_label'] = monthly_product['month'].apply(get_month_name)
    monthly_top = monthly_product[monthly_product['product_name'].isin(top_products_list)]

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(
            monthly_top, x='month_label', y='revenue', color='product_name',
            title='Monthly Revenue by Top Products',
            labels={'revenue': 'Revenue ($)', 'month_label': 'Month', 'product_name': 'Product'},
            markers=True
        )
        fig.update_layout(height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            monthly_top, x='month_label', y='quantity', color='product_name',
            title='Monthly Units Sold by Top Products',
            labels={'quantity': 'Units', 'month_label': 'Month', 'product_name': 'Product'},
            markers=True
        )
        fig.update_layout(height=400, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # Peak selling month per product
    st.markdown("---")
    st.subheader("🗓️ Peak Selling Month per Product")

    peak_months = monthly_product[monthly_product['product_name'].isin(top_products_list)].copy()
    peak_months = peak_months.loc[peak_months.groupby('product_name')['revenue'].idxmax()]
    peak_months = peak_months[['product_name', 'month_label', 'revenue', 'quantity']].rename(columns={
        'product_name': 'Product', 'month_label': 'Peak Month',
        'revenue': 'Peak Revenue ($)', 'quantity': 'Peak Units'
    })
    st.dataframe(
        peak_months.style.format({'Peak Revenue ($)': '${:,.0f}', 'Peak Units': '{:,.0f}'}),
        use_container_width=True
    )

    # ── CART → PURCHASE CONVERSION ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Cart-to-Purchase Conversion by Product")

    products_with_data = yearly_product[yearly_product['times_added_to_cart'] >= 10].copy()
    products_with_data = products_with_data.sort_values('cart_to_purchase_rate', ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌟 High Views, Check Conversion**")
        high_views = yearly_product.nlargest(6, 'times_added_to_cart')[['product_name','times_added_to_cart','cart_to_purchase_rate']]
        fig = px.scatter(
            high_views, x='times_added_to_cart', y='cart_to_purchase_rate',
            text='product_name', size='times_added_to_cart',
            title='Cart Adds vs Conversion Rate',
            labels={'times_added_to_cart': 'Times Added to Cart', 'cart_to_purchase_rate': 'Cart→Purchase Rate (%)'}
        )
        fig.update_traces(textposition='top center')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**📊 Cart→Purchase Rate Ranking**")
        fig = px.bar(
            products_with_data.head(8),
            y='product_name', x='cart_to_purchase_rate', orientation='h',
            labels={'cart_to_purchase_rate': 'Conversion Rate (%)', 'product_name': 'Product'},
            color='cart_to_purchase_rate', color_continuous_scale='RdYlGn'
        )
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # ── DETAILED TABLE ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Detailed Product Performance Table")

    yearly_product['avg_price'] = (yearly_product['total_revenue'] / yearly_product['total_quantity_sold']).round(2)
    st.dataframe(
        yearly_product.style.format({
            'total_revenue': '${:,.2f}', 'total_quantity_sold': '{:,.0f}',
            'times_purchased': '{:,.0f}', 'times_added_to_cart': '{:,.0f}',
            'cart_to_purchase_rate': '{:.2f}%', 'avg_price': '${:.2f}'
        }).background_gradient(subset=['total_revenue'], cmap='Blues'),
        use_container_width=True, height=400
    )

    # ── INSIGHTS ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 Product Insights")

    col1, col2, col3 = st.columns(3)
    with col1:
        top10_pct = top10['total_revenue'].sum() / yearly_product['total_revenue'].sum() * 100
        st.info(f"**📊 Revenue Concentration**\n\nTop 10 products = **{top10_pct:.1f}%** of revenue\n\n{'⚠️ High concentration' if top10_pct > 70 else '✅ Healthy distribution'}")
    with col2:
        good = len(products_with_data[products_with_data['cart_to_purchase_rate'] > 50])
        poor = len(products_with_data[products_with_data['cart_to_purchase_rate'] < 30])
        st.info(f"**🎯 Conversion Quality**\n\n✅ High conv (>50%): **{good}** products\n⚠️ Low conv (<30%): **{poor}** products")
    with col3:
        best = yearly_product.iloc[0]
        st.info(f"**🏆 Star Product**\n\n**{best['product_name']}**\n- Revenue: ${best['total_revenue']:,.0f}\n- Units: {best['total_quantity_sold']:,.0f}\n- Conv: {best['cart_to_purchase_rate']:.1f}%")

# ==============================================================================
# PAGE 4: CUSTOMER SEGMENTATION (RFM)
# ==============================================================================

def page_customer_segmentation(data, filters):
    """Customer Segmentation — RFM Yearly + Monthly Revenue by Segment"""

    st.markdown('<div class="main-header">👥 Customer Segmentation (RFM Analysis)</div>', unsafe_allow_html=True)
    st.markdown("### Understand customer value and behavior patterns")

    df = data['user_lifetime'].copy()
    df['last_order_date'] = pd.to_datetime(df['last_order_date'])

    total_customers = len(df)
    total_ltv       = df['total_revenue'].sum()

    # ── YEARLY SUMMARY KPIs ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 2025 Customer KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Customers",       f"{total_customers:,}")
    with col2:
        st.metric("💰 Avg Customer LTV",      f"${df['total_revenue'].mean():,.0f}")
    with col3:
        st.metric("💎 Total Customer Value",  f"${total_ltv:,.0f}")
    with col4:
        st.metric("🛍️ Avg Orders/Customer",  f"{df['total_orders'].mean():.1f}")

    # ── SEGMENT DISTRIBUTION ──────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🎯 Customer Segment Distribution")
        segment_counts = df['rfm_segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        segment_counts['%'] = (segment_counts['Count'] / total_customers * 100).round(1)

        fig = px.pie(
            segment_counts, values='Count', names='Segment',
            title='Customer Segments (2025)',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

        # Segment % breakdown
        st.markdown("**Segment Breakdown:**")
        for _, row in segment_counts.iterrows():
            st.markdown(f"- **{row['Segment']}**: {row['Count']:,} customers ({row['%']:.1f}%)")

    with col2:
        st.subheader("💰 Revenue by Segment")
        segment_revenue = df.groupby('rfm_segment').agg(
            Revenue=('total_revenue', 'sum'),
            Customers=('user_id', 'count')
        ).reset_index().rename(columns={'rfm_segment': 'Segment'})
        segment_revenue = segment_revenue.sort_values('Revenue', ascending=False)
        segment_revenue['% Revenue'] = (segment_revenue['Revenue'] / total_ltv * 100).round(1)

        fig = px.bar(
            segment_revenue, x='Segment', y='Revenue',
            title='Total Revenue by Segment',
            labels={'Revenue': 'Revenue ($)'},
            color='Revenue', color_continuous_scale='Viridis',
            text=segment_revenue['% Revenue'].apply(lambda x: f"{x:.1f}%")
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── MONTHLY REVENUE BY SEGMENT ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Revenue Contribution by Segment")

    daily_orders = data['daily_metrics'][
        data['daily_metrics']['date'].dt.year == 2025
    ].copy()
    daily_orders = add_month_col(daily_orders)

    # Approximate segment revenue monthly using RFM user_lifetime + daily revenue
    # We distribute total monthly revenue proportionally by segment share
    segment_share = segment_revenue.set_index('Segment')['% Revenue'] / 100

    monthly_rev = daily_orders.groupby(['month'])['total_revenue'].sum().reset_index()
    monthly_rev['month_label'] = monthly_rev['month'].apply(get_month_name)

    seg_monthly_rows = []
    for _, mrow in monthly_rev.iterrows():
        for seg, share in segment_share.items():
            seg_monthly_rows.append({
                'month_label': mrow['month_label'],
                'month': mrow['month'],
                'Segment': seg,
                'Revenue': mrow['total_revenue'] * share
            })
    seg_monthly_df = pd.DataFrame(seg_monthly_rows).sort_values('month')

    fig = px.bar(
        seg_monthly_df, x='month_label', y='Revenue', color='Segment',
        title='Estimated Monthly Revenue by Customer Segment',
        labels={'Revenue': 'Revenue ($)', 'month_label': 'Month'},
        barmode='stack'
    )
    fig.update_layout(height=420, plot_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True)

    # ── SEGMENT PERFORMANCE TABLE ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Segment Performance Details")

    segment_stats = df.groupby('rfm_segment').agg({
        'user_id':              'count',
        'total_revenue':        ['sum', 'mean'],
        'total_orders':         'mean',
        'avg_order_value':      'mean',
        'days_since_last_order':'mean'
    }).reset_index()
    segment_stats.columns = ['Segment','Customers','Total Revenue','Avg LTV','Avg Orders','Avg AOV','Avg Days Since Purchase']
    segment_stats = segment_stats.sort_values('Total Revenue', ascending=False)
    segment_stats['% of Customers'] = (segment_stats['Customers'] / total_customers * 100).round(1)
    segment_stats['% of Revenue']   = (segment_stats['Total Revenue'] / total_ltv * 100).round(1)

    st.dataframe(
        segment_stats.style.format({
            'Customers': '{:,}', 'Total Revenue': '${:,.0f}', 'Avg LTV': '${:,.0f}',
            'Avg Orders': '{:.1f}', 'Avg AOV': '${:.2f}',
            'Avg Days Since Purchase': '{:.0f}',
            '% of Customers': '{:.1f}%', '% of Revenue': '{:.1f}%'
        }).background_gradient(subset=['Total Revenue'], cmap='Greens'),
        use_container_width=True
    )

    # ── LTV DISTRIBUTION ──────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💎 Customer LTV Distribution")
        ltv_buckets = pd.cut(
            df['total_revenue'],
            bins=[0, 50, 200, 500, 1000, float('inf')],
            labels=['$0-50', '$50-200', '$200-500', '$500-1000', '$1000+']
        )
        ltv_dist = ltv_buckets.value_counts().sort_index().reset_index()
        ltv_dist.columns = ['LTV Range', 'Customers']
        fig = px.bar(
            ltv_dist, x='LTV Range', y='Customers',
            title='Customer Distribution by LTV',
            color='Customers', color_continuous_scale='Blues'
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 RFM Score Distribution")
        rfm_breakdown = pd.DataFrame({
            'Recency Score':  df['rfm_recency_score'].value_counts().sort_index(),
            'Frequency Score':df['rfm_frequency_score'].value_counts().sort_index(),
            'Monetary Score': df['rfm_monetary_score'].value_counts().sort_index()
        }).fillna(0).astype(int)

        fig = go.Figure()
        fig.add_trace(go.Bar(name='Recency',   x=rfm_breakdown.index, y=rfm_breakdown['Recency Score']))
        fig.add_trace(go.Bar(name='Frequency', x=rfm_breakdown.index, y=rfm_breakdown['Frequency Score']))
        fig.add_trace(go.Bar(name='Monetary',  x=rfm_breakdown.index, y=rfm_breakdown['Monetary Score']))
        fig.update_layout(
            title='RFM Score Distribution (1=Worst, 5=Best)',
            barmode='group', height=350,
            xaxis={'tickmode': 'linear', 'tick0': 1, 'dtick': 1}
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── RETENTION ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔄 Customer Retention Analysis")

    col1, col2 = st.columns(2)
    with col1:
        if 'has_purchase_last_year' in df.columns:
            retention_data = df['has_purchase_last_year'].value_counts().reset_index()
            retention_data.columns = ['Status', 'Count']
            retention_data['Status'] = retention_data['Status'].map({1: 'Purchased Last Year', 0: 'No Purchase Last Year'})
            fig = px.pie(
                retention_data, values='Count', names='Status',
                title='Customer Retention (YoY)', hole=0.4,
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
            retention_rate = retention_data[retention_data['Status'] == 'Purchased Last Year']['Count'].sum() / total_customers * 100
            st.markdown(f"**Retention Rate:** {retention_rate:.1f}%  {'✅ Strong' if retention_rate > 40 else '⚠️ Needs work' if retention_rate > 20 else '🚨 Critical'}")

    with col2:
        fig = px.histogram(
            df, x='days_since_last_order', nbins=30,
            title='Recency Distribution (Days Since Last Order)',
            labels={'days_since_last_order': 'Days'},
            color_discrete_sequence=['#3498db']
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        at_risk = len(df[df['days_since_last_order'] > 90])
        lost    = len(df[df['days_since_last_order'] > 365])
        st.markdown(f"**At Risk (>90 days):** {at_risk:,} ({at_risk/total_customers*100:.1f}%)")
        st.markdown(f"**Lost (>365 days):** {lost:,} ({lost/total_customers*100:.1f}%)")

    # ── ACTIONS BY SEGMENT ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🎯 Recommended Actions by Segment")

    recommendations = {
        'Champion':          ('🏆', 'Best customers — recent, frequent, high-value',   ['Enroll in VIP program', 'Offer early access', 'Request referrals']),
        'Loyal Customer':    ('💎', 'Regular buyers with consistent patterns',          ['Loyalty rewards', 'Personalized recommendations', 'Subscription options']),
        'Potential Loyalist':('🌱', 'Recent buyers showing promise',                    ['Nurture email sequences', 'Second-purchase incentive', 'Cross-sell']),
        'At Risk':           ('⚠️', 'Previously active, haven\'t bought recently',     ['Win-back campaign', 'Survey why they stopped', '"We miss you" discount']),
        'Lost':              ('😔', 'Inactive for >365 days',                           ['Aggressive re-engagement (20-30%)', 'Last-chance campaign']),
        'New Customer':      ('🎉', 'First 1-2 purchases',                              ['Welcome email series', 'First repeat purchase incentive', 'Feedback request']),
        'Needs Attention':   ('🔔', 'Moderate recency and frequency',                  ['Re-engagement email', 'Targeted offer', 'Product recommendations']),
        'Regular':           ('⭐', 'Consistent moderate buyers',                       ['Upsell to higher tier', 'Loyalty programme enrollment'])
    }
    for segment, (emoji, desc, actions) in recommendations.items():
        if segment in df['rfm_segment'].values:
            with st.expander(f"{emoji} {segment} — {desc}"):
                cnt = len(df[df['rfm_segment'] == segment])
                rev = df[df['rfm_segment'] == segment]['total_revenue'].sum()
                st.markdown(f"**Customers:** {cnt:,} ({cnt/total_customers*100:.1f}%) | **Revenue:** ${rev:,.0f}")
                for a in actions:
                    st.markdown(f"- {a}")

# ==============================================================================
# PAGE 5: MARKETING ATTRIBUTION
# ==============================================================================

def page_marketing_attribution(data, filters):
    """Marketing Attribution — Yearly Channel + Monthly breakdown"""

    st.markdown('<div class="main-header">📣 Marketing Attribution</div>', unsafe_allow_html=True)
    st.markdown("### Measure ROI of marketing channels and campaigns")

    # Full year attribution
    df_year = data['session_attribution'][
        data['session_attribution']['date'].dt.year == 2025
    ].copy()
    df_year = add_month_col(df_year)

    # Filtered
    df = data['session_attribution'][
        (data['session_attribution']['date'] >= filters['start_date']) &
        (data['session_attribution']['date'] <= filters['end_date'])
    ].copy()
    if filters['sources']:
        df = df[df['utm_source'].isin(filters['sources'])]
    if df.empty:
        st.warning("No attribution data available")
        return

    # ── YEARLY CHANNEL PERFORMANCE ─────────────────────────────────────────────
    yearly_source = df_year.groupby('utm_source').agg(
        Sessions    = ('session_id', 'count'),
        Conversions = ('converted',  'sum'),
        Revenue     = ('revenue',    'sum')
    ).reset_index().rename(columns={'utm_source': 'Source'})
    yearly_source['Conversion Rate']     = (yearly_source['Conversions'] / yearly_source['Sessions'] * 100).round(2)
    yearly_source['Revenue per Session'] = (yearly_source['Revenue']     / yearly_source['Sessions']).round(2)
    yearly_source = yearly_source.sort_values('Revenue', ascending=False)

    st.markdown("---")
    st.markdown("### 📌 2025 Yearly Channel KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔗 Total Sessions",    f"{yearly_source['Sessions'].sum():,}")
    with col2:
        st.metric("✅ Total Conversions", f"{yearly_source['Conversions'].sum():,}")
    with col3:
        st.metric("💰 Attributed Revenue",f"${yearly_source['Revenue'].sum():,.0f}")
    with col4:
        tot_s = yearly_source['Sessions'].sum()
        tot_c = yearly_source['Conversions'].sum()
        st.metric("📈 Overall Conv Rate", f"{tot_c/tot_s*100:.2f}%" if tot_s > 0 else "N/A")

    # ── CHANNEL REVENUE & CONVERSION ──────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Revenue by Channel (Yearly)")
        fig = px.bar(
            yearly_source.head(10), x='Source', y='Revenue',
            title='Top Channels by Revenue',
            color='Revenue', color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 Conversion Rate by Channel (Yearly)")
        filtered_src = yearly_source[yearly_source['Sessions'] >= 100]
        fig = px.bar(
            filtered_src.sort_values('Conversion Rate', ascending=False).head(10),
            x='Source', y='Conversion Rate',
            title='Conversion Rate (min 100 sessions)',
            color='Conversion Rate', color_continuous_scale='RdYlGn'
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── TRAFFIC DISTRIBUTION ───────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(yearly_source.head(8), values='Sessions', names='Source',
                     title='Session Distribution by Source', hole=0.4)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(yearly_source.head(8), values='Revenue', names='Source',
                     title='Revenue Distribution by Source', hole=0.4,
                     color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    # ── MONTHLY CHANNEL BREAKDOWN ──────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Channel Performance")

    top5_sources = yearly_source.head(5)['Source'].tolist()
    monthly_channel = df_year[df_year['utm_source'].isin(top5_sources)].groupby(
        ['month', 'utm_source']
    ).agg(
        Sessions    = ('session_id', 'count'),
        Revenue     = ('revenue',    'sum'),
        Conversions = ('converted',  'sum')
    ).reset_index()
    monthly_channel['month_label']     = monthly_channel['month'].apply(get_month_name)
    monthly_channel['Conversion Rate'] = (monthly_channel['Conversions'] / monthly_channel['Sessions'] * 100).round(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(
            monthly_channel, x='month_label', y='Revenue', color='utm_source',
            title='Monthly Revenue by Top 5 Channels',
            labels={'Revenue': 'Revenue ($)', 'month_label': 'Month', 'utm_source': 'Source'},
            markers=True
        )
        fig.update_layout(height=380, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            monthly_channel, x='month_label', y='Conversion Rate', color='utm_source',
            title='Monthly Conversion Rate by Channel',
            labels={'Conversion Rate': 'Conv Rate (%)', 'month_label': 'Month', 'utm_source': 'Source'},
            markers=True
        )
        fig.update_layout(height=380, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # Peak month per channel
    st.markdown("---")
    st.subheader("🗓️ Peak Month per Channel")
    peak_channel = monthly_channel.loc[monthly_channel.groupby('utm_source')['Revenue'].idxmax()]
    peak_channel = peak_channel[['utm_source','month_label','Revenue','Conversion Rate']].rename(columns={
        'utm_source': 'Channel', 'month_label': 'Peak Month',
        'Revenue': 'Peak Revenue ($)', 'Conversion Rate': 'Conv Rate (%)'
    })
    st.dataframe(
        peak_channel.style.format({'Peak Revenue ($)': '${:,.0f}', 'Conv Rate (%)': '{:.2f}%'}),
        use_container_width=True
    )

    # ── CAMPAIGN PERFORMANCE ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📢 Campaign Performance")

    if 'utm_campaign' in df.columns:
        campaign_metrics = df[df['utm_campaign'] != 'direct'].groupby('utm_campaign').agg(
            Sessions    = ('session_id', 'count'),
            Conversions = ('converted',  'sum'),
            Revenue     = ('revenue',    'sum')
        ).reset_index().rename(columns={'utm_campaign': 'Campaign'})
        campaign_metrics['Conversion Rate'] = (campaign_metrics['Conversions'] / campaign_metrics['Sessions'] * 100).round(2)
        campaign_metrics = campaign_metrics.sort_values('Revenue', ascending=False).head(15)

        fig = px.bar(
            campaign_metrics, x='Campaign', y='Revenue',
            title='Top 15 Campaigns by Revenue',
            color='Conversion Rate', color_continuous_scale='RdYlGn',
            hover_data=['Sessions', 'Conversions', 'Conversion Rate']
        )
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    # ── DETAILED TABLE ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Detailed Channel Performance")

    source_metrics = df.groupby('utm_source').agg(
        Sessions    = ('session_id', 'count'),
        Conversions = ('converted',  'sum'),
        Revenue     = ('revenue',    'sum')
    ).reset_index().rename(columns={'utm_source': 'Source'})
    source_metrics['Conversion Rate']     = (source_metrics['Conversions'] / source_metrics['Sessions'] * 100).round(2)
    source_metrics['Revenue per Session'] = (source_metrics['Revenue']     / source_metrics['Sessions']).round(2)
    source_metrics = source_metrics.sort_values('Revenue', ascending=False)

    st.dataframe(
        source_metrics.style.format({
            'Sessions': '{:,}', 'Conversions': '{:,}',
            'Revenue': '${:,.2f}', 'Conversion Rate': '{:.2f}%',
            'Revenue per Session': '${:.2f}'
        }).background_gradient(subset=['Revenue'], cmap='Greens'),
        use_container_width=True, height=400
    )

    # ── MARKETING INSIGHTS ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 Marketing Insights")

    overall_conv = source_metrics['Conversions'].sum() / source_metrics['Sessions'].sum() * 100 if source_metrics['Sessions'].sum() > 0 else 0
    col1, col2, col3 = st.columns(3)
    with col1:
        best = source_metrics.iloc[0]
        st.success(f"**🏆 Top Channel**\n\n**{best['Source']}**\n- Revenue: ${best['Revenue']:,.0f}\n- Conv: {best['Conversion Rate']:.2f}%\n\n**Action:** Increase budget")
    with col2:
        prob = source_metrics[(source_metrics['Sessions'] > source_metrics['Sessions'].median()) & (source_metrics['Conversion Rate'] < overall_conv)]
        if not prob.empty:
            p = prob.iloc[0]
            st.warning(f"**⚠️ Needs Optimization**\n\n**{p['Source']}**\n- Traffic: {p['Sessions']:,}\n- Low conv: {p['Conversion Rate']:.2f}%\n\n**Action:** Review landing pages")
        else:
            st.info("All channels performing well!")
    with col3:
        direct = source_metrics[source_metrics['Source'] == 'direct']
        if not direct.empty:
            d = direct.iloc[0]
            dpct = d['Sessions'] / source_metrics['Sessions'].sum() * 100
            st.info(f"**🔗 Direct Traffic**\n\n{dpct:.1f}% of sessions\n- Revenue: ${d['Revenue']:,.0f}\n\n{'✅ Good brand recognition' if dpct > 30 else 'Consider brand campaigns'}")

# ==============================================================================
# PAGE 6: PAGE ENGAGEMENT & UX
# ==============================================================================

def page_engagement_ux(data, filters):
    """Page Engagement & UX — Yearly top pages + Monthly trends"""

    st.markdown('<div class="main-header">📄 Page Engagement & UX</div>', unsafe_allow_html=True)
    st.markdown("### Optimize website content and user experience")

    # Full year
    df_year = data['page_engagement'][
        data['page_engagement']['date'].dt.year == 2025
    ].copy()
    df_year = add_month_col(df_year)

    # Filtered
    df = data['page_engagement'][
        (data['page_engagement']['date'] >= filters['start_date']) &
        (data['page_engagement']['date'] <= filters['end_date'])
    ].copy()
    if df.empty:
        st.warning("No page engagement data available")
        return

    # Yearly page summary
    yearly_pages = df_year.groupby('path').agg(
        pageviews         = ('pageviews',       'sum'),
        unique_users      = ('unique_users',     'sum'),
        sessions_with_page= ('sessions_with_page','sum'),
        avg_scroll_depth  = ('avg_scroll_depth', 'mean'),
        total_clicks      = ('total_clicks',     'sum')
    ).reset_index()
    yearly_pages['click_per_pageview'] = (yearly_pages['total_clicks'] / yearly_pages['pageviews']).round(2)
    yearly_pages = yearly_pages.sort_values('pageviews', ascending=False)

    # ── YEARLY TOP KPIs ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 2025 Yearly Engagement KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👁️ Total Pageviews",  f"{yearly_pages['pageviews'].sum():,}")
    with col2:
        st.metric("📄 Unique Pages",     f"{len(yearly_pages):,}")
    with col3:
        st.metric("📜 Avg Scroll Depth", f"{yearly_pages['avg_scroll_depth'].mean():.1f}%")
    with col4:
        st.metric("🖱️ Total Clicks",    f"{yearly_pages['total_clicks'].sum():,}")

    # ── TOP PAGES YEARLY ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔝 Top 10 Most Viewed Pages (2025 Yearly)")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            yearly_pages.head(10), y='path', x='pageviews', orientation='h',
            title='Top Pages by Pageviews',
            labels={'pageviews': 'Pageviews', 'path': 'Page'},
            color='pageviews', color_continuous_scale='Blues'
        )
        fig.update_layout(height=450, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            yearly_pages.nlargest(10, 'unique_users'), y='path', x='unique_users', orientation='h',
            title='Top Pages by Unique Users',
            labels={'unique_users': 'Unique Users', 'path': 'Page'},
            color='unique_users', color_continuous_scale='Greens'
        )
        fig.update_layout(height=450, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # ── HIGH CTR PAGES (YEARLY) ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🖱️ Highest CTR Pages (Yearly)")

    high_ctr_yearly = yearly_pages[yearly_pages['pageviews'] >= 50].nlargest(10, 'click_per_pageview')
    fig = px.bar(
        high_ctr_yearly, y='path', x='click_per_pageview', orientation='h',
        title='Top 10 Pages by Click Rate (min 50 views)',
        labels={'click_per_pageview': 'Clicks/Pageview', 'path': 'Page'},
        color='click_per_pageview', color_continuous_scale='Purples'
    )
    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

    # ── SCROLL DEPTH ANALYSIS ──────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📜 High Scroll Pages")
        high_scroll = yearly_pages[yearly_pages['pageviews'] >= 50].nlargest(10, 'avg_scroll_depth')
        fig = px.bar(
            high_scroll, y='path', x='avg_scroll_depth', orientation='h',
            title='Top Pages by Scroll Depth',
            color='avg_scroll_depth', color_continuous_scale='Greens'
        )
        fig.update_layout(height=380, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⚠️ Low Scroll Pages")
        low_scroll = yearly_pages[yearly_pages['pageviews'] >= 50].nsmallest(10, 'avg_scroll_depth')
        fig = px.bar(
            low_scroll, y='path', x='avg_scroll_depth', orientation='h',
            title='Bottom Pages by Scroll Depth',
            color='avg_scroll_depth', color_continuous_scale='Reds_r'
        )
        fig.update_layout(height=380, showlegend=False, yaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig, use_container_width=True)

    # ── MONTHLY ENGAGEMENT TREND ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Engagement Trends")

    monthly_eng = df_year.groupby('month').agg(
        pageviews       = ('pageviews',       'sum'),
        avg_scroll      = ('avg_scroll_depth','mean'),
        total_clicks    = ('total_clicks',    'sum')
    ).reset_index()
    monthly_eng['month_label'] = monthly_eng['month'].apply(get_month_name)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            monthly_eng, x='month_label', y='pageviews',
            title='Monthly Pageviews (2025)',
            labels={'pageviews': 'Pageviews', 'month_label': 'Month'},
            color='pageviews', color_continuous_scale='Blues'
        )
        fig.update_layout(height=350, showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            monthly_eng, x='month_label', y='avg_scroll',
            title='Monthly Avg Scroll Depth (%)',
            labels={'avg_scroll': 'Scroll Depth (%)', 'month_label': 'Month'},
            markers=True
        )
        fig.update_traces(line_color='#2ca02c', line_width=2)
        fig.update_layout(height=350, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    # Peak engagement month
    peak_eng_month = monthly_eng.loc[monthly_eng['pageviews'].idxmax()]
    eng_trend      = trend_label(monthly_eng['pageviews'])
    st.info(f"**💡 Engagement Insight:** Peak engagement month: **{peak_eng_month['month_label']}** ({peak_eng_month['pageviews']:,} pageviews). Overall trend: {eng_trend}")

    # ── PAGE TYPE ANALYSIS ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📂 Performance by Page Type")

    def categorize_page(path):
        if pd.isna(path): return 'Other'
        path = path.lower()
        if '/product' in path:    return 'Product Page'
        elif '/category' in path or '/collection' in path: return 'Category Page'
        elif '/cart' in path:     return 'Cart'
        elif '/checkout' in path: return 'Checkout'
        elif path in ['/', '/home']: return 'Homepage'
        elif '/blog' in path or '/article' in path: return 'Blog/Content'
        else: return 'Other'

    yearly_pages['page_type'] = yearly_pages['path'].apply(categorize_page)
    type_summary = yearly_pages.groupby('page_type').agg(
        pageviews       = ('pageviews',       'sum'),
        avg_scroll_depth= ('avg_scroll_depth','mean'),
        click_per_pv    = ('click_per_pageview','mean')
    ).reset_index().sort_values('pageviews', ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(type_summary, x='page_type', y='pageviews', title='Pageviews by Page Type',
                     color='pageviews', color_continuous_scale='Blues')
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(type_summary, x='page_type', y='avg_scroll_depth', title='Avg Scroll Depth by Page Type',
                     color='avg_scroll_depth', color_continuous_scale='Greens')
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── DETAILED TABLE ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Detailed Page Performance")

    page_summary = df.groupby('path').agg(
        pageviews         = ('pageviews',       'sum'),
        unique_users      = ('unique_users',     'sum'),
        sessions_with_page= ('sessions_with_page','sum'),
        avg_scroll_depth  = ('avg_scroll_depth', 'mean'),
        total_clicks      = ('total_clicks',     'sum')
    ).reset_index()
    page_summary['click_per_pageview'] = (page_summary['total_clicks'] / page_summary['pageviews']).round(2)
    page_summary = page_summary.sort_values('pageviews', ascending=False)

    st.dataframe(
        page_summary.head(50).style.format({
            'pageviews': '{:,}', 'unique_users': '{:,}',
            'sessions_with_page': '{:,}', 'avg_scroll_depth': '{:.1f}%',
            'total_clicks': '{:,}', 'click_per_pageview': '{:.2f}'
        }).background_gradient(subset=['pageviews'], cmap='Blues'),
        use_container_width=True, height=400
    )

    # ── UX RECOMMENDATIONS ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 UX Optimization Recommendations")

    col1, col2, col3 = st.columns(3)
    with col1:
        low_scroll_pages = len(yearly_pages[(yearly_pages['avg_scroll_depth'] < 30) & (yearly_pages['pageviews'] >= 50)])
        st.warning(f"**⚠️ Low Engagement Pages**\n\n{low_scroll_pages} pages with <30% scroll depth\n\n- Content too long/boring\n- Slow load\n\n**Action:** Review content structure")
    with col2:
        low_ctr_pages = page_summary[(page_summary['pageviews'] >= page_summary['pageviews'].median()) & (page_summary['click_per_pageview'] < 1)]
        if not low_ctr_pages.empty:
            st.warning(f"**🖱️ Low Click-Through**\n\n{len(low_ctr_pages)} popular pages with <1 click/view\n\n- Weak CTAs\n\n**Action:** Add prominent CTAs")
    with col3:
        best_type = type_summary.iloc[0]
        st.success(f"**✅ Top Page Type**\n\n**{best_type['page_type']}**\n- Views: {best_type['pageviews']:,.0f}\n- Scroll: {best_type['avg_scroll_depth']:.1f}%")

# ==============================================================================
# PAGE 7: DISCOUNT & PROMOTION ANALYSIS
# ==============================================================================

def page_promotions(data, filters):
    """Discount & Promotion — Yearly overview + Monthly patterns"""

    st.markdown('<div class="main-header">💰 Discount & Promotion Analysis</div>', unsafe_allow_html=True)
    st.markdown("### Measure effectiveness of promotional campaigns")

    # Full year coupon data
    df_year = data['coupon_performance'][
        data['coupon_performance']['date'].dt.year == 2025
    ].copy()
    df_year = add_month_col(df_year)

    # Filtered
    df = data['coupon_performance'][
        (data['coupon_performance']['date'] >= filters['start_date']) &
        (data['coupon_performance']['date'] <= filters['end_date'])
    ].copy()
    if df.empty:
        st.warning("No coupon data available for selected period")
        return

    with_coupon    = df[df['discount_coupon_code'] != 'NO_COUPON']
    without_coupon = df[df['discount_coupon_code'] == 'NO_COUPON']

    total_discount         = with_coupon['total_discount_given'].sum()
    revenue_with_coupon    = with_coupon['gross_revenue'].sum()
    revenue_without_coupon = without_coupon['gross_revenue'].sum()
    total_revenue          = revenue_with_coupon + revenue_without_coupon
    orders_with_coupon     = with_coupon['usage_count'].sum()
    orders_without_coupon  = without_coupon['usage_count'].sum()

    # ── YEARLY KPIs ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 2025 Yearly Discount KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💸 Total Discount Given", f"${total_discount:,.0f}")
    with col2:
        coupon_pct = revenue_with_coupon / total_revenue * 100 if total_revenue > 0 else 0
        st.metric("📊 % Revenue with Coupons", f"{coupon_pct:.1f}%")
    with col3:
        aov_with    = revenue_with_coupon    / orders_with_coupon    if orders_with_coupon > 0    else 0
        st.metric("💳 AOV (with coupon)",    f"${aov_with:.2f}")
    with col4:
        aov_without = revenue_without_coupon / orders_without_coupon if orders_without_coupon > 0 else 0
        st.metric("💳 AOV (no coupon)",      f"${aov_without:.2f}")

    # AOV impact message
    aov_diff = calculate_change(aov_with, aov_without)
    if aov_with > aov_without:
        st.success(f"✅ Coupons **increase** AOV by {aov_diff:.1f}% — customers buy more with discounts!")
    else:
        st.warning(f"⚠️ Coupons **decrease** AOV by {abs(aov_diff):.1f}% — customers may only buy cheap items with discounts")

    # ── YEARLY COUPON vs NO COUPON ─────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Revenue Distribution (Yearly)")
        rev_comp = pd.DataFrame({
            'Type': ['With Coupon', 'Without Coupon'],
            'Revenue': [revenue_with_coupon, revenue_without_coupon],
            'Orders':  [orders_with_coupon,  orders_without_coupon]
        })
        fig = px.pie(rev_comp, values='Revenue', names='Type',
                     title='Revenue: Coupon vs No Coupon', hole=0.4,
                     color_discrete_sequence=['#ff6b6b', '#4ecdc4'])
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🛍️ Order Distribution (Yearly)")
        fig = px.pie(rev_comp, values='Orders', names='Type',
                     title='Orders: Coupon vs No Coupon', hole=0.4,
                     color_discrete_sequence=['#ff6b6b', '#4ecdc4'])
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    # ── MONTHLY DISCOUNT USAGE ─────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Monthly Discount Patterns")

    with_coupon_year = df_year[df_year['discount_coupon_code'] != 'NO_COUPON']
    monthly_discount = with_coupon_year.groupby('month').agg(
        discount_given = ('total_discount_given', 'sum'),
        gross_revenue  = ('gross_revenue',         'sum'),
        usage_count    = ('usage_count',            'sum')
    ).reset_index()
    monthly_discount['month_label']    = monthly_discount['month'].apply(get_month_name)
    monthly_discount['discount_rate']  = (monthly_discount['discount_given'] / monthly_discount['gross_revenue'] * 100).round(2)

    peak_disc_month  = monthly_discount.loc[monthly_discount['usage_count'].idxmax()]
    disc_trend       = trend_label(monthly_discount['usage_count'])

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            monthly_discount, x='month_label', y='usage_count',
            title='Monthly Coupon Usage Count',
            labels={'usage_count': 'Coupons Used', 'month_label': 'Month'},
            color='usage_count', color_continuous_scale='Oranges'
        )
        fig.update_layout(height=350, showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            monthly_discount, x='month_label', y='discount_rate',
            title='Monthly Discount Rate (% of Revenue)',
            labels={'discount_rate': 'Discount Rate (%)', 'month_label': 'Month'},
            color='discount_rate', color_continuous_scale='Reds'
        )
        fig.update_layout(height=350, showlegend=False, plot_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    st.info(f"**💡 Seasonal Pattern:** Coupon usage is **{disc_trend.split()[1]}**. Peak month: **{peak_disc_month['month_label']}** ({peak_disc_month['usage_count']:,} uses). High-usage months may reflect seasonal/festive promotions.")

    # ── MONTHLY DISCOUNT IMPACT ON CONVERSION ──────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Monthly Discount Impact on Revenue")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=monthly_discount['month_label'], y=monthly_discount['gross_revenue'],
               name="Gross Revenue", marker_color='#4ecdc4'), secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=monthly_discount['month_label'], y=monthly_discount['discount_given'],
                   name="Discount Given", line=dict(color='red', width=2)), secondary_y=True
    )
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Gross Revenue ($)", secondary_y=False)
    fig.update_yaxes(title_text="Discount Given ($)", secondary_y=True)
    fig.update_layout(title="Monthly Revenue vs Discount Given", height=400, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    # ── TOP COUPONS ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🏆 Most Popular Coupons")

    coupon_summary = with_coupon.groupby('discount_coupon_code').agg(
        usage_count          = ('usage_count',        'sum'),
        total_discount_given = ('total_discount_given','sum'),
        gross_revenue        = ('gross_revenue',       'sum'),
        avg_order_value      = ('avg_order_value',     'mean'),
        discount_percentage  = ('discount_percentage', 'mean')
    ).reset_index()
    coupon_summary = coupon_summary.rename(columns={'gross_revenue': 'total_revenue'})
    coupon_summary = coupon_summary.sort_values('usage_count', ascending=False).head(15)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            coupon_summary, y='discount_coupon_code', x='usage_count', orientation='h',
            title='Top 15 Coupons by Usage',
            labels={'usage_count': 'Times Used', 'discount_coupon_code': 'Coupon'},
            color='usage_count', color_continuous_scale='Oranges'
        )
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            coupon_summary, y='discount_coupon_code', x='total_revenue', orientation='h',
            title='Top 15 Coupons by Revenue Generated',
            labels={'total_revenue': 'Revenue ($)', 'discount_coupon_code': 'Coupon'},
            color='total_revenue', color_continuous_scale='Greens'
        )
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # ── DISCOUNT DEPTH ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📉 Discount Depth Analysis")

    col1, col2 = st.columns(2)
    with col1:
        discount_buckets = pd.cut(
            with_coupon['discount_percentage'],
            bins=[0, 10, 20, 30, 40, 100],
            labels=['0-10%', '10-20%', '20-30%', '30-40%', '40%+']
        )
        disc_dist = discount_buckets.value_counts().sort_index().reset_index()
        disc_dist.columns = ['Discount Range', 'Count']
        fig = px.bar(disc_dist, x='Discount Range', y='Count',
                     title='Distribution of Discount Levels',
                     color='Count', color_continuous_scale='Reds')
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        wcc = with_coupon.copy()
        wcc['discount_bucket'] = pd.cut(
            wcc['discount_percentage'],
            bins=[0, 10, 20, 30, 40, 100],
            labels=['0-10%', '10-20%', '20-30%', '30-40%', '40%+']
        )
        rev_by_disc = wcc.groupby('discount_bucket')['gross_revenue'].sum().reset_index()
        rev_by_disc.columns = ['Discount Range', 'Revenue']
        fig = px.bar(rev_by_disc, x='Discount Range', y='Revenue',
                     title='Revenue by Discount Level',
                     color='Revenue', color_continuous_scale='Greens')
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── DETAILED TABLE ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Detailed Coupon Performance")

    st.dataframe(
        coupon_summary.style.format({
            'usage_count': '{:,}', 'total_discount_given': '${:,.2f}',
            'total_revenue': '${:,.2f}', 'avg_order_value': '${:.2f}',
            'discount_percentage': '{:.2f}%'
        }).background_gradient(subset=['total_revenue'], cmap='Greens'),
        use_container_width=True, height=400
    )

    # ── INSIGHTS ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("💡 Promotion Insights & Recommendations")

    col1, col2, col3 = st.columns(3)
    with col1:
        roi = ((revenue_with_coupon - total_discount) / total_discount * 100) if total_discount > 0 else 0
        if roi > 200:
            st.success(f"**✅ Great ROI**\n\nEvery $1 discount → ${roi/100:.2f} revenue\n\n**Action:** Continue strategy")
        elif roi > 100:
            st.info(f"**✔️ Positive ROI**\n\nEvery $1 discount → ${roi/100:.2f} revenue\n\n**Action:** Monitor & optimise depth")
        else:
            st.warning(f"**⚠️ Low ROI**\n\nEvery $1 discount → ${roi/100:.2f} revenue\n\n**Action:** Reduce discount depth")

    with col2:
        if coupon_pct > 70:
            st.warning(f"**⚠️ Over-Reliance on Discounts**\n\n{coupon_pct:.1f}% of revenue uses coupons\n\n**Risk:** Brand devaluation\n\n**Action:** Reduce frequency, build value")
        else:
            st.success(f"**✅ Balanced Strategy**\n\n{coupon_pct:.1f}% of revenue uses coupons\n\nGood mix of full-price and discounted sales")

    with col3:
        if not coupon_summary.empty:
            best_coup = coupon_summary.iloc[0]
            st.info(f"**🏆 Top Coupon**\n\n**{best_coup['discount_coupon_code']}**\n- Used: {best_coup['usage_count']:,.0f}×\n- Revenue: ${best_coup['total_revenue']:,.0f}\n- Avg discount: {best_coup['discount_percentage']:.1f}%\n\nReplicate this structure")

# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    data = load_data()
    if data is None:
        st.stop()

    filters = render_sidebar(data)

    st.sidebar.markdown("---")
    st.sidebar.title("📑 Navigation")

    page = st.sidebar.radio(
        "Select Page",
        [
            "📊 Executive Summary",
            "🔄 Conversion Funnel",
            "📦 Product Performance",
            "👥 Customer Segmentation",
            "📣 Marketing Attribution",
            "📄 Page Engagement & UX",
            "💰 Promotions & Discounts"
        ]
    )

    if page == "📊 Executive Summary":
        page_executive_summary(data, filters)
    elif page == "🔄 Conversion Funnel":
        page_conversion_funnel(data, filters)
    elif page == "📦 Product Performance":
        page_product_performance(data, filters)
    elif page == "👥 Customer Segmentation":
        page_customer_segmentation(data, filters)
    elif page == "📣 Marketing Attribution":
        page_marketing_attribution(data, filters)
    elif page == "📄 Page Engagement & UX":
        page_engagement_ux(data, filters)
    elif page == "💰 Promotions & Discounts":
        page_promotions(data, filters)

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
    📊 E-Commerce Analytics Dashboard<br>
    Built with Streamlit<br>
    Last updated: 2026-02-18
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()