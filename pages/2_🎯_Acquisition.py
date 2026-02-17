"""
ACQUISITION DASHBOARD
=====================
KPI 4: Total Sessions
KPI 5: Sessions by Landing Page
KPI 6: Sessions by Device/Platform
KPI 7: Session Geography
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Acquisition", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    h1 {color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Acquisition Dashboard")
st.markdown("### Traffic sources, channels, and user acquisition")

# Load data
@st.cache_data
def load_data():
    try:
        sessions = pd.read_csv('aggregated_data/session_attribution.csv')
        sessions_raw = pd.read_csv('raw_data/session_table.csv')
        return sessions, sessions_raw
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None

sessions_df, sessions_raw_df = load_data()

if sessions_df is not None:
    sessions_df['date'] = pd.to_datetime(sessions_df['date'])
    
    # DATE FILTER
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=sessions_df['date'].max() - timedelta(days=30),
            min_value=sessions_df['date'].min().date(),
            max_value=sessions_df['date'].max().date()
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=sessions_df['date'].max().date(),
            min_value=sessions_df['date'].min().date(),
            max_value=sessions_df['date'].max().date()
        )
    
    # Filter
    mask = (sessions_df['date'].dt.date >= start_date) & \
           (sessions_df['date'].dt.date <= end_date)
    filtered_df = sessions_df[mask]
    
    # KEY METRICS
    st.markdown("---")
    st.markdown("### 📊 Acquisition KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # KPI 4: Total Sessions
        total_sessions = len(filtered_df)
        st.metric(
            "📱 Total Sessions",
            f"{total_sessions:,}",
            help="Total number of website visits"
        )
    
    with col2:
        # Unique visitors
        unique_users = filtered_df['user_id'].nunique()
        st.metric(
            "👥 Unique Users",
            f"{unique_users:,}",
            f"{total_sessions/unique_users:.1f} sessions/user",
            help="Number of unique visitors"
        )
    
    with col3:
        # Conversion rate
        conversions = filtered_df['converted'].sum()
        conv_rate = (conversions / total_sessions * 100) if total_sessions > 0 else 0
        st.metric(
            "✅ Conversion Rate",
            f"{conv_rate:.2f}%",
            f"{conversions:,} conversions",
            help="Percentage of sessions that resulted in orders"
        )
    
    with col4:
        # Revenue
        total_revenue = filtered_df['revenue'].sum()
        revenue_per_session = total_revenue / total_sessions if total_sessions > 0 else 0
        st.metric(
            "💰 Revenue",
            f"${total_revenue:,.0f}",
            f"${revenue_per_session:.2f}/session",
            help="Total revenue from these sessions"
        )
    
    # TRAFFIC SOURCES
    st.markdown("---")
    st.markdown("### 🌐 Traffic by Source (UTM)")
    
    if 'utm_source' in filtered_df.columns:
        source_data = filtered_df.groupby('utm_source').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        source_data.columns = ['Source', 'Sessions', 'Conversions', 'Revenue']
        source_data['Conversion Rate'] = (source_data['Conversions'] / source_data['Sessions'] * 100).round(2)
        source_data = source_data.sort_values('Revenue', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_source = px.bar(
                source_data,
                x='Source',
                y='Sessions',
                title='Sessions by Traffic Source',
                color='Sessions',
                color_continuous_scale='Blues',
                text='Sessions'
            )
            fig_source.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_source.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_source, use_container_width=True)
        
        with col2:
            fig_rev = px.bar(
                source_data,
                x='Source',
                y='Revenue',
                title='Revenue by Traffic Source',
                color='Revenue',
                color_continuous_scale='Greens',
                text='Revenue'
            )
            fig_rev.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_rev.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_rev, use_container_width=True)
        
        # Source performance table
        st.markdown("#### 📋 Traffic Source Performance")
        display_source = source_data.copy()
        display_source['Revenue'] = display_source['Revenue'].apply(lambda x: f'${x:,.0f}')
        display_source['Conversion Rate'] = display_source['Conversion Rate'].apply(lambda x: f'{x:.2f}%')
        st.dataframe(display_source, use_container_width=True, hide_index=True)
    
    # LANDING PAGES
    st.markdown("---")
    st.markdown("### 📄 KPI 5: Sessions by Landing Page")
    
    if sessions_raw_df is not None and 'landing_page' in sessions_raw_df.columns:
        # Filter raw sessions by date if possible
        if 'time' in sessions_raw_df.columns:
            sessions_raw_df['time'] = pd.to_datetime(sessions_raw_df['time'])
            raw_mask = (sessions_raw_df['time'].dt.date >= start_date) & \
                       (sessions_raw_df['time'].dt.date <= end_date)
            filtered_raw = sessions_raw_df[raw_mask]
        else:
            filtered_raw = sessions_raw_df
        
        landing_data = filtered_raw['landing_page'].value_counts().head(10).reset_index()
        landing_data.columns = ['Landing Page', 'Sessions']
        
        fig_landing = px.bar(
            landing_data,
            x='Landing Page',
            y='Sessions',
            title='Top 10 Landing Pages',
            color='Sessions',
            color_continuous_scale='Viridis'
        )
        fig_landing.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_landing, use_container_width=True)
        
        st.dataframe(landing_data, use_container_width=True, hide_index=True)
    
    # DEVICE & PLATFORM
    st.markdown("---")
    st.markdown("### 📱 KPI 6: Sessions by Device/Platform")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'platform' in filtered_df.columns:
            platform_data = filtered_df['platform'].value_counts().reset_index()
            platform_data.columns = ['Platform', 'Sessions']
            
            fig_platform = px.pie(
                platform_data,
                values='Sessions',
                names='Platform',
                title='Sessions by Platform',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_platform, use_container_width=True)
    
    with col2:
        if 'device_type' in filtered_df.columns:
            device_data = filtered_df['device_type'].value_counts().head(5).reset_index()
            device_data.columns = ['Device', 'Sessions']
            
            fig_device = px.bar(
                device_data,
                x='Device',
                y='Sessions',
                title='Top 5 Devices',
                color='Sessions',
                color_continuous_scale='Blues'
            )
            fig_device.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_device, use_container_width=True)
    
    # Device performance comparison
    if 'platform' in filtered_df.columns:
        platform_perf = filtered_df.groupby('platform').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        platform_perf.columns = ['Platform', 'Sessions', 'Conversions', 'Revenue']
        platform_perf['Conversion Rate'] = (platform_perf['Conversions'] / platform_perf['Sessions'] * 100).round(2)
        platform_perf['Revenue per Session'] = (platform_perf['Revenue'] / platform_perf['Sessions']).round(2)
        
        st.markdown("#### 📊 Platform Performance Comparison")
        display_platform = platform_perf.copy()
        display_platform['Revenue'] = display_platform['Revenue'].apply(lambda x: f'${x:,.0f}')
        display_platform['Conversion Rate'] = display_platform['Conversion Rate'].apply(lambda x: f'{x:.2f}%')
        display_platform['Revenue per Session'] = display_platform['Revenue per Session'].apply(lambda x: f'${x:.2f}')
        st.dataframe(display_platform, use_container_width=True, hide_index=True)
    
    # GEOGRAPHY
    st.markdown("---")
    st.markdown("### 🌍 KPI 7: Session Geography")
    
    if 'country' in filtered_df.columns:
        geo_data = filtered_df.groupby('country').agg({
            'session_id': 'count',
            'converted': 'sum',
            'revenue': 'sum'
        }).reset_index()
        geo_data.columns = ['Country', 'Sessions', 'Conversions', 'Revenue']
        geo_data['Conversion Rate'] = (geo_data['Conversions'] / geo_data['Sessions'] * 100).round(2)
        geo_data = geo_data.sort_values('Revenue', ascending=False).head(10)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_country = px.bar(
                geo_data,
                x='Country',
                y='Sessions',
                title='Top 10 Countries by Sessions',
                color='Sessions',
                color_continuous_scale='Blues'
            )
            fig_country.update_layout(showlegend=False)
            st.plotly_chart(fig_country, use_container_width=True)
        
        with col2:
            fig_geo_rev = px.bar(
                geo_data,
                x='Country',
                y='Revenue',
                title='Top 10 Countries by Revenue',
                color='Revenue',
                color_continuous_scale='Greens'
            )
            fig_geo_rev.update_layout(showlegend=False)
            st.plotly_chart(fig_geo_rev, use_container_width=True)
        
        # Geography table
        st.markdown("#### 📋 Geographic Performance")
        display_geo = geo_data.copy()
        display_geo['Revenue'] = display_geo['Revenue'].apply(lambda x: f'${x:,.0f}')
        display_geo['Conversion Rate'] = display_geo['Conversion Rate'].apply(lambda x: f'{x:.2f}%')
        st.dataframe(display_geo, use_container_width=True, hide_index=True)
    
    # TREND OVER TIME
    st.markdown("---")
    st.markdown("### 📈 Session Trends")
    
    daily_sessions = filtered_df.groupby('date').agg({
        'session_id': 'count',
        'converted': 'sum',
        'revenue': 'sum'
    }).reset_index()
    daily_sessions.columns = ['Date', 'Sessions', 'Conversions', 'Revenue']
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=daily_sessions['Date'],
        y=daily_sessions['Sessions'],
        name='Sessions',
        line=dict(color='#636EFA', width=2)
    ))
    fig_trend.add_trace(go.Scatter(
        x=daily_sessions['Date'],
        y=daily_sessions['Conversions'],
        name='Conversions',
        line=dict(color='#EF553B', width=2),
        yaxis='y2'
    ))
    
    fig_trend.update_layout(
        title='Sessions & Conversions Over Time',
        hovermode='x unified',
        yaxis=dict(title='Sessions'),
        yaxis2=dict(title='Conversions', overlaying='y', side='right'),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # KEY INSIGHTS
    st.markdown("---")
    st.markdown("### 💡 Key Insights")
    
    if 'utm_source' in filtered_df.columns:
        top_source = source_data.iloc[0]
        worst_source = source_data[source_data['Sessions'] > 50].nsmallest(1, 'Conversion Rate').iloc[0] if len(source_data) > 1 else None
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"""
            **Top Performing Channel:**
            - **{top_source['Source']}** drives ${top_source['Revenue']:,.0f} revenue
            - {top_source['Sessions']:,} sessions
            - {top_source['Conversion Rate']:.2f}% conversion rate
            """)
        
        with col2:
            if worst_source is not None:
                st.warning(f"""
                **Needs Improvement:**
                - **{worst_source['Source']}** has low conversion ({worst_source['Conversion Rate']:.2f}%)
                - {worst_source['Sessions']:,} sessions but only {worst_source['Conversions']} conversions
                - Review targeting and landing page quality
                """)

else:
    st.error("Unable to load session data")
    st.info("Make sure session_attribution.csv exists")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>Acquisition Dashboard</p></div>", unsafe_allow_html=True)
