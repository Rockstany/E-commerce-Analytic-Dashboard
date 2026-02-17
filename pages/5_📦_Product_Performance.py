"""
PRODUCT PERFORMANCE DASHBOARD
==============================
KPI 19: Units Sold
KPI 20: Product Contribution to Revenue
Plus: Product metrics from earlier KPIs
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(page_title="Product Performance", page_icon="📦", layout="wide")

st.title("📦 Product Performance Dashboard")
st.markdown("### Analyze product sales, revenue, and trends")

@st.cache_data
def load_data():
    try:
        product_daily = pd.read_csv('aggregated_data/product_performance_daily.csv')
        order_items = pd.read_csv('raw_data/order_line_item_table.csv')
        cart = pd.read_csv('raw_data/add_to_cart_table.csv')
        return product_daily, order_items, cart
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None, None

product_df, items_df, cart_df = load_data()

if product_df is not None and items_df is not None:
    product_df['date'] = pd.to_datetime(product_df['date'])
    
    # DATE FILTER
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Start Date",
                                   value=product_df['date'].max() - timedelta(days=30),
                                   min_value=product_df['date'].min().date(),
                                   max_value=product_df['date'].max().date())
    
    with col2:
        end_date = st.date_input("End Date",
                                 value=product_df['date'].max().date(),
                                 min_value=product_df['date'].min().date(),
                                 max_value=product_df['date'].max().date())
    
    # Filter
    mask = (product_df['date'].dt.date >= start_date) & (product_df['date'].dt.date <= end_date)
    filtered_products = product_df[mask]
    
    # Aggregate by product
    product_summary = filtered_products.groupby('product_name').agg({
        'times_purchased': 'sum',
        'total_quantity_sold': 'sum',
        'total_revenue': 'sum',
        'times_added_to_cart': 'sum',
        'cart_to_purchase_rate': 'mean'
    }).reset_index()
    
    # KEY METRICS
    st.markdown("---")
    st.markdown("### 📊 Product KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_products = product_summary['product_name'].nunique()
        st.metric("📦 Total Products", f"{total_products:,}",
                 help="Number of unique products")
    
    with col2:
        # KPI 19: Units Sold
        total_units = product_summary['total_quantity_sold'].sum()
        st.metric("📊 Units Sold", f"{total_units:,}",
                 help="Total quantity sold across all products")
    
    with col3:
        # KPI 20: Revenue
        total_revenue = product_summary['total_revenue'].sum()
        st.metric("💰 Total Revenue", f"${total_revenue:,.0f}",
                 help="Total revenue from products")
    
    with col4:
        avg_conv = product_summary['cart_to_purchase_rate'].mean()
        st.metric("🎯 Avg Conversion", f"{avg_conv:.1f}%",
                 help="Average cart-to-purchase rate")
    
    # TOP PRODUCTS
    st.markdown("---")
    st.markdown("### 🏆 Top 10 Products by Revenue")
    
    top_products = product_summary.nlargest(10, 'total_revenue')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_rev = px.bar(top_products, x='product_name', y='total_revenue',
                        title='Revenue by Product',
                        color='total_revenue', color_continuous_scale='Blues',
                        text='total_revenue')
        fig_rev.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_rev.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_rev, use_container_width=True)
    
    with col2:
        fig_units = px.bar(top_products, x='product_name', y='total_quantity_sold',
                          title='Units Sold by Product',
                          color='total_quantity_sold', color_continuous_scale='Greens',
                          text='total_quantity_sold')
        fig_units.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_units.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_units, use_container_width=True)
    
    # PRODUCT PERFORMANCE TABLE
    st.markdown("---")
    st.markdown("### 📋 Product Performance Metrics")
    
    # Add calculated metrics
    product_summary['Revenue per Unit'] = (product_summary['total_revenue'] / 
                                          product_summary['total_quantity_sold']).round(2)
    product_summary['% of Total Revenue'] = (product_summary['total_revenue'] / 
                                             total_revenue * 100).round(2)
    
    # Sort by revenue
    product_summary = product_summary.sort_values('total_revenue', ascending=False)
    
    # Format for display
    display_products = product_summary.head(20).copy()
    display_products.columns = ['Product', 'Purchases', 'Units Sold', 'Revenue', 
                                'Cart Adds', 'Cart→Purchase %', 'Price/Unit', '% of Revenue']
    display_products['Revenue'] = display_products['Revenue'].apply(lambda x: f'${x:,.0f}')
    display_products['Price/Unit'] = display_products['Price/Unit'].apply(lambda x: f'${x:.2f}')
    display_products['Cart→Purchase %'] = display_products['Cart→Purchase %'].apply(lambda x: f'{x:.1f}%')
    display_products['% of Revenue'] = display_products['% of Revenue'].apply(lambda x: f'{x:.1f}%')
    
    st.dataframe(display_products, use_container_width=True, hide_index=True)
    
    # PRODUCT TRENDS
    st.markdown("---")
    st.markdown("### 📈 Product Revenue Trends")
    
    # Get top 5 products
    top_5 = product_summary.nlargest(5, 'total_revenue')['product_name'].tolist()
    
    # Filter for top 5
    top_5_data = filtered_products[filtered_products['product_name'].isin(top_5)]
    
    fig_trends = px.line(top_5_data, x='date', y='total_revenue', 
                        color='product_name',
                        title='Top 5 Products - Revenue Trend',
                        labels={'total_revenue': 'Daily Revenue', 'date': 'Date'})
    fig_trends.update_layout(hovermode='x unified', plot_bgcolor='white')
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # CART TO PURCHASE ANALYSIS
    st.markdown("---")
    st.markdown("### 🛒 Cart-to-Purchase Conversion")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Best converting products
        best_conv = product_summary.nlargest(10, 'cart_to_purchase_rate')
        
        fig_best = px.bar(best_conv, x='product_name', y='cart_to_purchase_rate',
                         title='Top 10 Products by Conversion Rate',
                         color='cart_to_purchase_rate', color_continuous_scale='Greens',
                         text='cart_to_purchase_rate')
        fig_best.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_best.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_best, use_container_width=True)
    
    with col2:
        # Worst converting (but popular)
        popular_products = product_summary[product_summary['times_added_to_cart'] >= 10]
        worst_conv = popular_products.nsmallest(10, 'cart_to_purchase_rate')
        
        fig_worst = px.bar(worst_conv, x='product_name', y='cart_to_purchase_rate',
                          title='Low Conversion Products (Need Attention)',
                          color='cart_to_purchase_rate', color_continuous_scale='Reds',
                          text='cart_to_purchase_rate')
        fig_worst.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_worst.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_worst, use_container_width=True)
    
    # REVENUE CONTRIBUTION
    st.markdown("---")
    st.markdown("### 💰 KPI 20: Revenue Contribution Analysis")
    
    # Calculate cumulative revenue %
    product_summary_sorted = product_summary.sort_values('total_revenue', ascending=False).copy()
    product_summary_sorted['Cumulative Revenue'] = product_summary_sorted['total_revenue'].cumsum()
    product_summary_sorted['Cumulative %'] = (product_summary_sorted['Cumulative Revenue'] / 
                                              total_revenue * 100)
    
    # Find 80/20 rule
    products_80_pct = (product_summary_sorted['Cumulative %'] <= 80).sum()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=product_summary_sorted.head(20)['product_name'],
            y=product_summary_sorted.head(20)['total_revenue'],
            name='Revenue',
            marker_color='#636EFA'
        ))
        fig_pareto.add_trace(go.Scatter(
            x=product_summary_sorted.head(20)['product_name'],
            y=product_summary_sorted.head(20)['Cumulative %'],
            name='Cumulative %',
            yaxis='y2',
            line=dict(color='#EF553B', width=3),
            marker=dict(size=8)
        ))
        
        fig_pareto.update_layout(
            title='Pareto Analysis - Top 20 Products',
            yaxis=dict(title='Revenue ($)'),
            yaxis2=dict(title='Cumulative %', overlaying='y', side='right', range=[0, 100]),
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        st.plotly_chart(fig_pareto, use_container_width=True)
    
    with col2:
        st.metric("🎯 80/20 Rule", f"{products_80_pct} products",
                 f"Drive 80% of revenue")
        
        st.info(f"""
        **Revenue Distribution:**
        - Top {products_80_pct} products = 80% revenue
        - Remaining {total_products - products_80_pct} products = 20% revenue
        - Focus on top performers
        """)
    
    # INSIGHTS
    st.markdown("---")
    st.markdown("### 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    top_product = product_summary.iloc[0]
    
    with col1:
        st.success(f"""
        **Top Performer:**
        - **{top_product['product_name']}**
        - ${top_product['total_revenue']:,.0f} revenue
        - {top_product['total_quantity_sold']:,.0f} units sold
        - {top_product['cart_to_purchase_rate']:.1f}% conversion
        """)
    
    with col2:
        if len(worst_conv) > 0:
            problem_product = worst_conv.iloc[0]
            st.warning(f"""
            **Needs Attention:**
            - **{problem_product['product_name']}**
            - Only {problem_product['cart_to_purchase_rate']:.1f}% conversion
            - {problem_product['times_added_to_cart']:.0f} cart adds
            - Review pricing, images, or description
            """)

else:
    st.error("Unable to load product data")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>Product Performance Dashboard</p></div>", unsafe_allow_html=True)
