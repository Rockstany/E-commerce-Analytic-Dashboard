"""
E-COMMERCE ANALYTICS DASHBOARD - MAIN APP
==========================================
Homepage with key business overview metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# PAGE CONFIG
st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CUSTOM CSS
st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    div[data-testid="stMetricValue"] {font-size: 28px; font-weight: 600;}
    h1 {color: #1f77b4; font-weight: 700; padding-bottom: 10px; border-bottom: 3px solid #1f77b4;}
    h3 {color: #2c3e50; margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

# HELPER FUNCTIONS
@st.cache_data(ttl=3600)
def load_data(filename):
    """Load CSV with caching"""
    try:
        df = pd.read_csv(f'aggregated_data/{filename}')
        return df
    except FileNotFoundError:
        st.error(f"❌ File not found: aggregated_data/{filename}")
        return None

def format_number(num, prefix="", suffix=""):
    """Format large numbers"""
    if num >= 1_000_000:
        return f"{prefix}{num/1_000_000:.1f}M{suffix}"
    elif num >= 1_000:
        return f"{prefix}{num/1_000:.1f}K{suffix}"
    else:
        return f"{prefix}{num:.0f}{suffix}"

def calculate_change(current, previous):
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

# SIDEBAR
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='color: #1f77b4; border: none;'>🛍️</h1>
            <h2 style='color: #2c3e50; margin: 0;'>Analytics</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.success("✅ Data loaded")
    st.caption(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# MAIN
st.title("🛍️ E-commerce Analytics Dashboard")
st.markdown("### Business Overview")

daily_metrics = load_data('daily_business_metrics.csv')

if daily_metrics is not None:
    daily_metrics['date'] = pd.to_datetime(daily_metrics['date'])
    
    # DATE FILTER
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=daily_metrics['date'].max() - timedelta(days=30),
            min_value=daily_metrics['date'].min().date(),
            max_value=daily_metrics['date'].max().date()
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=daily_metrics['date'].max().date(),
            min_value=daily_metrics['date'].min().date(),
            max_value=daily_metrics['date'].max().date()
        )
    
    # Filter
    mask = (daily_metrics['date'].dt.date >= start_date) & \
           (daily_metrics['date'].dt.date <= end_date)
    filtered_data = daily_metrics[mask].copy()
    
    # KEY METRICS
    st.markdown("---")
    st.markdown("### 💰 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Revenue", f"${filtered_data['total_revenue'].sum():,.0f}")
    
    with col2:
        st.metric("Orders", f"{filtered_data['total_orders'].sum():,.0f}")
    
    with col3:
        st.metric("Conversion", f"{filtered_data['conversion_rate'].mean():.2f}%")
    
    with col4:
        st.metric("AOV", f"${filtered_data['avg_order_value'].mean():.2f}")
    
    # CHART
    st.markdown("---")
    fig = px.line(filtered_data, x='date', y='total_revenue', title='Revenue Trend')
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>Built with Streamlit</p></div>", unsafe_allow_html=True)
