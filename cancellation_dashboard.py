import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Cancellation Report Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric > div {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Load and preprocess data
@st.cache_data
def load_data():
    df = pd.read_csv('Cancellation_Report__May.csv')
    
    # Clean data
    df['Modified Item'] = df['Modified Item'].str.strip()
    df['Modify Reason'] = df['Modify Reason'].str.strip()
    df['Order Entered By'] = df['Order Entered By'].str.strip()
    df['Who?'] = df['Who?'].str.strip()
    
    # Drop duplicates
    df = df.drop_duplicates(subset=['Order Number', 'Modified Item'], keep='first').copy()
    
    # Convert datetime
    df['Order Time'] = pd.to_datetime(df['Order Time'], format='%d-%b-%Y %I:%M %p')
    df['When?'] = pd.to_datetime(df['When?'], format='%d-%b-%Y %I:%M %p')
    
    # Add analysis columns
    df['Cancel_Date'] = df['When?'].dt.date
    df['Cancel_Hour'] = df['When?'].dt.hour
    df['Cancel_Day'] = df['When?'].dt.day_name()
    df['Time_Period'] = df['Cancel_Hour'].apply(lambda x: 
        'Morning (6-12)' if 6 <= x < 12 else
        'Afternoon (12-18)' if 12 <= x < 18 else
        'Evening (18-24)' if 18 <= x < 24 else
        'Late Night (0-6)')
    df['Time_to_Cancel_Min'] = (df['When?'] - df['Order Time']).dt.total_seconds() / 60
    
    return df

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Date range filter
min_date = df['Cancel_Date'].min()
max_date = df['Cancel_Date'].max()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Reason filter
all_reasons = ['All'] + sorted(df['Modify Reason'].unique().tolist())
selected_reason = st.sidebar.selectbox("Modify Reason", all_reasons)

# Staff filter
all_staff = ['All'] + sorted(df['Order Entered By'].unique().tolist())
selected_staff = st.sidebar.selectbox("Staff Member", all_staff)

# Time period filter
all_periods = ['All'] + df['Time_Period'].unique().tolist()
selected_period = st.sidebar.selectbox("Time Period", all_periods)

# Apply filters
filtered_df = df.copy()

if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df['Cancel_Date'] >= date_range[0]) & 
        (filtered_df['Cancel_Date'] <= date_range[1])
    ]

if selected_reason != 'All':
    filtered_df = filtered_df[filtered_df['Modify Reason'] == selected_reason]

if selected_staff != 'All':
    filtered_df = filtered_df[filtered_df['Order Entered By'] == selected_staff]

if selected_period != 'All':
    filtered_df = filtered_df[filtered_df['Time_Period'] == selected_period]

# Main title
st.title("📊 Cancellation Report Dashboard - May 2025")
st.markdown("---")

# KPI Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="Total Cancellations",
        value=f"{len(filtered_df):,}",
        delta=f"{len(filtered_df) - len(df)} from total" if len(filtered_df) != len(df) else None
    )

with col2:
    st.metric(
        label="Total Amount (SAR)",
        value=f"{filtered_df['Reduced Amount'].sum():,.2f}"
    )

with col3:
    st.metric(
        label="Avg Amount/Cancel",
        value=f"{filtered_df['Reduced Amount'].mean():,.2f}"
    )

with col4:
    st.metric(
        label="Unique Staff",
        value=f"{filtered_df['Order Entered By'].nunique()}"
    )

with col5:
    st.metric(
        label="Avg Time to Cancel",
        value=f"{filtered_df['Time_to_Cancel_Min'].mean():.0f} min"
    )

st.markdown("---")

# Row 1: Reason Analysis
st.subheader("📋 Cancellation Reasons Analysis")
col1, col2 = st.columns(2)

with col1:
    reason_data = filtered_df.groupby('Modify Reason').agg(
        Count=('Modify Reason', 'count'),
        Total_Amount=('Reduced Amount', 'sum')
    ).reset_index().sort_values('Total_Amount', ascending=True)
    
    fig_reason = px.bar(
        reason_data,
        x='Total_Amount',
        y='Modify Reason',
        orientation='h',
        title='Cancellation Amount by Reason',
        color='Total_Amount',
        color_continuous_scale='Reds'
    )
    fig_reason.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig_reason, use_container_width=True)

with col2:
    reason_count = filtered_df.groupby('Modify Reason').size().reset_index(name='Count')
    fig_reason_pie = px.pie(
        reason_count,
        values='Count',
        names='Modify Reason',
        title='Cancellation Distribution by Reason',
        hole=0.4
    )
    fig_reason_pie.update_layout(height=400)
    st.plotly_chart(fig_reason_pie, use_container_width=True)

st.markdown("---")

# Row 2: Staff Analysis
st.subheader("👥 Staff Performance Analysis")
col1, col2 = st.columns(2)

