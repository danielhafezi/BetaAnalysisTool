import streamlit as st
from datetime import datetime, timezone, timedelta
from src.data_fetcher import DataFetcher
from src.beta_calculator import calculate_all_betas, create_beta_charts, analyze_beta_patterns
import plotly.graph_objects as go
import pandas as pd

# Set page config for wider layout
st.set_page_config(page_title="Crypto Beta Calculator", layout="wide")

# Initialize DataFetcher
@st.cache_resource
def get_data_fetcher():
    return DataFetcher()

data_fetcher = get_data_fetcher()

# Initialize session state for end time
if 'end_time' not in st.session_state:
    st.session_state.end_time = "23:59"
if 'pattern_end_time' not in st.session_state:
    st.session_state.pattern_end_time = "23:59"
if 'pattern_end_time_default' not in st.session_state:
    st.session_state.pattern_end_time_default = "23:59"

def set_pattern_time_to_now():
    current_time = datetime.now(timezone.utc)
    st.session_state.pattern_end_time_default = current_time.strftime("%H:%M")

# Create tabs
tab1, tab2 = st.tabs(["Market Beta Analysis", "Beta Pattern Analysis"])

with tab1:
    st.title("Hyperliquid Perpetual Futures Beta Calculator")

    # Custom CSS for wider tables and layout
    st.markdown("""
        <style>
            .stDataFrame {
                width: 100%;
            }
            .dataframe {
                width: 100% !important;
            }
            div[data-testid="stHorizontalBlock"] > div {
                width: 100% !important;
            }
            [data-testid="column"] {
                width: calc(100% - 200px) !important;
            }
            [data-testid="column"] + [data-testid="column"] {
                width: 200px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state for end time
    if 'end_time' not in st.session_state:
        st.session_state.end_time = "23:59"

    # Date and Time input
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now(timezone.utc).date() - timedelta(days=1)
        )
        # Manual time input for start
        start_time_str = st.text_input(
            "Start Time", 
            "00:00",
            help="Enter time in 24-hour format"
        )
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            st.error("Please enter time in HH:MM format")
            start_time = datetime.strptime("00:00", "%H:%M").time()
    
    with col2:
        end_date = st.date_input("End Date", datetime.now(timezone.utc).date())
        
        # Create two columns for end time input and "Set to Now" button
        end_time_col, now_button_col = st.columns([3, 1])
        
        with end_time_col:
            # Manual time input for end
            end_time_str = st.text_input(
                "End Time", 
                st.session_state.end_time,
                key="end_time_input",
                help="Enter time in 24-hour format"
            )
            try:
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
            except ValueError:
                st.error("Please enter time in HH:MM format")
                end_time = datetime.strptime("23:59", "%H:%M").time()
        
        with now_button_col:
            # Add some spacing to align with the input box
            st.write("")
            st.write("")
            if st.button("Set to Now"):
                current_time = datetime.now(timezone.utc)
                st.session_state.end_time = current_time.strftime("%H:%M")
                st.rerun()

    if st.button("Calculate Betas"):
        start_dt = datetime.combine(start_date, start_time, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, end_time, tzinfo=timezone.utc)
        
        # Get valid pairs first to show progress
        valid_pairs = data_fetcher.get_valid_pairs()
        total_pairs = len(valid_pairs)
        
        if total_pairs > 0:
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create placeholder for the results
            results_placeholder = st.empty()
            
            # Calculate betas for all hours first
            btc_betas_df, eth_betas_df = calculate_all_betas(
                data_fetcher,
                int(start_dt.timestamp()),
                int(end_dt.timestamp()),
                progress_callback=lambda i: (
                    progress_bar.progress(i / total_pairs),
                    status_text.text(f"Processing pair {i}/{total_pairs}")
                )
            )
            
            if btc_betas_df is not None and eth_betas_df is not None:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Add session selector after results are calculated
                session = st.selectbox(
                    "Filter by Trading Session",
                    ["None", "US", "EU", "APAC"],
                    help="""
                    Filter data by trading sessions:
                    - None: All hours
                    - US: 13:30-20:00 UTC (9:30 AM - 4:00 PM ET)
                    - EU: 07:00-15:30 UTC (8:00 AM - 4:30 PM CET)
                    - APAC: 00:00-07:00 UTC (9:00 AM - 4:00 PM JST)
                    """
                )
                
                # If session is selected, filter the results
                if session != "None":
                    filtered_btc_df, filtered_eth_df = filter_results_by_session(
                        btc_betas_df, eth_betas_df, 
                        data_fetcher, 
                        int(start_dt.timestamp()), 
                        int(end_dt.timestamp()),
                        session
                    )
                else:
                    filtered_btc_df, filtered_eth_df = btc_betas_df, eth_betas_df
                
                # Show beta distribution charts
                st.subheader("Beta Distributions")
                figs = create_beta_charts(filtered_btc_df, filtered_eth_df)
                for fig in figs:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Show results in a row
                st.subheader("Results")
                col1, col2 = st.columns([0.8, 0.2])
                
                with col1:
                    st.dataframe(
                        filtered_btc_df,
                        use_container_width=True,
                        height=400
                    )
                    
                with col2:
                    st.markdown("##### Risk Level Distribution")
                    st.dataframe(
                        filtered_btc_df['Risk Level'].value_counts(),
                        use_container_width=True,
                        height=150
                    )
                    
                # Download button
                csv = filtered_btc_df.to_csv()
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f'hyperliquid_betas_{start_dt.strftime("%Y%m%d_%H%M")}_{session}.csv',
                    mime='text/csv'
                )

with tab2:
    st.title("Beta Pattern Analysis")
    st.write("Analyze when specific coins have their highest beta relative to BTC")
    
    # Create two columns for coin selection
    select_col1, select_col2 = st.columns(2)
    
    with select_col1:
        # Get valid pairs for selection
        valid_pairs = data_fetcher.get_valid_pairs()
        
        # First coin selection
        selected_coin = st.selectbox(
            "Select First Coin",
            options=valid_pairs,
            index=valid_pairs.index('ETH') if 'ETH' in valid_pairs else 0,
            key="first_coin"
        )
    
    with select_col2:
        # Second coin selection (optional)
        compare_coin = st.selectbox(
            "Select Second Coin (Optional)",
            options=['None'] + valid_pairs,
            index=0,
            key="second_coin"
        )
    
    # Date and Time input
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now(timezone.utc).date() - timedelta(days=7),
            key="pattern_start_date"
        )
        start_time_str = st.text_input(
            "Start Time", 
            "00:00",
            key="pattern_start_time",
            help="Enter time in 24-hour format"
        )
        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            st.error("Please enter time in HH:MM format")
            start_time = datetime.strptime("00:00", "%H:%M").time()
    
    with col2:
        end_date = st.date_input(
            "End Date", 
            datetime.now(timezone.utc).date(),
            key="pattern_end_date"
        )
        
        # Create two columns for end time input and "Set to Now" button
        end_time_col, now_button_col = st.columns([3, 1])
        
        with end_time_col:
            # Manual time input for end using value directly instead of session state
            end_time_str = st.text_input(
                "End Time", 
                value="23:59" if 'pattern_end_time_default' not in st.session_state else st.session_state.pattern_end_time_default,
                key="pattern_end_time",
                help="Enter time in 24-hour format"
            )
            try:
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
            except ValueError:
                st.error("Please enter time in HH:MM format")
                end_time = datetime.strptime("23:59", "%H:%M").time()
        
        with now_button_col:
            # Add some spacing to align with the input box
            st.write("")
            st.write("")
            st.button("Set to Now", key="pattern_set_to_now", on_click=set_pattern_time_to_now)
    
    if st.button("Analyze Beta Patterns"):
        start_dt = datetime.combine(start_date, start_time, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, end_time, tzinfo=timezone.utc)
        
        # Analyze first coin (with all hours)
        with st.spinner(f"Analyzing beta patterns for {selected_coin}..."):
            results = analyze_beta_patterns(
                data_fetcher,
                selected_coin,
                int(start_dt.timestamp()),
                int(end_dt.timestamp())
            )
            
            # If comparison coin is selected, analyze it too
            compare_results = None
            if compare_coin != 'None':
                with st.spinner(f"Analyzing beta patterns for {compare_coin}..."):
                    compare_results = analyze_beta_patterns(
                        data_fetcher,
                        compare_coin,
                        int(start_dt.timestamp()),
                        int(end_dt.timestamp())
                    )
            
            if results is not None:
                # Add session selector after results
                session = st.selectbox(
                    "Filter by Trading Session",
                    ["None", "US", "EU", "APAC"],
                    help="""
                    Filter data by trading sessions:
                    - None: All hours
                    - US: 13:30-20:00 UTC (9:30 AM - 4:00 PM ET)
                    - EU: 07:00-15:30 UTC (8:00 AM - 4:30 PM CET)
                    - APAC: 00:00-07:00 UTC (9:00 AM - 4:00 PM JST)
                    """,
                    key="pattern_session"
                )
                
                # Filter results if session is selected
                if session != "None":
                    filtered_results = filter_patterns_by_session(
                        results, data_fetcher, selected_coin,
                        int(start_dt.timestamp()), int(end_dt.timestamp()),
                        session
                    )
                    if compare_results is not None:
                        filtered_compare = filter_patterns_by_session(
                            compare_results, data_fetcher, compare_coin,
                            int(start_dt.timestamp()), int(end_dt.timestamp()),
                            session
                        )
                    else:
                        filtered_compare = None
                else:
                    filtered_results = results
                    filtered_compare = compare_results
                
                # Create beta time series chart
                st.subheader(f"Beta Analysis for {selected_coin}" + (f" vs {compare_coin}" if filtered_compare else ""))
                st.write("""
                This chart shows how the coin's beta relative to BTC changes over time.
                - Beta > 1: The coin tends to move more extremely than BTC
                - Beta < 1: The coin tends to move less extremely than BTC
                - Beta = 1: The coin moves similarly to BTC
                """)
                
                # Create the beta time series chart
                beta_fig = go.Figure()
                
                # Add first coin's beta line
                beta_fig.add_trace(go.Scatter(
                    x=filtered_results['beta_series'].index,
                    y=filtered_results['beta_series']['beta'],
                    name=f'{selected_coin} Beta',
                    line=dict(color='blue', width=1),
                    hovertemplate="<b>%{x|%Y-%m-%d %H:%M:%S}</b><br>" +
                                "<b>Beta:</b> %{y:.3f}<br>" +
                                "<extra></extra>"
                ))
                
                # Add comparison coin's beta line if selected
                if filtered_compare is not None:
                    beta_fig.add_trace(go.Scatter(
                        x=filtered_compare['beta_series'].index,
                        y=filtered_compare['beta_series']['beta'],
                        name=f'{compare_coin} Beta',
                        line=dict(color='red', width=1),
                        hovertemplate="<b>%{x|%Y-%m-%d %H:%M:%S}</b><br>" +
                                    "<b>Beta:</b> %{y:.3f}<br>" +
                                    "<extra></extra>"
                    ))
                
                # Add reference line for beta = 1
                beta_fig.add_hline(
                    y=1,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="β = 1",
                    annotation_position="bottom right"
                )
                
                # Ensure the x-axis shows the complete requested time range
                beta_fig.update_layout(
                    title=f"Beta Values Over Time",
                    xaxis_title="Time",
                    yaxis_title="Beta Value",
                    xaxis=dict(
                        range=[start_dt, end_dt],
                        rangeslider=dict(visible=True)
                    ),
                    hovermode='x unified',
                    showlegend=True,
                    template="plotly_white",
                    height=500
                )
                
                st.plotly_chart(beta_fig, use_container_width=True)
                
                # Display hourly and daily charts
                col1, col2 = st.columns(2)
                
                with col1:
                    hourly_fig = go.Figure()
                    current_hour = datetime.now(timezone.utc).hour
                    
                    # Add first coin's hourly data with conditional colors
                    hourly_colors = ['red' if h == current_hour else 'blue' for h in range(24)]
                    hourly_fig.add_trace(go.Bar(
                        x=[f"{h:02d}:00-{(h+1):02d}:00" for h in range(24)],
                        y=filtered_results['hourly_beta'].values,
                        name=selected_coin,
                        marker_color=hourly_colors
                    ))
                    # Add comparison coin's hourly data if selected
                    if filtered_compare is not None:
                        compare_hourly_colors = ['red' if h == current_hour else 'orange' for h in range(24)]
                        hourly_fig.add_trace(go.Bar(
                            x=[f"{h:02d}:00-{(h+1):02d}:00" for h in range(24)],
                            y=filtered_compare['hourly_beta'].values,
                            name=compare_coin,
                            marker_color=compare_hourly_colors
                        ))
                    
                    hourly_fig.update_layout(
                        title=f"Average Beta by Hour (UTC)",
                        xaxis_title="Hour of Day",
                        yaxis_title="Average Beta",
                        template="plotly_white",
                        barmode='group',
                        xaxis=dict(
                            tickangle=45,
                            tickmode='array',
                            ticktext=[f"{h:02d}:00-{(h+1):02d}:00" for h in range(24)],
                            tickvals=list(range(24))
                        )
                    )
                    st.plotly_chart(hourly_fig, use_container_width=True)
                
                with col2:
                    daily_fig = go.Figure()
                    current_day = datetime.now(timezone.utc).weekday()
                    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    # Add first coin's daily data with conditional colors
                    daily_colors = ['red' if i == current_day else 'blue' for i in range(7)]
                    daily_fig.add_trace(go.Bar(
                        x=filtered_results['daily_beta'].index,
                        y=filtered_results['daily_beta'].values,
                        name=selected_coin,
                        marker_color=daily_colors
                    ))
                    # Add comparison coin's daily data if selected
                    if filtered_compare is not None:
                        compare_daily_colors = ['red' if i == current_day else 'orange' for i in range(7)]
                        daily_fig.add_trace(go.Bar(
                            x=filtered_compare['daily_beta'].index,
                            y=filtered_compare['daily_beta'].values,
                            name=compare_coin,
                            marker_color=compare_daily_colors
                        ))
                    
                    daily_fig.update_layout(
                        title=f"Average Beta by Day of Week",
                        xaxis_title="Day of Week",
                        yaxis_title="Average Beta",
                        template="plotly_white",
                        barmode='group'
                    )
                    st.plotly_chart(daily_fig, use_container_width=True)
                
                # Add current beta information
                if filtered_results.get('current_window'):
                    current_beta = filtered_results['current_window'].get('beta')
                    if current_beta is not None:
                        st.info(f"Current Beta (as of {filtered_results['current_window']['day']} "
                               f"{filtered_results['current_window']['time']} UTC): "
                               f"{current_beta} (based on {filtered_results['current_window']['samples']} samples)")
                
                # Add download buttons for the data
                col1, col2 = st.columns(2)
                with col1:
                    csv = filtered_results['beta_series'].to_csv()
                    st.download_button(
                        label=f"Download {selected_coin} Beta Data",
                        data=csv,
                        file_name=f'{selected_coin}_beta_data_{start_dt.strftime("%Y%m%d_%H%M")}.csv',
                        mime='text/csv'
                    )
                
                if filtered_compare is not None:
                    with col2:
                        csv = filtered_compare['beta_series'].to_csv()
                        st.download_button(
                            label=f"Download {compare_coin} Beta Data",
                            data=csv,
                            file_name=f'{compare_coin}_beta_data_{start_dt.strftime("%Y%m%d_%H%M")}.csv',
                            mime='text/csv'
                        )
                
                # Add Beta Pattern Tables
                st.subheader("Beta Pattern Analysis")
                col1, col2 = st.columns(2)
                
                # Get current day and time for highlighting
                current_day = datetime.now(timezone.utc).strftime("%A")
                current_hour = datetime.now(timezone.utc).hour
                current_time_window = f"{current_hour:02d}:00-{(current_hour+1):02d}:00"

                # Custom CSS for highlighting the current time window
                st.markdown("""
                    <style>
                    .highlight {
                        background-color: #ff0000 !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                with col1:
                    st.markdown("#### Highest Beta Time Windows")
                    high_beta_df = pd.DataFrame(filtered_results['highest_beta'])
                    # Reorder columns to show rank first
                    high_beta_df = high_beta_df[['rank', 'day', 'time', 'beta', 'samples']]
                    
                    # Add a boolean column for highlighting
                    high_beta_df['highlight'] = (high_beta_df['day'] == current_day) & (high_beta_df['time'] == current_time_window)
                    
                    # Apply styling with more prominent red
                    styled_high_beta = high_beta_df.style.apply(
                        lambda x: ['background-color: #ff0000' if x['highlight'] else '' for _ in x],
                        axis=1
                    )
                    
                    st.dataframe(
                        styled_high_beta,
                        use_container_width=True,
                        height=400
                    )
                
                with col2:
                    st.markdown("#### Lowest Beta Time Windows")
                    low_beta_df = pd.DataFrame(filtered_results['lowest_beta'])
                    # Reorder columns to show rank first
                    low_beta_df = low_beta_df[['rank', 'day', 'time', 'beta', 'samples']]
                    
                    # Add a boolean column for highlighting
                    low_beta_df['highlight'] = (low_beta_df['day'] == current_day) & (low_beta_df['time'] == current_time_window)
                    
                    # Apply styling with more prominent red
                    styled_low_beta = low_beta_df.style.apply(
                        lambda x: ['background-color: #ff0000' if x['highlight'] else '' for _ in x],
                        axis=1
                    )
                    
                    st.dataframe(
                        styled_low_beta,
                        use_container_width=True,
                        height=400
                    )
            else:
                st.error("Failed to analyze beta patterns. Please try a different time range or coin.")
