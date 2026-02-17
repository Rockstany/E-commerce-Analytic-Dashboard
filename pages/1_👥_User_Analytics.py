"""
USER ANALYTICS DASHBOARD
========================
KPI 1: Active Users
KPI 2: Returning Users  
KPI 3: Repeat Purchasers
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="User Analytics", page_icon="👥", layout="wide")

st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    h1 {color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("👥 User Analytics Dashboard")
st.markdown("### Track user engagement, retention, and loyalty")

# Load data
@st.cache_data
def load_data():
    try:
        users = pd.read_csv('raw_data/user_table.csv')
        sessions = pd.read_csv('aggregated_data/session_attribution.csv')
        user_metrics = pd.read_csv('aggregated_data/user_lifetime_metrics.csv')
        return users, sessions, user_metrics
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None, None

users_df, sessions_df, user_metrics_df = load_data()

if users_df is not None and sessions_df is not None:
    
    # Convert dates
    if 'date' in sessions_df.columns:
        sessions_df['date'] = pd.to_datetime(sessions_df['date'])
    
    # DATE FILTER
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if 'date' in sessions_df.columns:
            start_date = st.date_input(
                "Start Date",
                value=sessions_df['date'].max() - timedelta(days=30),
                min_value=sessions_df['date'].min().date(),
                max_value=sessions_df['date'].max().date()
            )
    
    with col2:
        if 'date' in sessions_df.columns:
            end_date = st.date_input(
                "End Date",
                value=sessions_df['date'].max().date(),
                min_value=sessions_df['date'].min().date(),
                max_value=sessions_df['date'].max().date()
            )
    
    # Filter sessions
    if 'date' in sessions_df.columns:
        mask = (sessions_df['date'].dt.date >= start_date) & \
               (sessions_df['date'].dt.date <= end_date)
        filtered_sessions = sessions_df[mask]
    else:
        filtered_sessions = sessions_df
    
    # KEY USER METRICS
    st.markdown("---")
    st.markdown("### 📊 User KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # KPI 1: Active Users (unique users in period)
        active_users = filtered_sessions['user_id'].nunique()
        st.metric(
            "🟢 Active Users",
            f"{active_users:,}",
            help="Total unique users who visited in selected period"
        )
    
    with col2:
        # KPI 2: Returning Users
        user_session_counts = filtered_sessions.groupby('user_id').size()
        returning_users = (user_session_counts > 1).sum()
        returning_rate = (returning_users / active_users * 100) if active_users > 0 else 0
        
        st.metric(
            "🔄 Returning Users",
            f"{returning_users:,}",
            f"{returning_rate:.1f}% of total",
            help="Users who came back more than once"
        )
    
    with col3:
        # KPI 3: Repeat Purchasers (from user_table)
        total_users = len(users_df)
        purchased_last_year = users_df['has_purchase_last_year'].sum()
        purchased_last_qtr = users_df['has_purchase_last_qtr'].sum()
        
        st.metric(
            "🛒 Purchasers (Last Year)",
            f"{purchased_last_year:,}",
            f"{purchased_last_year/total_users*100:.1f}% of all users",
            help="Users who purchased in last 12 months"
        )
    
    with col4:
        st.metric(
            "🛒 Purchasers (Last Qtr)",
            f"{purchased_last_qtr:,}",
            f"{purchased_last_qtr/total_users*100:.1f}% of all users",
            help="Users who purchased in last 3 months"
        )
    
    # USER FUNNEL
    st.markdown("---")
    st.markdown("### 🔽 User Engagement Funnel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Funnel visualization
        new_users = active_users - returning_users
        
        fig_funnel = go.Figure(go.Funnel(
            y=['Total Users in System', 'Active Users (Period)', 'Returning Users', 'Purchased Last Year', 'Purchased Last Qtr'],
            x=[total_users, active_users, returning_users, purchased_last_year, purchased_last_qtr],
            textinfo="value+percent initial",
            marker=dict(color=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'])
        ))
        fig_funnel.update_layout(height=400, title="User Engagement Levels")
        st.plotly_chart(fig_funnel, use_container_width=True)
    
    with col2:
        # User type breakdown
        user_types_data = pd.DataFrame({
            'Type': ['New Users', 'Returning Users'],
            'Count': [new_users, returning_users]
        })
        
        fig_pie = px.pie(
            user_types_data,
            values='Count',
            names='Type',
            title='New vs Returning Users',
            color_discrete_sequence=['#636EFA', '#EF553B'],
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # DAILY ACTIVE USERS TREND
    if 'date' in filtered_sessions.columns:
        st.markdown("---")
        st.markdown("### 📈 Daily Active Users Trend")
        
        daily_users = filtered_sessions.groupby('date')['user_id'].nunique().reset_index()
        daily_users.columns = ['Date', 'Active Users']
        
        fig_trend = px.line(
            daily_users,
            x='Date',
            y='Active Users',
            title='Daily Active Users Over Time',
            markers=True
        )
        fig_trend.update_traces(line_color='#1f77b4', line_width=2)
        fig_trend.update_layout(hovermode='x unified', plot_bgcolor='white')
        st.plotly_chart(fig_trend, use_container_width=True)
    
    # USER LIFETIME VALUE ANALYSIS
    if user_metrics_df is not None:
        st.markdown("---")
        st.markdown("### 💎 User Lifetime Value Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Revenue distribution
            fig_hist = px.histogram(
                user_metrics_df,
                x='total_revenue',
                nbins=50,
                title='User Revenue Distribution',
                labels={'total_revenue': 'Total Revenue ($)', 'count': 'Number of Users'}
            )
            fig_hist.update_layout(showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Orders distribution
            fig_orders = px.histogram(
                user_metrics_df,
                x='total_orders',
                nbins=30,
                title='User Order Frequency Distribution',
                labels={'total_orders': 'Total Orders', 'count': 'Number of Users'}
            )
            fig_orders.update_layout(showlegend=False)
            st.plotly_chart(fig_orders, use_container_width=True)
        
        # RFM Segment Analysis
        if 'rfm_segment' in user_metrics_df.columns:
            st.markdown("---")
            st.markdown("### 🎯 Customer Segmentation (RFM)")
            
            segment_counts = user_metrics_df['rfm_segment'].value_counts().reset_index()
            segment_counts.columns = ['Segment', 'Users']
            
            segment_revenue = user_metrics_df.groupby('rfm_segment')['total_revenue'].sum().reset_index()
            segment_counts = segment_counts.merge(segment_revenue, left_on='Segment', right_on='rfm_segment', how='left')
            segment_counts = segment_counts[['Segment', 'Users', 'total_revenue']]
            segment_counts.columns = ['Segment', 'Users', 'Total Revenue']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_seg = px.bar(
                    segment_counts,
                    x='Segment',
                    y='Users',
                    title='Users by Segment',
                    color='Users',
                    color_continuous_scale='Blues'
                )
                fig_seg.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_seg, use_container_width=True)
            
            with col2:
                fig_rev = px.bar(
                    segment_counts,
                    x='Segment',
                    y='Total Revenue',
                    title='Revenue by Segment',
                    color='Total Revenue',
                    color_continuous_scale='Greens'
                )
                fig_rev.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_rev, use_container_width=True)
            
            # Segment table
            st.markdown("#### 📋 Segment Details")
            segment_counts['Avg Revenue per User'] = segment_counts['Total Revenue'] / segment_counts['Users']
            segment_counts['Total Revenue'] = segment_counts['Total Revenue'].apply(lambda x: f"${x:,.0f}")
            segment_counts['Avg Revenue per User'] = segment_counts['Avg Revenue per User'].apply(lambda x: f"${x:,.0f}")
            
            st.dataframe(segment_counts, use_container_width=True, hide_index=True)
    
    # KEY INSIGHTS
    st.markdown("---")
    st.markdown("### 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **User Engagement:**
        - {active_users:,} active users in selected period
        - {returning_rate:.1f}% are returning visitors
        - Returning users show {returning_users:,} repeat visits
        """)
    
    with col2:
        st.success(f"""
        **Purchase Behavior:**
        - {purchased_last_year:,} users purchased in last year ({purchased_last_year/total_users*100:.1f}%)
        - {purchased_last_qtr:,} recent purchasers ({purchased_last_qtr/total_users*100:.1f}%)
        - Focus on converting {active_users - purchased_last_qtr:,} active non-purchasers
        """)

else:
    st.error("Unable to load user data")
    st.info("Make sure user_table.csv and session_attribution.csv files exist")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'><p>User Analytics Dashboard</p></div>", unsafe_allow_html=True)