with col1:
    staff_data = filtered_df.groupby('Order Entered By').agg(
        Cancellations=('Order Number', 'count'),
        Total_Amount=('Reduced Amount', 'sum')
    ).reset_index().sort_values('Cancellations', ascending=False)
    
    fig_staff = px.bar(
        staff_data,
        x='Order Entered By',
        y='Cancellations',
        title='Cancellations by Staff Member',
        color='Total_Amount',
        color_continuous_scale='Blues'
    )
    fig_staff.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_staff, use_container_width=True)

with col2:
    # Staff vs Reason heatmap
    staff_reason = pd.crosstab(filtered_df['Order Entered By'], filtered_df['Modify Reason'])
    
    fig_heatmap = px.imshow(
        staff_reason,
        title='Staff vs Reason Heatmap',
        color_continuous_scale='YlOrRd',
        aspect='auto'
    )
    fig_heatmap.update_layout(height=400)
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# Row 3: Time Analysis
st.subheader("🕐 Time Analysis")
col1, col2 = st.columns(2)

with col1:
    hourly_data = filtered_df.groupby('Cancel_Hour').size().reset_index(name='Cancellations')
    
    fig_hourly = px.bar(
        hourly_data,
        x='Cancel_Hour',
        y='Cancellations',
        title='Cancellations by Hour of Day',
        color='Cancellations',
        color_continuous_scale='Viridis'
    )
    fig_hourly.update_layout(height=400, xaxis=dict(tickmode='linear', dtick=2))
    st.plotly_chart(fig_hourly, use_container_width=True)

with col2:
    period_data = filtered_df.groupby('Time_Period').agg(
        Cancellations=('Order Number', 'count'),
        Amount=('Reduced Amount', 'sum')
    ).reset_index()
    
    fig_period = px.pie(
        period_data,
        values='Cancellations',
        names='Time_Period',
        title='Cancellations by Time Period',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_period.update_layout(height=400)
    st.plotly_chart(fig_period, use_container_width=True)

st.markdown("---")

# Row 4: Daily Trend and Items
st.subheader("📈 Trends & Top Items")
col1, col2 = st.columns(2)

with col1:
    daily_data = filtered_df.groupby('Cancel_Date').agg(
        Cancellations=('Order Number', 'count'),
        Amount=('Reduced Amount', 'sum')
    ).reset_index()
    
    fig_daily = go.Figure()
    fig_daily.add_trace(go.Scatter(
        x=daily_data['Cancel_Date'],
        y=daily_data['Cancellations'],
        mode='lines+markers',
        name='Cancellations',
        line=dict(color='#667eea', width=2),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))
    fig_daily.update_layout(
        title='Daily Cancellation Trend',
        height=400,
        xaxis_title='Date',
        yaxis_title='Cancellations'
    )
    st.plotly_chart(fig_daily, use_container_width=True)

with col2:
    item_data = filtered_df[filtered_df['Modified Item'] != '.'].groupby('Modified Item').agg(
        Times_Cancelled=('Modified Item', 'count'),
        Total_Amount=('Reduced Amount', 'sum')
    ).reset_index().sort_values('Times_Cancelled', ascending=False).head(10)
    
    fig_items = px.bar(
        item_data,
        x='Times_Cancelled',
        y='Modified Item',
        orientation='h',
        title='Top 10 Most Cancelled Items',
        color='Total_Amount',
        color_continuous_scale='Teal'
    )
    fig_items.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_items, use_container_width=True)

st.markdown("---")

# Data Tables Section
st.subheader("📋 Detailed Data")

tab1, tab2, tab3 = st.tabs(["Reason Summary", "Staff Summary", "Raw Data"])

with tab1:
    reason_summary = filtered_df.groupby('Modify Reason').agg(
        Count=('Modify Reason', 'count'),
        Total_Amount=('Reduced Amount', 'sum'),
        Avg_Amount=('Reduced Amount', 'mean')
    ).reset_index().sort_values('Total_Amount', ascending=False)
    reason_summary['Percentage'] = (reason_summary['Total_Amount'] / reason_summary['Total_Amount'].sum() * 100).round(2)
    st.dataframe(reason_summary, use_container_width=True, hide_index=True)

with tab2:
    staff_summary = filtered_df.groupby('Order Entered By').agg(
        Total_Cancellations=('Order Number', 'count'),
        Total_Amount=('Reduced Amount', 'sum'),
        Avg_Amount=('Reduced Amount', 'mean')
    ).reset_index().sort_values('Total_Cancellations', ascending=False)
    st.dataframe(staff_summary, use_container_width=True, hide_index=True)

with tab3:
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# Download section
st.markdown("---")
st.subheader("📥 Download Data")

col1, col2 = st.columns(2)

with col1:
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Filtered Data (CSV)",
        data=csv,
        file_name="filtered_cancellation_data.csv",
        mime="text/csv"
    )

with col2:
    full_csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Data (CSV)",
        data=full_csv,
        file_name="full_cancellation_data.csv",
        mime="text/csv"
    )

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Dashboard created for Cancellation Analysis | Data: May 2025"
    "</div>",
    unsafe_allow_html=True
)
