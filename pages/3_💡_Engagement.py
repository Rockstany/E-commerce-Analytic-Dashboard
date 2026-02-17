"""
ENGAGEMENT DASHBOARD
===================
KPI 12: Add-to-Cart Rate
KPI 14: Scroll Depth
KPI 15: Click-Through Rate
KPI 17-18: Page Views
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Engagement", page_icon="💡", layout="wide")

st.title("💡 Engagement Dashboard")
st.markdown("### User interaction and content engagement")

@st.cache_data
def load_data():
    try:
        pageviews = pd.read_csv('raw_data/pageview_table.csv')
        scrolls = pd.read_csv('raw_data/scroll_table.csv')
        clicks = pd.read_csv('raw_data/click_table.csv')
        cart = pd.read_csv('raw_data/add_to_cart_table.csv')
        engagement = pd.read_csv('aggregated_data/page_engagement_metrics.csv')
        return pageviews, scrolls, clicks, cart, engagement
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None, None, None, None

pageviews_df, scrolls_df, clicks_df, cart_df, engagement_df = load_data()

if pageviews_df is not None:
    
    # KEY METRICS
    st.markdown("---")
    st.markdown("### 📊 Engagement KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # KPI 17: Page Views
        total_pageviews = len(pageviews_df)
        unique_pageviews = pageviews_df['session_id'].nunique()
        st.metric("📄 Total Page Views", f"{total_pageviews:,}", 
                 f"{unique_pageviews:,} unique sessions")
    
    with col2:
        # KPI 12: Add-to-Cart Rate
        if cart_df is not None:
            total_cart_adds = len(cart_df)
            cart_rate = (total_cart_adds / total_pageviews * 100) if total_pageviews > 0 else 0
            st.metric("🛒 Add-to-Cart Events", f"{total_cart_adds:,}",
                     f"{cart_rate:.2f}% of pageviews")
    
    with col3:
        # KPI 14: Scroll Depth
        if scrolls_df is not None:
            avg_scroll = scrolls_df['scroll_percent'].mean()
            st.metric("📊 Avg Scroll Depth", f"{avg_scroll:.1f}%",
                     help="Average percentage of page scrolled")
    
    with col4:
        # KPI 15: Click Events
        if clicks_df is not None:
            total_clicks = len(clicks_df)
            click_rate = (total_clicks / total_pageviews * 100) if total_pageviews > 0 else 0
            st.metric("👆 Total Clicks", f"{total_clicks:,}",
                     f"{click_rate:.1f}% CTR")
    
    # TOP PAGES
    st.markdown("---")
    st.markdown("### 📄 Most Viewed Pages")
    
    top_pages = pageviews_df['path'].value_counts().head(10).reset_index()
    top_pages.columns = ['Page', 'Views']
    
    fig_pages = px.bar(top_pages, x='Page', y='Views', 
                       title='Top 10 Pages by Views',
                       color='Views', color_continuous_scale='Blues')
    fig_pages.update_layout(showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig_pages, use_container_width=True)
    
    st.dataframe(top_pages, use_container_width=True, hide_index=True)
    
    # SCROLL DEPTH ANALYSIS
    if scrolls_df is not None:
        st.markdown("---")
        st.markdown("### 📊 Scroll Depth Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogram of scroll depths
            fig_scroll_hist = px.histogram(scrolls_df, x='scroll_percent', nbins=20,
                                          title='Scroll Depth Distribution',
                                          labels={'scroll_percent': 'Scroll Depth (%)', 'count': 'Frequency'})
            st.plotly_chart(fig_scroll_hist, use_container_width=True)
        
        with col2:
            # Scroll depth by page
            if 'path' in scrolls_df.columns:
                page_scroll = scrolls_df.groupby('path')['scroll_percent'].mean().nlargest(10).reset_index()
                page_scroll.columns = ['Page', 'Avg Scroll %']
                
                fig_page_scroll = px.bar(page_scroll, x='Page', y='Avg Scroll %',
                                        title='Top Pages by Scroll Engagement',
                                        color='Avg Scroll %', color_continuous_scale='Greens')
                fig_page_scroll.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_page_scroll, use_container_width=True)
    
    # CLICK ANALYSIS
    if clicks_df is not None:
        st.markdown("---")
        st.markdown("### 👆 Click Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Most clicked elements
            if 'target_text' in clicks_df.columns:
                top_clicks = clicks_df['target_text'].value_counts().head(10).reset_index()
                top_clicks.columns = ['Element', 'Clicks']
                
                fig_clicks = px.bar(top_clicks, x='Element', y='Clicks',
                                   title='Most Clicked Elements',
                                   color='Clicks', color_continuous_scale='Oranges')
                fig_clicks.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_clicks, use_container_width=True)
        
        with col2:
            # Click by page
            if 'path' in clicks_df.columns:
                page_clicks = clicks_df['path'].value_counts().head(10).reset_index()
                page_clicks.columns = ['Page', 'Clicks']
                
                fig_page_clicks = px.bar(page_clicks, x='Page', y='Clicks',
                                        title='Pages with Most Clicks',
                                        color='Clicks', color_continuous_scale='Purples')
                fig_page_clicks.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_page_clicks, use_container_width=True)
    
    # ADD TO CART ANALYSIS
    if cart_df is not None:
        st.markdown("---")
        st.markdown("### 🛒 Add-to-Cart Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top products added to cart
            if 'product_name' in cart_df.columns:
                top_cart_products = cart_df['product_name'].value_counts().head(10).reset_index()
                top_cart_products.columns = ['Product', 'Times Added']
                
                fig_cart = px.bar(top_cart_products, x='Product', y='Times Added',
                                 title='Most Added to Cart Products',
                                 color='Times Added', color_continuous_scale='Reds')
                fig_cart.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_cart, use_container_width=True)
        
        with col2:
            # Cart adds over time if date available
            if 'time' in cart_df.columns:
                cart_df['date'] = pd.to_datetime(cart_df['time']).dt.date
                daily_cart = cart_df.groupby('date').size().reset_index()
                daily_cart.columns = ['Date', 'Cart Adds']
                
                fig_cart_trend = px.line(daily_cart, x='Date', y='Cart Adds',
                                        title='Add-to-Cart Trend',
                                        markers=True)
                fig_cart_trend.update_traces(line_color='#EF553B')
                st.plotly_chart(fig_cart_trend, use_container_width=True)
    
    # PAGE ENGAGEMENT TABLE
    if engagement_df is not None:
        st.markdown("---")
        st.markdown("### 📊 Page Engagement Metrics")
        
        engagement_df['date'] = pd.to_datetime(engagement_df['date'])
        
        # Aggregate by page
        page_metrics = engagement_df.groupby('path').agg({
            'pageviews': 'sum',
            'unique_users': 'sum',
            'avg_scroll_depth': 'mean',
            'total_clicks': 'sum'
        }).nlargest(15, 'pageviews').reset_index()
        
        page_metrics.columns = ['Page', 'Total Views', 'Unique Users', 'Avg Scroll %', 'Total Clicks']
        page_metrics['Avg Scroll %'] = page_metrics['Avg Scroll %'].round(1)
        
        st.dataframe(page_metrics, use_container_width=True, hide_index=True)
    
    # INSIGHTS
    st.markdown("---")
    st.markdown("### 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Content Engagement:**
        - {total_pageviews:,} total page views
        - {avg_scroll if scrolls_df is not None else 'N/A'}% average scroll depth
        - {total_clicks if clicks_df is not None else 'N/A':,} click interactions
        """)
    
    with col2:
        if cart_df is not None:
            st.success(f"""
            **Purchase Intent:**
            - {total_cart_adds:,} items added to cart
            - {cart_rate:.2f}% add-to-cart rate
            - Focus on converting cart adds to purchases
            """)

else:
    st.error("Unable to load engagement data")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>Engagement Dashboard</p></div>", unsafe_allow_html=True)
