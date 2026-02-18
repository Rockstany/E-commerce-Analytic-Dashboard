"""
E-COMMERCE ANALYTICS DASHBOARD
Built with Streamlit

HOW TO RUN:
streamlit run dashboard.py

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

# Custom CSS for better styling
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
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# DATA LOADING FUNCTIONS
# ==============================================================================

@st.cache_data
def load_data():
    """
    Loads all aggregated CSV files with error handling
    
    Returns:
        dict: Dictionary containing all DataFrames
    """
    data = {}
    
    try:
        # Load all aggregated tables
        data['daily_metrics'] = pd.read_csv('aggregated_data/daily_business_metrics.csv')
        data['daily_metrics']['date'] = pd.to_datetime(data['daily_metrics']['date'])
        
        data['session_attribution'] = pd.read_csv('aggregated_data/session_attribution.csv')
        data['session_attribution']['date'] = pd.to_datetime(data['session_attribution']['date'])
        
        data['session_funnel'] = pd.read_csv('aggregated_data/session_funnel.csv')
        data['session_funnel']['date'] = pd.to_datetime(data['session_funnel']['date'])
        
        data['product_performance'] = pd.read_csv('aggregated_data/product_performance_daily.csv')
        data['product_performance']['date'] = pd.to_datetime(data['product_performance']['date'])
        
        data['user_lifetime'] = pd.read_csv('aggregated_data/user_lifetime_metrics.csv')
        data['user_lifetime']['first_order_date'] = pd.to_datetime(data['user_lifetime']['first_order_date'])
        data['user_lifetime']['last_order_date'] = pd.to_datetime(data['user_lifetime']['last_order_date'])
        
        data['page_engagement'] = pd.read_csv('aggregated_data/page_engagement_metrics.csv')
        data['page_engagement']['date'] = pd.to_datetime(data['page_engagement']['date'])
        
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
    """Format numbers with K, M, B suffixes"""
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
    """Calculate percentage change"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def create_metric_card(label, value, change=None, prefix='', suffix=''):
    """Create styled metric card"""
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
    """Render sidebar with global filters"""
    st.sidebar.title("🎛️ Filters")
    
    # Date range filter
    st.sidebar.subheader("📅 Date Range")
    
    # Get min and max dates from daily metrics
    min_date = data['daily_metrics']['date'].min().date()
    max_date = data['daily_metrics']['date'].max().date()
    
    # Default to last 30 days
    default_start = max_date - timedelta(days=30)
    
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0]
    
    # Quick date filters
    st.sidebar.markdown("**Quick Filters:**")
    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("Last 7 Days"):
        start_date = max_date - timedelta(days=7)
        end_date = max_date
    
    if col2.button("Last 30 Days"):
        start_date = max_date - timedelta(days=30)
        end_date = max_date
    
    if col1.button("Last 90 Days"):
        start_date = max_date - timedelta(days=90)
        end_date = max_date
    
    if col2.button("All Time"):
        start_date = min_date
        end_date = max_date
    
    st.sidebar.markdown("---")
    
    # Additional filters
    st.sidebar.subheader("🔍 Additional Filters")
    
    # Product filter (for product-specific pages)
    products = sorted(data['product_performance']['product_name'].unique())
    selected_products = st.sidebar.multiselect(
        "Filter by Products",
        options=products,
        default=None,
        help="Leave empty to show all products"
    )
    
    # UTM Source filter (for marketing pages)
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
        'start_date': pd.Timestamp(start_date),
        'end_date': pd.Timestamp(end_date),
        'products': selected_products if selected_products else None,
        'sources': selected_sources if selected_sources else None
    }

# ==============================================================================
# PAGE 1: EXECUTIVE SUMMARY
# ==============================================================================

