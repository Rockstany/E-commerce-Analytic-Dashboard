"""
MARKETING ATTRIBUTION DASHBOARD
================================

This page shows which marketing channels drive the most revenue and conversions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Marketing Attribution",
    page_icon="🎯",
    layout="wide"
)

# Custom styling
st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    h1 {color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🎯 Marketing Attribution Analysis")
st.markdown("### Track which campaigns and channels drive revenue")

# Load data
@st.cache_data(ttl=3600)
def load_data():
    """Load session attribution data"""
    try:
        df = pd.read_csv('data/session_attribution.csv')
        df['date'] = pd.to_datetime(df['date'])
        return df
    except FileNotFoundError:
        st.error("❌ session_attribution.csv not found in data/ folder")
        return None

df = load_data()

if df is not None:
    # ==================================================================
    # FILTERS
    # ==================================================================
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # Date filter
        date_range = st.date_input(
            "Date Range",
            value=(df['date'].max() - timedelta(days=30), df['date'].max()),
            min_value=df['date'].min(),
            max_value=df['date'].max()
        )
    
    with col2:
        # Channel filter
        if 'utm_source' in df.columns:
            all_sources = ['All'] + sorted(df['utm_source'].dropna().unique().tolist())
            selected_source = st.selectbox("Filter by Source", all_sources)
    
    # Apply filters
    if len(date_range) == 2:
        mask = (df['date'].dt.date >= date_range[0]) & \
               (df['date'].dt.date <= date_range[1])
        filtered_df = df[mask].copy()
    else:
        filtered_df = df.copy()
    
    if selected_source != 'All':
        filtered_df = filtered_df[filtered_df['utm_source'] == selected_source]
    
    # ==================================================================
    # KEY METRICS
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📊 Overall Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sessions = len(filtered_df)
        st.metric(
            "👥 Total Sessions",
            f"{total_sessions:,}",
            help="Total website visits in selected period"
        )
    
    with col2:
        total_conversions = filtered_df['converted'].sum()
        st.metric(
            "✅ Conversions",
            f"{total_conversions:,}",
            help="Number of sessions that resulted in orders"
        )
    
    with col3:
        conversion_rate = (total_conversions / total_sessions * 100) if total_sessions > 0 else 0
        st.metric(
            "📈 Conversion Rate",
            f"{conversion_rate:.2f}%",
            help="Percentage of sessions that converted"
        )
    
    with col4:
        total_revenue = filtered_df['revenue'].sum()
        st.metric(
            "💰 Revenue",
            f"${total_revenue:,.0f}",
            help="Total revenue attributed to these sessions"
        )
    
    # ==================================================================
    # CHANNEL PERFORMANCE
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 🎯 Performance by Marketing Channel")
    
    if 'utm_source' in filtered_df.columns:
        # Aggregate by source
        channel_perf = filtered_df.groupby('utm_source').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        channel_perf.columns = ['Channel', 'Sessions', 'Conversions', 'Revenue']
        
        # Calculate metrics
        channel_perf['Conversion Rate'] = (
            channel_perf['Conversions'] / channel_perf['Sessions'] * 100
        ).round(2)
        
        channel_perf['Revenue per Session'] = (
            channel_perf['Revenue'] / channel_perf['Sessions']
        ).round(2)
        
        # Sort by revenue
        channel_perf = channel_perf.sort_values('Revenue', ascending=False)
        
        # Two column layout
        col1, col2 = st.columns(2)
        
        with col1:
            # Revenue by channel chart
            st.markdown("#### 💰 Revenue by Channel")
            fig_revenue = px.bar(
                channel_perf,
                x='Channel',
                y='Revenue',
                color='Revenue',
                color_continuous_scale='Blues',
                text='Revenue'
            )
            fig_revenue.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_revenue.update_layout(
                showlegend=False,
                xaxis_title='',
                yaxis_title='Revenue ($)',
                plot_bgcolor='white'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col2:
            # Conversion rate by channel
            st.markdown("#### 📊 Conversion Rate by Channel")
            fig_conv = px.bar(
                channel_perf,
                x='Channel',
                y='Conversion Rate',
                color='Conversion Rate',
                color_continuous_scale='Greens',
                text='Conversion Rate'
            )
            fig_conv.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_conv.update_layout(
                showlegend=False,
                xaxis_title='',
                yaxis_title='Conversion Rate (%)',
                plot_bgcolor='white'
            )
            st.plotly_chart(fig_conv, use_container_width=True)
        
        # Detailed metrics table
        st.markdown("---")
        st.markdown("#### 📋 Detailed Channel Metrics")
        
        # Format table for display
        display_df = channel_perf.copy()
        display_df['Revenue'] = display_df['Revenue'].apply(lambda x: f'${x:,.2f}')
        display_df['Revenue per Session'] = display_df['Revenue per Session'].apply(lambda x: f'${x:.2f}')
        display_df['Conversion Rate'] = display_df['Conversion Rate'].apply(lambda x: f'{x:.2f}%')
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    
    # ==================================================================
    # CAMPAIGN PERFORMANCE
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📢 Performance by Campaign")
    
    if 'utm_campaign' in filtered_df.columns:
        # Filter out empty campaigns
        campaign_df = filtered_df[filtered_df['utm_campaign'].notna() & 
                                  (filtered_df['utm_campaign'] != '')].copy()
        
        if len(campaign_df) > 0:
            # Aggregate by campaign
            campaign_perf = campaign_df.groupby('utm_campaign').agg({
                'session_id': 'count',
                'converted': 'sum',
                'revenue': 'sum'
            }).reset_index()
            
            campaign_perf.columns = ['Campaign', 'Sessions', 'Conversions', 'Revenue']
            campaign_perf['Conversion Rate'] = (
                campaign_perf['Conversions'] / campaign_perf['Sessions'] * 100
            ).round(2)
            
            # Sort by revenue
            campaign_perf = campaign_perf.sort_values('Revenue', ascending=False)
            
            # Top 10 campaigns
            top_campaigns = campaign_perf.head(10)
            
            # Bubble chart
            fig_bubble = px.scatter(
                top_campaigns,
                x='Sessions',
                y='Conversion Rate',
                size='Revenue',
                color='Revenue',
                hover_name='Campaign',
                labels={
                    'Sessions': 'Total Sessions',
                    'Conversion Rate': 'Conversion Rate (%)',
                    'Revenue': 'Revenue ($)'
                },
                title='Top 10 Campaigns (Bubble size = Revenue)',
                color_continuous_scale='Viridis'
            )
            
            fig_bubble.update_layout(
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
                height=500
            )
            
            st.plotly_chart(fig_bubble, use_container_width=True)
            
            # Campaign table
            st.markdown("#### 📋 Top Campaigns")
            
            display_campaign = top_campaigns.copy()
            display_campaign['Revenue'] = display_campaign['Revenue'].apply(lambda x: f'${x:,.0f}')
            display_campaign['Conversion Rate'] = display_campaign['Conversion Rate'].apply(lambda x: f'{x:.2f}%')
            
            st.dataframe(
                display_campaign,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No campaign data available for selected period")
    
    # ==================================================================
    # TREND OVER TIME
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📈 Trends Over Time")
    
    # Daily metrics by channel
    if 'utm_source' in filtered_df.columns:
        daily_channel = filtered_df.groupby(['date', 'utm_source']).agg({
            'session_id': 'count',
            'revenue': 'sum'
        }).reset_index()
        
        daily_channel.columns = ['Date', 'Channel', 'Sessions', 'Revenue']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sessions over time by channel
            fig_sessions = px.line(
                daily_channel,
                x='Date',
                y='Sessions',
                color='Channel',
                title='Daily Sessions by Channel'
            )
            fig_sessions.update_layout(
                hovermode='x unified',
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray')
            )
            st.plotly_chart(fig_sessions, use_container_width=True)
        
        with col2:
            # Revenue over time by channel
            fig_rev_trend = px.line(
                daily_channel,
                x='Date',
                y='Revenue',
                color='Channel',
                title='Daily Revenue by Channel'
            )
            fig_rev_trend.update_layout(
                hovermode='x unified',
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='lightgray'),
                yaxis=dict(showgrid=True, gridcolor='lightgray')
            )
            st.plotly_chart(fig_rev_trend, use_container_width=True)
    
    # ==================================================================
    # DEVICE & PLATFORM BREAKDOWN
    # ==================================================================
    
    st.markdown("---")
    st.markdown("### 📱 Device & Platform Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'platform' in filtered_df.columns:
            # Platform breakdown
            platform_perf = filtered_df.groupby('platform').agg({
                'session_id': 'count',
                'converted': 'sum',
                'revenue': 'sum'
            }).reset_index()
            
            platform_perf.columns = ['Platform', 'Sessions', 'Conversions', 'Revenue']
            
            fig_platform = px.pie(
                platform_perf,
                values='Revenue',
                names='Platform',
                title='Revenue by Platform',
                hole=0.4
            )
            st.plotly_chart(fig_platform, use_container_width=True)
    
    with col2:
        if 'device_type' in filtered_df.columns:
            # Device breakdown (top 5)
            device_perf = filtered_df.groupby('device_type').agg({
                'session_id': 'count',
                'revenue': 'sum'
            }).reset_index()
            
            device_perf.columns = ['Device', 'Sessions', 'Revenue']
            device_perf = device_perf.sort_values('Revenue', ascending=False).head(5)
            
            fig_device = px.bar(
                device_perf,
                x='Device',
                y='Revenue',
                title='Revenue by Device Type (Top 5)',
                color='Revenue',
                color_continuous_scale='Blues'
            )
            fig_device.update_layout(showlegend=False)
            st.plotly_chart(fig_device, use_container_width=True)
    
    # ==================================================================
    # GEOGRAPHIC ANALYSIS
    # ==================================================================
    
    if 'country' in filtered_df.columns:
        st.markdown("---")
        st.markdown("### 🌍 Geographic Performance")
        
        country_perf = filtered_df.groupby('country').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        
        country_perf.columns = ['Country', 'Sessions', 'Conversions', 'Revenue']
        country_perf = country_perf.sort_values('Revenue', ascending=False).head(10)
        
        fig_geo = px.bar(
            country_perf,
            x='Country',
            y=['Revenue', 'Sessions'],
            title='Top 10 Countries by Revenue',
            barmode='group'
        )
        fig_geo.update_layout(
            plot_bgcolor='white',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='lightgray')
        )
        st.plotly_chart(fig_geo, use_container_width=True)
    
    # ==================================================================
    # DOWNLOAD DATA
    # ==================================================================
    
    st.markdown("---")
    
    if st.checkbox("Show raw data"):
        st.dataframe(filtered_df, use_container_width=True)
    
    # Download button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Attribution Data",
        data=csv,
        file_name=f'marketing_attribution_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

else:
    st.error("Unable to load attribution data")
    st.info("Make sure session_attribution.csv exists in the data/ folder")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Marketing Attribution Dashboard | Built with Streamlit</p>
    </div>
""", unsafe_allow_html=True)
