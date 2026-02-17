"""
CONVERSION DASHBOARD
====================
KPI 8: Total Orders
KPI 9: Revenue
KPI 10: Average Order Value
KPI 11: Discount Usage
KPI 13: Cart Drop-off Rate
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(page_title="Conversion", page_icon="🛒", layout="wide")

st.title("🛒 Conversion Dashboard")
st.markdown("### Orders, revenue, and conversion optimization")

@st.cache_data
def load_data():
    try:
        daily = pd.read_csv('aggregated_data/daily_business_metrics.csv')
        orders = pd.read_csv('raw_data/order_table.csv')
        funnel = pd.read_csv('aggregated_data/session_funnel.csv')
        cart = pd.read_csv('raw_data/add_to_cart_table.csv')
        coupon = pd.read_csv('aggregated_data/coupon_performance.csv')
        return daily, orders, funnel, cart, coupon
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None, None, None, None

daily_df, orders_df, funnel_df, cart_df, coupon_df = load_data()

if daily_df is not None and orders_df is not None:
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    orders_df['time'] = pd.to_datetime(orders_df['time'])
    
    # DATE FILTER
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Start Date", 
                                   value=daily_df['date'].max() - timedelta(days=30),
                                   min_value=daily_df['date'].min().date(),
                                   max_value=daily_df['date'].max().date())
    
    with col2:
        end_date = st.date_input("End Date",
                                 value=daily_df['date'].max().date(),
                                 min_value=daily_df['date'].min().date(),
                                 max_value=daily_df['date'].max().date())
    
    # Filter
    mask = (daily_df['date'].dt.date >= start_date) & (daily_df['date'].dt.date <= end_date)
    filtered_daily = daily_df[mask]
    
    order_mask = (orders_df['time'].dt.date >= start_date) & (orders_df['time'].dt.date <= end_date)
    filtered_orders = orders_df[order_mask]
    
    # KEY METRICS
    st.markdown("---")
    st.markdown("### 📊 Conversion KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # KPI 8: Total Orders
        total_orders = filtered_daily['total_orders'].sum()
        st.metric("🛒 Total Orders", f"{total_orders:,.0f}",
                 help="Number of completed purchases")
    
    with col2:
        # KPI 9: Revenue
        total_revenue = filtered_daily['total_revenue'].sum()
        st.metric("💰 Total Revenue", f"${total_revenue:,.0f}",
                 help="Total sales revenue")
    
    with col3:
        # KPI 10: Average Order Value
        aov = filtered_daily['avg_order_value'].mean()
        st.metric("💳 Avg Order Value", f"${aov:.2f}",
                 help="Average amount per order")
    
    with col4:
        # Conversion Rate
        conv_rate = filtered_daily['conversion_rate'].mean()
        st.metric("📈 Conversion Rate", f"{conv_rate:.2f}%",
                 help="% of sessions that convert")
    
    # DISCOUNT METRICS
    st.markdown("---")
    st.markdown("### 💸 KPI 11: Discount Usage")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_discount = filtered_orders['discount'].sum()
        st.metric("💵 Total Discounts", f"${total_discount:,.0f}")
    
    with col2:
        orders_with_discount = (filtered_orders['discount'] > 0).sum()
        discount_rate = (orders_with_discount / len(filtered_orders) * 100) if len(filtered_orders) > 0 else 0
        st.metric("🎟️ Orders with Discount", f"{orders_with_discount:,}",
                 f"{discount_rate:.1f}% of orders")
    
    with col3:
        avg_discount = filtered_orders[filtered_orders['discount'] > 0]['discount'].mean()
        st.metric("📊 Avg Discount", f"${avg_discount:.2f}" if avg_discount == avg_discount else "$0.00")
    
    with col4:
        discount_pct = (total_discount / total_revenue * 100) if total_revenue > 0 else 0
        st.metric("📉 Discount % of Revenue", f"{discount_pct:.2f}%")
    
    # CART ABANDONMENT
    if funnel_df is not None and cart_df is not None:
        st.markdown("---")
        st.markdown("### 🛒 KPI 13: Cart Drop-off Rate")
        
        funnel_df['date'] = pd.to_datetime(funnel_df['date'])
        funnel_mask = (funnel_df['date'].dt.date >= start_date) & (funnel_df['date'].dt.date <= end_date)
        filtered_funnel = funnel_df[funnel_mask]
        
        total_cart_adds = filtered_funnel['had_add_to_cart'].sum()
        total_purchases = filtered_funnel['had_order'].sum()
        cart_dropoff = total_cart_adds - total_purchases
        dropoff_rate = (cart_dropoff / total_cart_adds * 100) if total_cart_adds > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("➕ Cart Additions", f"{total_cart_adds:,}")
        
        with col2:
            st.metric("✅ Completed Purchases", f"{total_purchases:,}")
        
        with col3:
            st.metric("❌ Abandoned Carts", f"{cart_dropoff:,}",
                     delta=f"-{dropoff_rate:.1f}%", delta_color="inverse")
        
        with col4:
            cart_conv_rate = (total_purchases / total_cart_adds * 100) if total_cart_adds > 0 else 0
            st.metric("🎯 Cart Conversion", f"{cart_conv_rate:.1f}%")
    
    # REVENUE TREND
    st.markdown("---")
    st.markdown("### 📈 Revenue & Orders Trend")
    
    fig_rev = go.Figure()
    fig_rev.add_trace(go.Bar(name='Revenue', x=filtered_daily['date'], y=filtered_daily['total_revenue'],
                             marker_color='#636EFA'))
    fig_rev.add_trace(go.Scatter(name='Orders', x=filtered_daily['date'], y=filtered_daily['total_orders'],
                                 yaxis='y2', line=dict(color='#EF553B', width=3)))
    
    fig_rev.update_layout(
        title='Daily Revenue & Orders',
        yaxis=dict(title='Revenue ($)'),
        yaxis2=dict(title='Orders', overlaying='y', side='right'),
        hovermode='x unified',
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_rev, use_container_width=True)
    
    # FUNNEL VISUALIZATION
    if funnel_df is not None:
        st.markdown("---")
        st.markdown("### 🔽 Complete Conversion Funnel")
        
        total_sessions = len(filtered_funnel)
        product_views = filtered_funnel['had_product_view'].sum()
        
        fig_funnel = go.Figure(go.Funnel(
            y=['Sessions', 'Product Views', 'Add to Cart', 'Orders'],
            x=[total_sessions, product_views, total_cart_adds, total_purchases],
            textinfo="value+percent initial",
            marker=dict(color=['#636EFA', '#EF553B', '#00CC96', '#AB63FA'])
        ))
        fig_funnel.update_layout(height=400, title="Conversion Funnel with Drop-off Rates")
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        # Drop-off percentages
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dropoff_1 = ((total_sessions - product_views) / total_sessions * 100) if total_sessions > 0 else 0
            st.metric("🔻 Session → Product", f"{dropoff_1:.1f}% drop-off")
        
        with col2:
            dropoff_2 = ((product_views - total_cart_adds) / product_views * 100) if product_views > 0 else 0
            st.metric("🔻 Product → Cart", f"{dropoff_2:.1f}% drop-off")
        
        with col3:
            st.metric("🔻 Cart → Purchase", f"{dropoff_rate:.1f}% drop-off")
    
    # DISCOUNT PERFORMANCE
    if coupon_df is not None:
        st.markdown("---")
        st.markdown("### 🎟️ Coupon Performance")
        
        coupon_df['date'] = pd.to_datetime(coupon_df['date'])
        coupon_mask = (coupon_df['date'].dt.date >= start_date) & (coupon_df['date'].dt.date <= end_date)
        filtered_coupons = coupon_df[coupon_mask]
        
        top_coupons = filtered_coupons.groupby('discount_coupon_code').agg({
            'usage_count': 'sum',
            'total_discount_given': 'sum',
            'total_revenue': 'sum'
        }).nlargest(10, 'total_revenue').reset_index()
        
        top_coupons.columns = ['Coupon', 'Usage', 'Discount Given', 'Revenue']
        
        fig_coupon = px.bar(top_coupons, x='Coupon', y='Revenue',
                           title='Top 10 Coupons by Revenue',
                           color='Revenue', color_continuous_scale='Greens',
                           text='Revenue')
        fig_coupon.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_coupon.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_coupon, use_container_width=True)
        
        # Coupon table
        display_coupons = top_coupons.copy()
        display_coupons['Discount Given'] = display_coupons['Discount Given'].apply(lambda x: f'${x:,.0f}')
        display_coupons['Revenue'] = display_coupons['Revenue'].apply(lambda x: f'${x:,.0f}')
        st.dataframe(display_coupons, use_container_width=True, hide_index=True)
    
    # INSIGHTS
    st.markdown("---")
    st.markdown("### 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success(f"""
        **Conversion Performance:**
        - {total_orders:,} orders generating ${total_revenue:,.0f}
        - {aov:.2f} average order value
        - {conv_rate:.2f}% overall conversion rate
        """)
    
    with col2:
        st.warning(f"""
        **Optimization Opportunities:**
        - {dropoff_rate:.1f}% cart abandonment rate
        - ${total_discount:,.0f} in discounts ({discount_pct:.1f}% of revenue)
        - Focus on reducing cart drop-offs
        """)

else:
    st.error("Unable to load conversion data")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>Conversion Dashboard</p></div>", unsafe_allow_html=True)