def page_executive_summary(data, filters):
    """Executive Summary Dashboard"""
    
    st.markdown('<div class="main-header">📊 Executive Summary</div>', unsafe_allow_html=True)
    st.markdown("### High-level business metrics at a glance")
    
    # Filter data by date range
    df = data['daily_metrics'][
        (data['daily_metrics']['date'] >= filters['start_date']) &
        (data['daily_metrics']['date'] <= filters['end_date'])
    ].copy()
    
    if df.empty:
        st.warning("No data available for selected date range")
        return
    
    # Calculate current period metrics
    total_revenue = df['total_revenue'].sum()
    total_orders = df['total_orders'].sum()
    total_sessions = df['total_sessions'].sum()
    avg_conversion_rate = (total_orders / total_sessions * 100) if total_sessions > 0 else 0
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Calculate previous period for comparison
    period_days = (filters['end_date'] - filters['start_date']).days
    prev_start = filters['start_date'] - timedelta(days=period_days)
    prev_end = filters['start_date'] - timedelta(days=1)
    
    df_prev = data['daily_metrics'][
        (data['daily_metrics']['date'] >= prev_start) &
        (data['daily_metrics']['date'] <= prev_end)
    ]
    
    if not df_prev.empty:
        prev_revenue = df_prev['total_revenue'].sum()
        prev_orders = df_prev['total_orders'].sum()
        prev_sessions = df_prev['total_sessions'].sum()
        prev_conversion = (prev_orders / prev_sessions * 100) if prev_sessions > 0 else 0
        prev_aov = prev_revenue / prev_orders if prev_orders > 0 else 0
        
        revenue_change = calculate_change(total_revenue, prev_revenue)
        orders_change = calculate_change(total_orders, prev_orders)
        conversion_change = calculate_change(avg_conversion_rate, prev_conversion)
        aov_change = calculate_change(avg_order_value, prev_aov)
    else:
        revenue_change = orders_change = conversion_change = aov_change = None
    
    # TOP METRICS ROW
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Total Revenue",
            value=f"${total_revenue:,.0f}",
            delta=f"{revenue_change:+.1f}%" if revenue_change else None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="🛍️ Total Orders",
            value=f"{total_orders:,}",
            delta=f"{orders_change:+.1f}%" if orders_change else None,
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="📈 Conversion Rate",
            value=f"{avg_conversion_rate:.2f}%",
            delta=f"{conversion_change:+.1f}%" if conversion_change else None,
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            label="💵 Avg Order Value",
            value=f"${avg_order_value:.2f}",
            delta=f"{aov_change:+.1f}%" if aov_change else None,
            delta_color="normal"
        )
    
    st.markdown("---")
    
    # REVENUE TREND CHART
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Daily Revenue Trend")
        
        fig = px.line(
            df,
            x='date',
            y='total_revenue',
            title='Revenue Over Time',
            labels={'total_revenue': 'Revenue ($)', 'date': 'Date'}
        )
        
        fig.update_traces(line_color='#1f77b4', line_width=2)
        fig.update_layout(
            hovermode='x unified',
            plot_bgcolor='white',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("👥 New vs Repeat Customers")
        
        if 'new_customers' in df.columns and 'repeat_customers' in df.columns:
            new_customers = df['new_customers'].sum()
            repeat_customers = df['repeat_customers'].sum()
            
            fig = go.Figure(data=[go.Pie(
                labels=['New Customers', 'Repeat Customers'],
                values=[new_customers, repeat_customers],
                hole=0.4,
                marker_colors=['#ff7f0e', '#2ca02c']
            )])
            
            fig.update_layout(
                title='Customer Type Distribution',
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Stats below pie chart
            st.markdown(f"""
            **Total Customers**: {new_customers + repeat_customers:,}
            - 🆕 New: {new_customers:,} ({new_customers/(new_customers+repeat_customers)*100:.1f}%)
            - 🔄 Repeat: {repeat_customers:,} ({repeat_customers/(new_customers+repeat_customers)*100:.1f}%)
            """)
        else:
            st.info("New/Repeat customer data not available")
    
    # CONVERSION & AOV TRENDS
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Conversion Rate Trend")
        
        fig = px.line(
            df,
            x='date',
            y='conversion_rate',
            title='Conversion Rate Over Time',
            labels={'conversion_rate': 'Conversion Rate (%)', 'date': 'Date'}
        )
        
        # Add benchmark line at 3%
        fig.add_hline(
            y=3.0,
            line_dash="dash",
            line_color="red",
            annotation_text="Industry Avg (3%)",
            annotation_position="right"
        )
        
        fig.update_traces(line_color='#2ca02c', line_width=2)
        fig.update_layout(height=350, plot_bgcolor='white')
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💳 Average Order Value Trend")
        
        fig = px.line(
            df,
            x='date',
            y='avg_order_value',
            title='AOV Over Time',
            labels={'avg_order_value': 'AOV ($)', 'date': 'Date'}
        )
        
        fig.update_traces(line_color='#d62728', line_width=2)
        fig.update_layout(height=350, plot_bgcolor='white')
        
        st.plotly_chart(fig, use_container_width=True)
    
    # KEY INSIGHTS
    st.markdown("---")
    st.subheader("💡 Key Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Best performing day
        best_day = df.loc[df['total_revenue'].idxmax()]
        st.info(f"""
        **🏆 Best Revenue Day**  
        {best_day['date'].strftime('%Y-%m-%d')}  
        Revenue: ${best_day['total_revenue']:,.0f}
        """)
    
    with col2:
        # Average daily revenue
        avg_daily_revenue = df['total_revenue'].mean()
        st.info(f"""
        **📊 Avg Daily Revenue**  
        ${avg_daily_revenue:,.0f}  
        Based on {len(df)} days
        """)
    
    with col3:
        # Total sessions
        st.info(f"""
        **👁️ Total Sessions**  
        {total_sessions:,}  
        Avg: {total_sessions/len(df):,.0f}/day
        """)

# ==============================================================================
# PAGE 2: CONVERSION FUNNEL
# ==============================================================================

def page_conversion_funnel(data, filters):
    """Conversion Funnel Analysis"""
    
    st.markdown('<div class="main-header">🔄 Conversion Funnel Analysis</div>', unsafe_allow_html=True)
    st.markdown("### Track user journey from visit to purchase")
    
    # Filter data
    df = data['session_funnel'][
        (data['session_funnel']['date'] >= filters['start_date']) &
        (data['session_funnel']['date'] <= filters['end_date'])
    ].copy()
    
    if df.empty:
        st.warning("No funnel data available for selected date range")
        return
    
    # Calculate funnel metrics
    total_sessions = len(df)
    product_views = df['had_product_view'].sum()
    cart_adds = df['had_add_to_cart'].sum()
    purchases = df['had_order'].sum()
    
    # Calculate conversion rates
    product_view_rate = (product_views / total_sessions * 100) if total_sessions > 0 else 0
    cart_rate = (cart_adds / total_sessions * 100) if total_sessions > 0 else 0
    purchase_rate = (purchases / total_sessions * 100) if total_sessions > 0 else 0
    cart_to_purchase_rate = (purchases / cart_adds * 100) if cart_adds > 0 else 0

    # Calculate drop-off percentages
    drop_off_1 = 100 - product_view_rate
    drop_off_2 = product_view_rate - cart_rate
    drop_off_3 = cart_rate - purchase_rate

    
    # FUNNEL VISUALIZATION
    st.markdown("---")
    st.subheader("📊 Funnel Overview")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create funnel chart
        funnel_data = pd.DataFrame({
            'Stage': ['Sessions', 'Product Views', 'Add to Cart', 'Purchase'],
            'Count': [total_sessions, product_views, cart_adds, purchases],
            'Percentage': [100, product_view_rate, cart_rate, purchase_rate]
        })
        
        fig = go.Figure(go.Funnel(
            y=funnel_data['Stage'],
            x=funnel_data['Count'],
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(
                color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
            )
        ))
        
        fig.update_layout(
            title='Conversion Funnel',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Funnel Metrics")
        
        st.metric(
            "Sessions",
            f"{total_sessions:,}",
            "100%"
        )
        
    
    # TIME METRICS
    st.markdown("---")
    st.subheader("⏱️ Time Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Average time to cart
        avg_time_to_cart = df[df['time_to_cart_minutes'].notna()]['time_to_cart_minutes'].mean()
        
        st.markdown(f"""
        **⏰ Average Time to Add to Cart**  
        `{avg_time_to_cart:.1f}` minutes
        
        *How long users take from landing on site to adding first item to cart*
        """)
        
        # Distribution
        fig = px.histogram(
            df[df['time_to_cart_minutes'].notna()],
            x='time_to_cart_minutes',
            nbins=30,
            title='Distribution of Time to Cart',
            labels={'time_to_cart_minutes': 'Minutes', 'count': 'Sessions'}
        )
        
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Average time to purchase
        avg_time_to_purchase = df[df['time_to_order_minutes'].notna()]['time_to_order_minutes'].mean()
        
        st.markdown(f"""
        **⏰ Average Time to Purchase**  
        `{avg_time_to_purchase:.1f}` minutes
        
        *How long users take from landing on site to completing purchase*
        """)
        
        # Distribution
        fig = px.histogram(
            df[df['time_to_order_minutes'].notna()],
            x='time_to_order_minutes',
            nbins=30,
            title='Distribution of Time to Purchase',
            labels={'time_to_order_minutes': 'Minutes', 'count': 'Sessions'}
        )
        
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # FUNNEL BY DEVICE TYPE
    st.markdown("---")
    st.subheader("📱 Funnel by Device Type")
    
    # Join with session attribution to get device type
    df_with_device = df.merge(
        data['session_attribution'][['session_id', 'device_type']],
        on='session_id',
        how='left'
    )
    
    if 'device_type' in df_with_device.columns:
        device_funnel = df_with_device.groupby('device_type').agg({
            'session_id': 'count',
            'had_product_view': 'sum',
            'had_add_to_cart': 'sum',
            'had_order': 'sum'
        }).reset_index()
        
        device_funnel.columns = ['Device', 'Sessions', 'Product Views', 'Cart Adds', 'Purchases']
        
        # Calculate rates
        device_funnel['Product View Rate'] = (device_funnel['Product Views'] / device_funnel['Sessions'] * 100).round(2)
        device_funnel['Cart Rate'] = (device_funnel['Cart Adds'] / device_funnel['Sessions'] * 100).round(2)
        device_funnel['Conversion Rate'] = (device_funnel['Purchases'] / device_funnel['Sessions'] * 100).round(2)
        
        # Bar chart comparing conversion rates
        fig = px.bar(
            device_funnel,
            x='Device',
            y=['Product View Rate', 'Cart Rate', 'Conversion Rate'],
            title='Conversion Rates by Device Type',
            barmode='group',
            labels={'value': 'Rate (%)', 'variable': 'Funnel Stage'}
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        st.dataframe(
            device_funnel.style.format({
                'Sessions': '{:,}',
                'Product Views': '{:,}',
                'Cart Adds': '{:,}',
                'Purchases': '{:,}',
                'Product View Rate': '{:.2f}%',
                'Cart Rate': '{:.2f}%',
                'Conversion Rate': '{:.2f}%'
            }),
            use_container_width=True
        )
    else:
        st.info("Device type data not available")
    
    # INSIGHTS
    st.markdown("---")
    st.subheader("💡 Optimization Recommendations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if product_view_rate < 50:
            st.error(f"""
            **⚠️ Low Product View Rate ({product_view_rate:.1f}%)**
            
            **Possible Issues:**
            - Poor navigation
            - Unclear value proposition
            - Slow page load times
            
            **Recommendations:**
            - Improve homepage clarity
            - Add prominent product categories
            - Optimize site speed
            """)
        else:
            st.success(f"""
            **✅ Good Product View Rate ({product_view_rate:.1f}%)**
            
            Users are successfully finding products
            """)
    
    with col2:
        if cart_to_purchase_rate < 30:
            st.error(f"""
            **⚠️ Low Cart→Purchase Rate ({cart_to_purchase_rate:.1f}%)**
            
            **Possible Issues:**
            - Checkout friction
            - Unexpected shipping costs
            - Payment issues
            - Trust concerns
            
            **Recommendations:**
            - Simplify checkout process
            - Show shipping costs upfront
            - Add trust badges
            - Enable guest checkout
            """)
        else:
            st.success(f"""
            **✅ Good Cart→Purchase Rate ({cart_to_purchase_rate:.1f}%)**
            
            Checkout process is working well
            """)
    
    with col3:
        if avg_time_to_purchase > 30:
            st.warning(f"""
            **⏰ Long Purchase Journey ({avg_time_to_purchase:.0f} min)**
            
            **Possible Reasons:**
            - High consideration products
            - Complex product catalog
            - Users comparing options
            
            **Recommendations:**
            - Add comparison tools
            - Improve product recommendations
            - Add customer reviews
            """)
        else:
            st.success(f"""
            **⚡ Quick Purchase Journey ({avg_time_to_purchase:.0f} min)**
            
            Users make fast decisions
            """)

# ==============================================================================
# PAGE 3: PRODUCT PERFORMANCE
# ==============================================================================

def page_product_performance(data, filters):
    """Product Performance Dashboard"""
    
    st.markdown('<div class="main-header">📦 Product Performance</div>', unsafe_allow_html=True)
    st.markdown("### Analyze product sales and identify opportunities")
    
    # Filter data
    df = data['product_performance'][
        (data['product_performance']['date'] >= filters['start_date']) &
        (data['product_performance']['date'] <= filters['end_date'])
    ].copy()
    
    if filters['products']:
        df = df[df['product_name'].isin(filters['products'])]
    
    if df.empty:
        st.warning("No product data available for selected filters")
        return
    
    # Aggregate by product
    product_summary = df.groupby('product_name').agg({
        'total_revenue': 'sum',
        'total_quantity_sold': 'sum',
        'times_purchased': 'sum',
        'times_added_to_cart': 'sum',
        'cart_to_purchase_rate': 'mean'
    }).reset_index()
    
    product_summary = product_summary.sort_values('total_revenue', ascending=False)
    
    # TOP METRICS
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_product_revenue = product_summary['total_revenue'].sum()
        st.metric("💰 Total Revenue", f"${total_product_revenue:,.0f}")
    
    with col2:
        total_quantity = product_summary['total_quantity_sold'].sum()
        st.metric("📦 Units Sold", f"{total_quantity:,.0f}")
    
    with col3:
        unique_products = len(product_summary)
        st.metric("🏷️ Active Products", f"{unique_products:,}")
    
    with col4:
        avg_cart_to_purchase = product_summary['cart_to_purchase_rate'].mean()
        st.metric("🎯 Avg Cart→Purchase", f"{avg_cart_to_purchase:.1f}%")
    
    # TOP PRODUCTS
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Products by Revenue")
        
        top_10_revenue = product_summary.head(10)
        
        fig = px.bar(
            top_10_revenue,
            y='product_name',
            x='total_revenue',
            orientation='h',
            title='Top Products by Revenue',
            labels={'total_revenue': 'Revenue ($)', 'product_name': 'Product'},
            color='total_revenue',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Top 10 Products by Units Sold")
        
        top_10_qty = product_summary.nlargest(10, 'total_quantity_sold')
        
        fig = px.bar(
            top_10_qty,
            y='product_name',
            x='total_quantity_sold',
            orientation='h',
            title='Top Products by Quantity',
            labels={'total_quantity_sold': 'Units Sold', 'product_name': 'Product'},
            color='total_quantity_sold',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # CART TO PURCHASE RATE ANALYSIS
    st.markdown("---")
    st.subheader("🎯 Cart-to-Purchase Conversion by Product")
    
    # Filter products with enough data
    products_with_data = product_summary[product_summary['times_added_to_cart'] >= 10].copy()
    products_with_data = products_with_data.sort_values('cart_to_purchase_rate', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌟 Best Performing Products (High Conversion)**")
        top_performers = products_with_data.head(10)
        
        fig = px.bar(
            top_performers,
            y='product_name',
            x='cart_to_purchase_rate',
            orientation='h',
            labels={'cart_to_purchase_rate': 'Conversion Rate (%)', 'product_name': 'Product'},
            color='cart_to_purchase_rate',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**⚠️ Underperforming Products (Low Conversion)**")
        bottom_performers = products_with_data.tail(10)
        
        fig = px.bar(
            bottom_performers,
            y='product_name',
            x='cart_to_purchase_rate',
            orientation='h',
            labels={'cart_to_purchase_rate': 'Conversion Rate (%)', 'product_name': 'Product'},
            color='cart_to_purchase_rate',
            color_continuous_scale='Reds_r'
        )
        
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # PRODUCT TREND ANALYSIS
    st.markdown("---")
    st.subheader("📈 Product Trend Analysis")
    
    # Select product for trend
    selected_product = st.selectbox(
        "Select a product to view trend",
        options=sorted(df['product_name'].unique()),
        index=0
    )
    
    if selected_product:
        product_trend = df[df['product_name'] == selected_product].sort_values('date')
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                product_trend,
                x='date',
                y='total_revenue',
                title=f'Revenue Trend: {selected_product}',
                labels={'total_revenue': 'Revenue ($)', 'date': 'Date'}
            )
            
            fig.update_traces(line_color='#1f77b4', line_width=2)
            fig.update_layout(height=350, plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                product_trend,
                x='date',
                y='total_quantity_sold',
                title=f'Units Sold Trend: {selected_product}',
                labels={'total_quantity_sold': 'Units', 'date': 'Date'}
            )
            
            fig.update_traces(line_color='#2ca02c', line_width=2)
            fig.update_layout(height=350, plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)
    
    # DETAILED TABLE
    st.markdown("---")
    st.subheader("📋 Detailed Product Performance Table")
    
    # Add calculated columns
    product_summary['avg_price'] = (product_summary['total_revenue'] / product_summary['total_quantity_sold']).round(2)
    
    # Display table with formatting
    st.dataframe(
        product_summary.style.format({
            'total_revenue': '${:,.2f}',
            'total_quantity_sold': '{:,.0f}',
            'times_purchased': '{:,.0f}',
            'times_added_to_cart': '{:,.0f}',
            'cart_to_purchase_rate': '{:.2f}%',
            'avg_price': '${:.2f}'
        }).background_gradient(subset=['total_revenue'], cmap='Blues'),
        use_container_width=True,
        height=400
    )
    
    # INSIGHTS
    st.markdown("---")
    st.subheader("💡 Product Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Revenue concentration
        top_10_revenue_pct = (top_10_revenue['total_revenue'].sum() / total_product_revenue * 100)
        
        st.info(f"""
        **📊 Revenue Concentration**
        
        Top 10 products generate **{top_10_revenue_pct:.1f}%** of total revenue
        
        {
            "⚠️ High concentration - diversify product mix" if top_10_revenue_pct > 70 
            else "✅ Healthy revenue distribution"
        }
        """)
    
    with col2:
        # Average conversion
        good_conversion = len(products_with_data[products_with_data['cart_to_purchase_rate'] > 50])
        poor_conversion = len(products_with_data[products_with_data['cart_to_purchase_rate'] < 30])
        
        st.info(f"""
        **🎯 Conversion Quality**
        
        - ✅ High conversion (>50%): **{good_conversion}** products
        - ⚠️ Low conversion (<30%): **{poor_conversion}** products
        
        Focus on improving low-conversion products
        """)
    
    with col3:
        # Best performer details
        best_product = product_summary.iloc[0]
        
        st.info(f"""
        **🏆 Star Product**
        
        **{best_product['product_name']}**
        
        - Revenue: ${best_product['total_revenue']:,.0f}
        - Units: {best_product['total_quantity_sold']:,.0f}
        - Conv: {best_product['cart_to_purchase_rate']:.1f}%
        """)

# ==============================================================================
# PAGE 4: CUSTOMER SEGMENTATION (RFM)
# ==============================================================================

def page_customer_segmentation(data, filters):
    """Customer Segmentation Dashboard"""
    
    st.markdown('<div class="main-header">👥 Customer Segmentation (RFM Analysis)</div>', unsafe_allow_html=True)
    st.markdown("### Understand customer value and behavior patterns")
    
    df = data['user_lifetime'].copy()
    
    # Convert to datetime for comparison
    df['last_order_date'] = pd.to_datetime(df['last_order_date'])
    
    # Filter by date if last order was in range
    df_filtered = df[
        (df['last_order_date'] >= filters['start_date']) &
        (df['last_order_date'] <= filters['end_date'])
    ] if filters else df
    
    # Use all data for lifetime metrics but show filtered stats
    total_customers = len(df)
    active_customers = len(df_filtered)
    
    # SUMMARY METRICS
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Customers", f"{total_customers:,}")
    
    with col2:
        avg_ltv = df['total_revenue'].mean()
        st.metric("💰 Avg Customer LTV", f"${avg_ltv:,.0f}")
    
    with col3:
        total_ltv = df['total_revenue'].sum()
        st.metric("💎 Total Customer Value", f"${total_ltv:,.0f}")
    
    with col4:
        avg_orders = df['total_orders'].mean()
        st.metric("🛍️ Avg Orders/Customer", f"{avg_orders:.1f}")
    
    # RFM SEGMENT DISTRIBUTION
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Customer Segment Distribution")
        
        segment_counts = df['rfm_segment'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        
        fig = px.pie(
            segment_counts,
            values='Count',
            names='Segment',
            title='Customer Segments',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 Revenue by Segment")
        
        segment_revenue = df.groupby('rfm_segment').agg({
            'total_revenue': 'sum',
            'user_id': 'count'
        }).reset_index()
        
        segment_revenue.columns = ['Segment', 'Revenue', 'Customers']
        segment_revenue = segment_revenue.sort_values('Revenue', ascending=False)
        
        fig = px.bar(
            segment_revenue,
            x='Segment',
            y='Revenue',
            title='Total Revenue by Segment',
            labels={'Revenue': 'Revenue ($)', 'Segment': 'Customer Segment'},
            color='Revenue',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # SEGMENT DETAILS
    st.markdown("---")
    st.subheader("📊 Segment Performance Details")
    
    segment_stats = df.groupby('rfm_segment').agg({
        'user_id': 'count',
        'total_revenue': ['sum', 'mean'],
        'total_orders': 'mean',
        'avg_order_value': 'mean',
        'days_since_last_order': 'mean'
    }).reset_index()
    
    segment_stats.columns = [
        'Segment',
        'Customers',
        'Total Revenue',
        'Avg LTV',
        'Avg Orders',
        'Avg AOV',
        'Avg Days Since Purchase'
    ]
    
    segment_stats = segment_stats.sort_values('Total Revenue', ascending=False)
    
    # Add percentage
    segment_stats['% of Customers'] = (segment_stats['Customers'] / total_customers * 100).round(1)
    segment_stats['% of Revenue'] = (segment_stats['Total Revenue'] / total_ltv * 100).round(1)
    
    st.dataframe(
        segment_stats.style.format({
            'Customers': '{:,}',
            'Total Revenue': '${:,.0f}',
            'Avg LTV': '${:,.0f}',
            'Avg Orders': '{:.1f}',
            'Avg AOV': '${:.2f}',
            'Avg Days Since Purchase': '{:.0f}',
            '% of Customers': '{:.1f}%',
            '% of Revenue': '{:.1f}%'
        }).background_gradient(subset=['Total Revenue'], cmap='Greens'),
        use_container_width=True
    )
    
    # LTV DISTRIBUTION
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💎 Customer Lifetime Value Distribution")
        
        # Create LTV buckets
        ltv_buckets = pd.cut(
            df['total_revenue'],
            bins=[0, 50, 200, 500, 1000, float('inf')],
            labels=['$0-50', '$50-200', '$200-500', '$500-1000', '$1000+']
        )
        
        ltv_dist = ltv_buckets.value_counts().sort_index().reset_index()
        ltv_dist.columns = ['LTV Range', 'Customers']
        
        fig = px.bar(
            ltv_dist,
            x='LTV Range',
            y='Customers',
            title='Customer Distribution by LTV',
            labels={'Customers': 'Number of Customers', 'LTV Range': 'LTV Bucket'},
            color='Customers',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 RFM Score Distribution")
        
        # Breakdown of R, F, M scores
        rfm_breakdown = pd.DataFrame({
            'Recency Score': df['rfm_recency_score'].value_counts().sort_index(),
            'Frequency Score': df['rfm_frequency_score'].value_counts().sort_index(),
            'Monetary Score': df['rfm_monetary_score'].value_counts().sort_index()
        }).fillna(0).astype(int)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(name='Recency', x=rfm_breakdown.index, y=rfm_breakdown['Recency Score']))
        fig.add_trace(go.Bar(name='Frequency', x=rfm_breakdown.index, y=rfm_breakdown['Frequency Score']))
        fig.add_trace(go.Bar(name='Monetary', x=rfm_breakdown.index, y=rfm_breakdown['Monetary Score']))
        
        fig.update_layout(
            title='RFM Score Distribution (1=Worst, 5=Best)',
            barmode='group',
            xaxis_title='Score',
            yaxis_title='Number of Customers',
            height=350,
            xaxis={'tickmode': 'linear', 'tick0': 1, 'dtick': 1}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # CUSTOMER RETENTION
    st.markdown("---")
    st.subheader("🔄 Customer Retention Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'has_purchase_last_year' in df.columns:
            retention_data = df['has_purchase_last_year'].value_counts().reset_index()
            retention_data.columns = ['Status', 'Count']
            retention_data['Status'] = retention_data['Status'].map({1: 'Purchased Last Year', 0: 'No Purchase Last Year'})
            
            fig = px.pie(
                retention_data,
                values='Count',
                names='Status',
                title='Customer Retention (Year-over-Year)',
                hole=0.4,
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            retention_rate = (retention_data[retention_data['Status'] == 'Purchased Last Year']['Count'].sum() / 
                            total_customers * 100)
            
            st.markdown(f"""
            **Retention Rate**: {retention_rate:.1f}%
            
            {
                "✅ Strong retention!" if retention_rate > 40 
                else "⚠️ Focus on retention campaigns" if retention_rate > 20
                else "🚨 Critical retention issue"
            }
            """)
    
    with col2:
        # Days since last order distribution
        fig = px.histogram(
            df,
            x='days_since_last_order',
            nbins=30,
            title='Recency Distribution (Days Since Last Order)',
            labels={'days_since_last_order': 'Days', 'count': 'Customers'},
            color_discrete_sequence=['#3498db']
        )
        
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Add recency insights
        at_risk = len(df[df['days_since_last_order'] > 90])
        lost = len(df[df['days_since_last_order'] > 365])
        
        st.markdown(f"""
        **Recency Insights:**
        - At Risk (>90 days): {at_risk:,} customers ({at_risk/total_customers*100:.1f}%)
        - Lost (>365 days): {lost:,} customers ({lost/total_customers*100:.1f}%)
        """)
    
    # ACTION RECOMMENDATIONS
    st.markdown("---")
    st.subheader("🎯 Recommended Actions by Segment")
    
    recommendations = {
        'Champion': {
            'emoji': '🏆',
            'description': 'Your best customers - recent, frequent, high-value',
            'actions': [
                'Enroll in VIP loyalty program',
                'Offer early access to new products',
                'Request referrals and reviews',
                'Send exclusive discount codes'
            ]
        },
        'Loyal Customer': {
            'emoji': '💎',
            'description': 'Regular buyers with consistent purchase patterns',
            'actions': [
                'Implement loyalty rewards program',
                'Send personalized product recommendations',
                'Offer subscription or auto-replenish options',
                'Request testimonials'
            ]
        },
        'Potential Loyalist': {
            'emoji': '🌱',
            'description': 'Recent buyers showing promise',
            'actions': [
                'Send nurture email sequences',
                'Offer second-purchase incentive',
                'Provide educational content',
                'Cross-sell complementary products'
            ]
        },
        'At Risk': {
            'emoji': '⚠️',
            'description': 'Previously active but haven\'t bought recently',
            'actions': [
                'Launch win-back email campaign',
                'Survey why they stopped buying',
                'Offer "We miss you" discount',
                'Highlight new products/features'
            ]
        },
        'Lost': {
            'emoji': '😔',
            'description': 'Inactive for >365 days',
            'actions': [
                'Send aggressive re-engagement discount (20-30%)',
                'Test different messaging angles',
                'Consider removing from active lists to save costs',
                'Last-chance campaign before permanent opt-out'
            ]
        },
        'New Customer': {
            'emoji': '🎉',
            'description': 'Just made first 1-2 purchases',
            'actions': [
                'Welcome series with brand story',
                'Onboarding email sequence',
                'First repeat purchase incentive',
                'Request feedback on initial experience'
            ]
        }
    }
    
    # Display recommendations in expandable sections
    for segment, info in recommendations.items():
        if segment in df['rfm_segment'].values:
            with st.expander(f"{info['emoji']} {segment} - {info['description']}"):
                customer_count = len(df[df['rfm_segment'] == segment])
                revenue = df[df['rfm_segment'] == segment]['total_revenue'].sum()
                
                st.markdown(f"**Customers**: {customer_count:,} ({customer_count/total_customers*100:.1f}%)")
                st.markdown(f"**Total Revenue**: ${revenue:,.0f}")
                st.markdown("**Recommended Actions:**")
                for action in info['actions']:
                    st.markdown(f"- {action}")

# ==============================================================================
# PAGE 5: MARKETING ATTRIBUTION
# ==============================================================================

def page_marketing_attribution(data, filters):
    """Marketing Attribution Dashboard"""
    
    st.markdown('<div class="main-header">📣 Marketing Attribution</div>', unsafe_allow_html=True)
    st.markdown("### Measure ROI of marketing channels and campaigns")
    
    # Filter data
    df = data['session_attribution'][
        (data['session_attribution']['date'] >= filters['start_date']) &
        (data['session_attribution']['date'] <= filters['end_date'])
    ].copy()
    
    if filters['sources']:
        df = df[df['utm_source'].isin(filters['sources'])]
    
    if df.empty:
        st.warning("No attribution data available for selected filters")
        return
    
    # Calculate metrics by source
    source_metrics = df.groupby('utm_source').agg({
        'session_id': 'count',
        'converted': 'sum',
        'revenue': 'sum'
    }).reset_index()
    
    source_metrics.columns = ['Source', 'Sessions', 'Conversions', 'Revenue']
    source_metrics['Conversion Rate'] = (source_metrics['Conversions'] / source_metrics['Sessions'] * 100).round(2)
    source_metrics['Revenue per Session'] = (source_metrics['Revenue'] / source_metrics['Sessions']).round(2)
    source_metrics = source_metrics.sort_values('Revenue', ascending=False)
    
    # TOP METRICS
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sessions = source_metrics['Sessions'].sum()
        st.metric("🔗 Total Sessions", f"{total_sessions:,}")
    
    with col2:
        total_conversions = source_metrics['Conversions'].sum()
        st.metric("✅ Total Conversions", f"{total_conversions:,}")
    
    with col3:
        total_revenue = source_metrics['Revenue'].sum()
        st.metric("💰 Attributed Revenue", f"${total_revenue:,.0f}")
    
    with col4:
        overall_conv_rate = (total_conversions / total_sessions * 100) if total_sessions > 0 else 0
        st.metric("📈 Overall Conv Rate", f"{overall_conv_rate:.2f}%")
    
    # CHANNEL PERFORMANCE
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Revenue by Channel")
        
        fig = px.bar(
            source_metrics.head(10),
            x='Source',
            y='Revenue',
            title='Top 10 Channels by Revenue',
            labels={'Revenue': 'Revenue ($)', 'Source': 'Traffic Source'},
            color='Revenue',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Conversion Rate by Channel")
        
        # Only show channels with >100 sessions for fair comparison
        source_metrics_filtered = source_metrics[source_metrics['Sessions'] >= 100]
        
        fig = px.bar(
            source_metrics_filtered.sort_values('Conversion Rate', ascending=False).head(10),
            x='Source',
            y='Conversion Rate',
            title='Top 10 Channels by Conversion Rate (min 100 sessions)',
            labels={'Conversion Rate': 'Conversion Rate (%)', 'Source': 'Traffic Source'},
            color='Conversion Rate',
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # TRAFFIC SOURCES PIE CHART
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌐 Traffic Distribution")
        
        fig = px.pie(
            source_metrics.head(8),
            values='Sessions',
            names='Source',
            title='Session Distribution by Source',
            hole=0.4
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💸 Revenue Distribution")
        
        fig = px.pie(
            source_metrics.head(8),
            values='Revenue',
            names='Source',
            title='Revenue Distribution by Source',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # CAMPAIGN PERFORMANCE
    st.markdown("---")
    st.subheader("📢 Campaign Performance")
    
    if 'utm_campaign' in df.columns:
        campaign_metrics = df[df['utm_campaign'] != 'direct'].groupby('utm_campaign').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        campaign_metrics.columns = ['Campaign', 'Sessions', 'Conversions', 'Revenue']
        campaign_metrics['Conversion Rate'] = (campaign_metrics['Conversions'] / campaign_metrics['Sessions'] * 100).round(2)
        campaign_metrics = campaign_metrics.sort_values('Revenue', ascending=False).head(15)
        
        fig = px.bar(
            campaign_metrics,
            x='Campaign',
            y='Revenue',
            title='Top 15 Campaigns by Revenue',
            labels={'Revenue': 'Revenue ($)', 'Campaign': 'Campaign Name'},
            color='Conversion Rate',
            color_continuous_scale='RdYlGn',
            hover_data=['Sessions', 'Conversions', 'Conversion Rate']
        )
        
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    # TRAFFIC TREND OVER TIME
    st.markdown("---")
    st.subheader("📊 Traffic Trend by Source")
    
    # Daily sessions by source
    daily_source = df.groupby(['date', 'utm_source']).agg({
        'session_id': 'count'
    }).reset_index()
    
    daily_source.columns = ['Date', 'Source', 'Sessions']
    
    # Only show top 5 sources for clarity
    top_5_sources = source_metrics.head(5)['Source'].tolist()
    daily_source_filtered = daily_source[daily_source['Source'].isin(top_5_sources)]
    
    fig = px.line(
        daily_source_filtered,
        x='Date',
        y='Sessions',
        color='Source',
        title='Daily Sessions by Top 5 Traffic Sources',
        labels={'Sessions': 'Number of Sessions', 'Date': 'Date'}
    )
    
    fig.update_layout(height=400, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)
    
    # DETAILED CHANNEL TABLE
    st.markdown("---")
    st.subheader("📋 Detailed Channel Performance")
    
    st.dataframe(
        source_metrics.style.format({
            'Sessions': '{:,}',
            'Conversions': '{:,}',
            'Revenue': '${:,.2f}',
            'Conversion Rate': '{:.2f}%',
            'Revenue per Session': '${:.2f}'
        }).background_gradient(subset=['Revenue'], cmap='Greens'),
        use_container_width=True,
        height=400
    )
    
    # INSIGHTS & RECOMMENDATIONS
    st.markdown("---")
    st.subheader("💡 Marketing Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Best ROI channel
        best_channel = source_metrics.iloc[0]
        
        st.success(f"""
        **🏆 Top Performing Channel**
        
        **{best_channel['Source']}**
        
        - Revenue: ${best_channel['Revenue']:,.0f}
        - Sessions: {best_channel['Sessions']:,}
        - Conv Rate: {best_channel['Conversion Rate']:.2f}%
        
        **Action**: Increase budget allocation
        """)
    
    with col2:
        # High traffic, low conversion
        high_traffic_low_conv = source_metrics[
            (source_metrics['Sessions'] > source_metrics['Sessions'].median()) &
            (source_metrics['Conversion Rate'] < overall_conv_rate)
        ]
        
        if not high_traffic_low_conv.empty:
            problem_channel = high_traffic_low_conv.iloc[0]
            
            st.warning(f"""
            **⚠️ Needs Optimization**
            
            **{problem_channel['Source']}**
            
            - High traffic: {problem_channel['Sessions']:,} sessions
            - Low conversion: {problem_channel['Conversion Rate']:.2f}%
            
            **Action**: Review targeting, landing pages
            """)
        else:
            st.info("All channels performing well!")
    
    with col3:
        # Direct traffic analysis
        direct_traffic = source_metrics[source_metrics['Source'] == 'direct']
        
        if not direct_traffic.empty:
            direct = direct_traffic.iloc[0]
            direct_pct = (direct['Sessions'] / total_sessions * 100)
            
            st.info(f"""
            **🔗 Direct Traffic**
            
            {direct_pct:.1f}% of all sessions
            
            - Sessions: {direct['Sessions']:,}
            - Revenue: ${direct['Revenue']:,.0f}
            
            {
                "✅ Good brand recognition" if direct_pct > 30
                else "Consider brand awareness campaigns"
            }
            """)

# ==============================================================================
# PAGE 6: PAGE ENGAGEMENT & UX
# ==============================================================================

def page_engagement_ux(data, filters):
    """Page Engagement & UX Dashboard"""
    
    st.markdown('<div class="main-header">📄 Page Engagement & UX</div>', unsafe_allow_html=True)
    st.markdown("### Optimize website content and user experience")
    
    # Filter data
    df = data['page_engagement'][
        (data['page_engagement']['date'] >= filters['start_date']) &
        (data['page_engagement']['date'] <= filters['end_date'])
    ].copy()
    
    if df.empty:
        st.warning("No page engagement data available for selected date range")
        return
    
    # Aggregate by page
    page_summary = df.groupby('path').agg({
        'pageviews': 'sum',
        'unique_users': 'sum',
        'sessions_with_page': 'sum',
        'avg_scroll_depth': 'mean',
        'total_clicks': 'sum'
    }).reset_index()
    
    page_summary['click_per_pageview'] = (page_summary['total_clicks'] / page_summary['pageviews']).round(2)
    page_summary = page_summary.sort_values('pageviews', ascending=False)
    
    # TOP METRICS
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pageviews = page_summary['pageviews'].sum()
        st.metric("👁️ Total Pageviews", f"{total_pageviews:,}")
    
    with col2:
        unique_pages = len(page_summary)
        st.metric("📄 Unique Pages", f"{unique_pages:,}")
    
    with col3:
        avg_scroll = page_summary['avg_scroll_depth'].mean()
        st.metric("📜 Avg Scroll Depth", f"{avg_scroll:.1f}%")
    
    with col4:
        total_clicks = page_summary['total_clicks'].sum()
        st.metric("🖱️ Total Clicks", f"{total_clicks:,}")
    
    # TOP PAGES
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔝 Top 10 Most Viewed Pages")
        
        top_10_pages = page_summary.head(10)
        
        fig = px.bar(
            top_10_pages,
            y='path',
            x='pageviews',
            orientation='h',
            title='Top Pages by Pageviews',
            labels={'pageviews': 'Pageviews', 'path': 'Page Path'},
            color='pageviews',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Engagement by Page")
        
        # Show top 10 by unique users
        top_engagement = page_summary.nlargest(10, 'unique_users')
        
        fig = px.bar(
            top_engagement,
            y='path',
            x='unique_users',
            orientation='h',
            title='Top Pages by Unique Users',
            labels={'unique_users': 'Unique Users', 'path': 'Page Path'},
            color='unique_users',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # SCROLL DEPTH ANALYSIS
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📜 Pages with Best Engagement (High Scroll)")
        
        high_scroll = page_summary[page_summary['pageviews'] >= 50].nlargest(10, 'avg_scroll_depth')
        
        fig = px.bar(
            high_scroll,
            y='path',
            x='avg_scroll_depth',
            orientation='h',
            title='Top 10 Pages by Scroll Depth (min 50 views)',
            labels={'avg_scroll_depth': 'Avg Scroll Depth (%)', 'path': 'Page Path'},
            color='avg_scroll_depth',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚠️ Pages with Low Engagement (Low Scroll)")
        
        low_scroll = page_summary[page_summary['pageviews'] >= 50].nsmallest(10, 'avg_scroll_depth')
        
        fig = px.bar(
            low_scroll,
            y='path',
            x='avg_scroll_depth',
            orientation='h',
            title='Bottom 10 Pages by Scroll Depth (min 50 views)',
            labels={'avg_scroll_depth': 'Avg Scroll Depth (%)', 'path': 'Page Path'},
            color='avg_scroll_depth',
            color_continuous_scale='Reds_r'
        )
        
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # CLICK ANALYSIS
    st.markdown("---")
    st.subheader("🖱️ Click-Through Rate Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pages with high clicks
        high_ctr = page_summary[page_summary['pageviews'] >= 50].nlargest(10, 'click_per_pageview')
        
        fig = px.bar(
            high_ctr,
            y='path',
            x='click_per_pageview',
            orientation='h',
            title='Pages with Highest Click Rate',
            labels={'click_per_pageview': 'Clicks per Pageview', 'path': 'Page Path'},
            color='click_per_pageview',
            color_continuous_scale='Purples'
        )
        
        fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Scatter: Pageviews vs Scroll Depth
        fig = px.scatter(
            page_summary[page_summary['pageviews'] >= 20],
            x='pageviews',
            y='avg_scroll_depth',
            size='total_clicks',
            hover_data=['path'],
            title='Pageviews vs Engagement (size = clicks)',
            labels={
                'pageviews': 'Pageviews',
                'avg_scroll_depth': 'Avg Scroll Depth (%)'
            },
            color='avg_scroll_depth',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # PAGE CATEGORY ANALYSIS
    st.markdown("---")
    st.subheader("📂 Performance by Page Type")
    
    # Extract page type from path
    def categorize_page(path):
        if pd.isna(path):
            return 'Other'
        path = path.lower()
        if '/product' in path:
            return 'Product Page'
        elif '/category' in path or '/collection' in path:
            return 'Category Page'
        elif '/cart' in path:
            return 'Cart'
        elif '/checkout' in path:
            return 'Checkout'
        elif path == '/' or path == '/home':
            return 'Homepage'
        elif '/blog' in path or '/article' in path:
            return 'Blog/Content'
        else:
            return 'Other'
    
    page_summary['page_type'] = page_summary['path'].apply(categorize_page)
    
    type_summary = page_summary.groupby('page_type').agg({
        'pageviews': 'sum',
        'avg_scroll_depth': 'mean',
        'click_per_pageview': 'mean'
    }).reset_index()
    
    type_summary = type_summary.sort_values('pageviews', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            type_summary,
            x='page_type',
            y='pageviews',
            title='Pageviews by Page Type',
            labels={'pageviews': 'Total Pageviews', 'page_type': 'Page Type'},
            color='pageviews',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            type_summary,
            x='page_type',
            y='avg_scroll_depth',
            title='Avg Scroll Depth by Page Type',
            labels={'avg_scroll_depth': 'Avg Scroll Depth (%)', 'page_type': 'Page Type'},
            color='avg_scroll_depth',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # DETAILED TABLE
    st.markdown("---")
    st.subheader("📋 Detailed Page Performance")
    
    st.dataframe(
        page_summary.head(50).style.format({
            'pageviews': '{:,}',
            'unique_users': '{:,}',
            'sessions_with_page': '{:,}',
            'avg_scroll_depth': '{:.1f}%',
            'total_clicks': '{:,}',
            'click_per_pageview': '{:.2f}'
        }).background_gradient(subset=['pageviews'], cmap='Blues'),
        use_container_width=True,
        height=400
    )
    
    # INSIGHTS
    st.markdown("---")
    st.subheader("💡 UX Optimization Recommendations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Low scroll pages
        low_engagement_pages = len(page_summary[
            (page_summary['avg_scroll_depth'] < 30) &
            (page_summary['pageviews'] >= 50)
        ])
        
        st.warning(f"""
        **⚠️ Low Engagement Pages**
        
        {low_engagement_pages} pages with <30% scroll depth
        
        **Possible Issues:**
        - Content too long or boring
        - Slow page load
        - Unclear value proposition
        
        **Action**: Review content structure
        """)
    
    with col2:
        # High traffic, low clicks
        high_traffic_low_clicks = page_summary[
            (page_summary['pageviews'] >= page_summary['pageviews'].median()) &
            (page_summary['click_per_pageview'] < 1)
        ]
        
        if not high_traffic_low_clicks.empty:
            st.warning(f"""
            **🖱️ Low Click-Through**
            
            {len(high_traffic_low_clicks)} popular pages with <1 click/view
            
            **Possible Issues:**
            - Weak CTAs
            - Unclear next steps
            - Dead-end pages
            
            **Action**: Add prominent CTAs
            """)
    
    with col3:
        # Best performing page type
        best_type = type_summary.iloc[0]
        
        st.success(f"""
        **✅ Top Page Type**
        
        **{best_type['page_type']}**
        
        - Views: {best_type['pageviews']:,.0f}
        - Scroll: {best_type['avg_scroll_depth']:.1f}%
        
        Apply successful patterns to other page types
        """)

# ==============================================================================
# PAGE 7: DISCOUNT & PROMOTION ANALYSIS
# ==============================================================================

def page_promotions(data, filters):
    """Discount & Promotion Analysis Dashboard"""
    
    st.markdown('<div class="main-header">💰 Discount & Promotion Analysis</div>', unsafe_allow_html=True)
    st.markdown("### Measure effectiveness of promotional campaigns")
    
    # Filter data
    df = data['coupon_performance'][
        (data['coupon_performance']['date'] >= filters['start_date']) &
        (data['coupon_performance']['date'] <= filters['end_date'])
    ].copy()
    
    if df.empty:
        st.warning("No coupon data available for selected date range")
        return
    
    # Separate coupon vs non-coupon orders
    with_coupon = df[df['discount_coupon_code'] != 'NO_COUPON']
    without_coupon = df[df['discount_coupon_code'] == 'NO_COUPON']
    
    # Calculate totals
    total_discount = with_coupon['total_discount_given'].sum()
    revenue_with_coupon = with_coupon['total_revenue'].sum()
    revenue_without_coupon = without_coupon['total_revenue'].sum()
    total_revenue = revenue_with_coupon + revenue_without_coupon
    
    orders_with_coupon = with_coupon['usage_count'].sum()
    orders_without_coupon = without_coupon['usage_count'].sum()
    total_orders = orders_with_coupon + orders_without_coupon
    
    # TOP METRICS
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💸 Total Discount Given", f"${total_discount:,.0f}")
    
    with col2:
        coupon_pct = (revenue_with_coupon / total_revenue * 100) if total_revenue > 0 else 0
        st.metric("📊 % Revenue with Coupons", f"{coupon_pct:.1f}%")
    
    with col3:
        aov_with = revenue_with_coupon / orders_with_coupon if orders_with_coupon > 0 else 0
        st.metric("💳 AOV (with coupon)", f"${aov_with:.2f}")
    
    with col4:
        aov_without = revenue_without_coupon / orders_without_coupon if orders_without_coupon > 0 else 0
        st.metric("💳 AOV (no coupon)", f"${aov_without:.2f}")
    
    # COUPON VS NON-COUPON COMPARISON
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Revenue Distribution")
        
        revenue_comparison = pd.DataFrame({
            'Type': ['With Coupon', 'Without Coupon'],
            'Revenue': [revenue_with_coupon, revenue_without_coupon],
            'Orders': [orders_with_coupon, orders_without_coupon]
        })
        
        fig = px.pie(
            revenue_comparison,
            values='Revenue',
            names='Type',
            title='Revenue: Coupon vs No Coupon',
            hole=0.4,
            color_discrete_sequence=['#ff6b6b', '#4ecdc4']
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🛍️ Order Distribution")
        
        fig = px.pie(
            revenue_comparison,
            values='Orders',
            names='Type',
            title='Orders: Coupon vs No Coupon',
            hole=0.4,
            color_discrete_sequence=['#ff6b6b', '#4ecdc4']
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # AOV COMPARISON
    st.markdown("---")
    st.subheader("💵 Average Order Value Comparison")
    
    comparison_data = pd.DataFrame({
        'Order Type': ['With Coupon', 'Without Coupon'],
        'AOV': [aov_with, aov_without]
    })
    
    fig = px.bar(
        comparison_data,
        x='Order Type',
        y='AOV',
        title='Average Order Value: Coupon vs No Coupon',
        labels={'AOV': 'Average Order Value ($)', 'Order Type': ''},
        color='AOV',
        color_continuous_scale='RdYlGn',
        text='AOV'
    )
    
    fig.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    aov_diff = ((aov_with - aov_without) / aov_without * 100) if aov_without > 0 else 0
    
    if aov_with > aov_without:
        st.success(f"✅ Coupons increase AOV by {aov_diff:.1f}% - customers buy more with discounts!")
    else:
        st.warning(f"⚠️ Coupons decrease AOV by {abs(aov_diff):.1f}% - customers may use coupons only for cheap items")
    
    # TOP COUPONS
    st.markdown("---")
    st.subheader("🏆 Most Popular Coupons")
    
    coupon_summary = with_coupon.groupby('discount_coupon_code').agg({
        'usage_count': 'sum',
        'total_discount_given': 'sum',
        'total_revenue': 'sum',
        'avg_order_value': 'mean',
        'discount_percentage': 'mean'
    }).reset_index()
    
    coupon_summary = coupon_summary.sort_values('usage_count', ascending=False).head(15)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            coupon_summary,
            y='discount_coupon_code',
            x='usage_count',
            orientation='h',
            title='Top 15 Coupons by Usage',
            labels={'usage_count': 'Times Used', 'discount_coupon_code': 'Coupon Code'},
            color='usage_count',
            color_continuous_scale='Oranges'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            coupon_summary,
            y='discount_coupon_code',
            x='total_revenue',
            orientation='h',
            title='Top 15 Coupons by Revenue Generated',
            labels={'total_revenue': 'Revenue ($)', 'discount_coupon_code': 'Coupon Code'},
            color='total_revenue',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # DISCOUNT DEPTH ANALYSIS
    st.markdown("---")
    st.subheader("📉 Discount Depth Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribution of discount percentages
        discount_buckets = pd.cut(
            with_coupon['discount_percentage'],
            bins=[0, 10, 20, 30, 40, 100],
            labels=['0-10%', '10-20%', '20-30%', '30-40%', '40%+']
        )
        
        discount_dist = discount_buckets.value_counts().sort_index().reset_index()
        discount_dist.columns = ['Discount Range', 'Count']
        
        fig = px.bar(
            discount_dist,
            x='Discount Range',
            y='Count',
            title='Distribution of Discount Levels',
            labels={'Count': 'Number of Orders', 'Discount Range': 'Discount %'},
            color='Count',
            color_continuous_scale='Reds'
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Revenue by discount level
        with_coupon_copy = with_coupon.copy()
        with_coupon_copy['discount_bucket'] = pd.cut(
            with_coupon_copy['discount_percentage'],
            bins=[0, 10, 20, 30, 40, 100],
            labels=['0-10%', '10-20%', '20-30%', '30-40%', '40%+']
        )
        
        revenue_by_discount = with_coupon_copy.groupby('discount_bucket')['total_revenue'].sum().reset_index()
        revenue_by_discount.columns = ['Discount Range', 'Revenue']
        
        fig = px.bar(
            revenue_by_discount,
            x='Discount Range',
            y='Revenue',
            title='Revenue by Discount Level',
            labels={'Revenue': 'Total Revenue ($)', 'Discount Range': 'Discount %'},
            color='Revenue',
            color_continuous_scale='Greens'
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # DISCOUNT TREND OVER TIME
    st.markdown("---")
    st.subheader("📈 Discount Trend Over Time")
    
    daily_discount = with_coupon.groupby('date').agg({
        'total_discount_given': 'sum',
        'total_revenue': 'sum',
        'usage_count': 'sum'
    }).reset_index()
    
    daily_discount['discount_rate'] = (daily_discount['total_discount_given'] / daily_discount['total_revenue'] * 100).round(2)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=daily_discount['date'], y=daily_discount['total_discount_given'], 
                   name="Discount Given", line=dict(color='red', width=2)),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(x=daily_discount['date'], y=daily_discount['usage_count'], 
                   name="Coupon Usage", line=dict(color='blue', width=2)),
        secondary_y=True
    )
    
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Discount Given ($)", secondary_y=False)
    fig.update_yaxes(title_text="Coupon Usage Count", secondary_y=True)
    fig.update_layout(title="Daily Discount Trend", height=400, hovermode='x unified')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # DETAILED TABLE
    st.markdown("---")
    st.subheader("📋 Detailed Coupon Performance")
    
    st.dataframe(
        coupon_summary.style.format({
            'usage_count': '{:,}',
            'total_discount_given': '${:,.2f}',
            'total_revenue': '${:,.2f}',
            'avg_order_value': '${:.2f}',
            'discount_percentage': '{:.2f}%'
        }).background_gradient(subset=['total_revenue'], cmap='Greens'),
        use_container_width=True,
        height=400
    )
    
    # INSIGHTS
    st.markdown("---")
    st.subheader("💡 Promotion Insights & Recommendations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        roi = ((revenue_with_coupon - total_discount) / total_discount * 100) if total_discount > 0 else 0
        
        if roi > 200:
            st.success(f"""
            **✅ Great ROI**
            
            Every $1 in discounts generates ${roi/100:.2f} in revenue
            
            **Action**: Coupons are profitable, continue strategy
            """)
        elif roi > 100:
            st.info(f"""
            **✔️ Positive ROI**
            
            Every $1 in discounts generates ${roi/100:.2f} in revenue
            
            **Action**: Monitor closely, optimize discount depth
            """)
        else:
            st.warning(f"""
            **⚠️ Low ROI**
            
            Every $1 in discounts generates ${roi/100:.2f} in revenue
            
            **Action**: Reduce discount depth or frequency
            """)
    
    with col2:
        if coupon_pct > 70:
            st.warning(f"""
            **⚠️ Over-Reliance on Discounts**
            
            {coupon_pct:.1f}% of revenue uses coupons
            
            **Risk**: Brand devaluation, margin erosion
            
            **Action**: 
            - Test reducing discount frequency
            - Focus on value proposition
            """)
        else:
            st.success(f"""
            **✅ Balanced Discount Strategy**
            
            {coupon_pct:.1f}% of revenue uses coupons
            
            Good mix of full-price and discounted sales
            """)
    
    with col3:
        # Best performing coupon
        if not coupon_summary.empty:
            best_coupon = coupon_summary.iloc[0]
            
            st.info(f"""
            **🏆 Top Coupon**
            
            Code: **{best_coupon['discount_coupon_code']}**
            
            - Used: {best_coupon['usage_count']:,.0f} times
            - Revenue: ${best_coupon['total_revenue']:,.0f}
            - Avg discount: {best_coupon['discount_percentage']:.1f}%
            
            Replicate this coupon structure
            """)

# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    """Main application entry point"""
    
    # Load data
    data = load_data()
    
    if data is None:
        st.stop()
    
    # Render sidebar and get filters
    filters = render_sidebar(data)
    
    # Page navigation
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
    
    # Render selected page
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
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
    📊 E-Commerce Analytics Dashboard<br>
    Built with Streamlit<br>
    Last updated: 2026-02-14
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()