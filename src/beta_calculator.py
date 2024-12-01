import pandas as pd
import numpy as np
import plotly.graph_objects as go

def filter_by_session(df, session):
    """Filter DataFrame by trading session hours."""
    if session == "None" or session is None:
        return df
        
    # Convert index to UTC
    df_utc = df.copy()
    df_utc.index = df_utc.index.tz_localize('UTC') if df_utc.index.tz is None else df_utc.index.tz_convert('UTC')
    
    # Define session hours (in UTC)
    session_hours = {
        "US": (13, 30, 20, 0),  # 13:30-20:00 UTC (9:30 AM - 4:00 PM ET)
        "EU": (7, 0, 15, 30),   # 07:00-15:30 UTC (8:00 AM - 4:30 PM CET)
        "APAC": (0, 0, 7, 0)    # 00:00-07:00 UTC (9:00 AM - 4:00 PM JST)
    }
    
    start_hour, start_min, end_hour, end_min = session_hours[session]
    
    # Filter by session hours
    if start_hour < end_hour:
        # Simple case: session is within same day
        mask = (
            ((df_utc.index.hour > start_hour) | 
             ((df_utc.index.hour == start_hour) & (df_utc.index.minute >= start_min))) &
            ((df_utc.index.hour < end_hour) |
             ((df_utc.index.hour == end_hour) & (df_utc.index.minute <= end_min)))
        )
    else:
        # Complex case: session spans across midnight (e.g., APAC session ending next day)
        mask = (
            # After start time today
            ((df_utc.index.hour > start_hour) | 
             ((df_utc.index.hour == start_hour) & (df_utc.index.minute >= start_min))) |
            # Before end time tomorrow
            ((df_utc.index.hour < end_hour) |
             ((df_utc.index.hour == end_hour) & (df_utc.index.minute <= end_min)))
        )
    
    return df_utc[mask]

def calculate_beta(coin_prices, reference_prices, session=None):
    try:
        # Filter by session if specified
        if session and session != "None":
            coin_prices = filter_by_session(coin_prices, session)
            reference_prices = filter_by_session(reference_prices, session)
            
        joined = pd.concat([coin_prices, reference_prices], axis=1).dropna()
        if len(joined) < 2:
            return None
            
        returns_coin = joined.iloc[:,0].pct_change().dropna()
        returns_ref = joined.iloc[:,1].pct_change().dropna()
        
        covariance = np.cov(returns_coin, returns_ref)[0][1]
        variance = np.var(returns_ref)
        return covariance / variance
    except:
        return None

def create_beta_charts(btc_betas_df, eth_betas_df):
    # Create figures for both BTC and ETH betas
    figs = []
    
    # BTC Beta Chart
    fig_btc = go.Figure()
    
    # Add top 20 coins
    top_20 = btc_betas_df.head(20).index
    fig_btc.add_trace(go.Scatter(
        x=btc_betas_df[btc_betas_df.index.isin(top_20)].index,
        y=btc_betas_df[btc_betas_df.index.isin(top_20)]['Beta'],
        mode='markers',
        name='Top 20',
        marker=dict(
            size=8,
            color='gold',
            opacity=0.8
        )
    ))
    
    # Add bottom 20 coins
    bottom_20 = btc_betas_df.tail(20).index
    fig_btc.add_trace(go.Scatter(
        x=btc_betas_df[btc_betas_df.index.isin(bottom_20)].index,
        y=btc_betas_df[btc_betas_df.index.isin(bottom_20)]['Beta'],
        mode='markers',
        name='Bottom 20',
        marker=dict(
            size=8,
            color='red',
            opacity=0.8
        )
    ))
    
    # Add other coins
    other_coins = btc_betas_df[~btc_betas_df.index.isin(list(top_20) + list(bottom_20))].index
    fig_btc.add_trace(go.Scatter(
        x=btc_betas_df[btc_betas_df.index.isin(other_coins)].index,
        y=btc_betas_df[btc_betas_df.index.isin(other_coins)]['Beta'],
        mode='markers',
        name='Other Coins',
        marker=dict(
            size=8,
            color='blue',
            opacity=0.6
        )
    ))
    
    # Add BTC reference line
    fig_btc.add_hline(
        y=1,
        line_dash="dash",
        line_color="orange",
        annotation_text="BTC Beta = 1",
        annotation_position="bottom right"
    )
    
    fig_btc.update_layout(
        title="BTC Beta Distribution",
        xaxis_title="Coins",
        yaxis_title="BTC Beta Value",
        showlegend=True,
        height=500,
        template="plotly_white"
    )
    
    figs.append(fig_btc)
    
    # ETH Beta Chart
    fig_eth = go.Figure()
    
    # Add top 20 coins
    top_20_eth = eth_betas_df.head(20).index
    fig_eth.add_trace(go.Scatter(
        x=eth_betas_df[eth_betas_df.index.isin(top_20_eth)].index,
        y=eth_betas_df[eth_betas_df.index.isin(top_20_eth)]['Beta'],
        mode='markers',
        name='Top 20',
        marker=dict(
            size=8,
            color='gold',
            opacity=0.8
        )
    ))
    
    # Add bottom 20 coins
    bottom_20_eth = eth_betas_df.tail(20).index
    fig_eth.add_trace(go.Scatter(
        x=eth_betas_df[eth_betas_df.index.isin(bottom_20_eth)].index,
        y=eth_betas_df[eth_betas_df.index.isin(bottom_20_eth)]['Beta'],
        mode='markers',
        name='Bottom 20',
        marker=dict(
            size=8,
            color='red',
            opacity=0.8
        )
    ))
    
    # Add other coins
    other_coins_eth = eth_betas_df[~eth_betas_df.index.isin(list(top_20_eth) + list(bottom_20_eth))].index
    fig_eth.add_trace(go.Scatter(
        x=eth_betas_df[eth_betas_df.index.isin(other_coins_eth)].index,
        y=eth_betas_df[eth_betas_df.index.isin(other_coins_eth)]['Beta'],
        mode='markers',
        name='Other Coins',
        marker=dict(
            size=8,
            color='blue',
            opacity=0.6
        )
    ))
    
    # Add ETH reference line
    fig_eth.add_hline(
        y=1,
        line_dash="dash",
        line_color="purple",
        annotation_text="ETH Beta = 1",
        annotation_position="bottom right"
    )
    
    fig_eth.update_layout(
        title="ETH Beta Distribution",
        xaxis_title="Coins",
        yaxis_title="ETH Beta Value",
        showlegend=True,
        height=500,
        template="plotly_white"
    )
    
    figs.append(fig_eth)
    
    return figs

def calculate_all_betas(data_fetcher, start_timestamp, end_timestamp, session=None, progress_callback=None):
    valid_pairs = data_fetcher.get_valid_pairs()
    btc_prices = data_fetcher.get_historical_prices('BTC', start_timestamp, end_timestamp)
    eth_prices = data_fetcher.get_historical_prices('ETH', start_timestamp, end_timestamp)
    
    if btc_prices is None or len(btc_prices) < 2 or eth_prices is None or len(eth_prices) < 2:
        return None, None
        
    btc_betas = {'BTC': 1.0}
    eth_betas = {'ETH': 1.0}
    price_changes = {}
    current_prices = {}
    
    # Get BTC and ETH price changes
    btc_change, btc_current = data_fetcher.get_price_change('BTC', start_timestamp, end_timestamp)
    eth_change, eth_current = data_fetcher.get_price_change('ETH', start_timestamp, end_timestamp)
    
    if btc_change is not None:
        price_changes['BTC'] = btc_change
        current_prices['BTC'] = btc_current
    if eth_change is not None:
        price_changes['ETH'] = eth_change
        current_prices['ETH'] = eth_current
    
    total_pairs = len(valid_pairs)
    for idx, symbol in enumerate(valid_pairs, 1):
        if symbol not in ['BTC', 'ETH']:
            prices = data_fetcher.get_historical_prices(symbol, start_timestamp, end_timestamp)
            if prices is not None and len(prices) > 1:
                btc_beta = calculate_beta(prices, btc_prices, session)
                eth_beta = calculate_beta(prices, eth_prices, session)
                
                if btc_beta is not None:
                    btc_betas[symbol] = btc_beta
                if eth_beta is not None:
                    eth_betas[symbol] = eth_beta
                    
                # Get price change and current price
                price_change, current_price = data_fetcher.get_price_change(symbol, start_timestamp, end_timestamp)
                if price_change is not None:
                    price_changes[symbol] = price_change
                    current_prices[symbol] = current_price
                    
        # Update progress if callback is provided
        if progress_callback:
            progress_callback(idx)
    
    # Create DataFrames
    btc_df = pd.DataFrame.from_dict(btc_betas, orient='index', columns=['Beta'])
    eth_df = pd.DataFrame.from_dict(eth_betas, orient='index', columns=['Beta'])
    
    # Sort and round
    btc_df = btc_df.sort_values('Beta', ascending=False)
    eth_df = eth_df.sort_values('Beta', ascending=False)
    btc_df['Beta'] = btc_df['Beta'].round(3)
    eth_df['Beta'] = eth_df['Beta'].round(3)
    
    # Add price changes to BTC betas DataFrame
    btc_df['Price Change %'] = pd.Series(price_changes)
    btc_df['Current Price'] = pd.Series(current_prices)
    
    # Format price change column
    btc_df['Price Change %'] = btc_df.apply(
        lambda row: f"{row['Price Change %']:.2f}% (${row['Current Price']:.2f})" 
        if pd.notnull(row['Price Change %']) and pd.notnull(row['Current Price']) 
        else None, 
        axis=1
    )
    
    # Drop temporary column and add risk levels
    btc_df = btc_df.drop('Current Price', axis=1)
    btc_df['Risk Level'] = pd.cut(
        btc_df['Beta'],
        bins=[-np.inf, 0.5, 0.8, 1.2, np.inf],
        labels=['Low', 'Medium', 'Normal', 'High']
    )
    
    return btc_df, eth_df

def analyze_beta_patterns(data_fetcher, symbol, start_timestamp, end_timestamp, session=None):
    """Analyze beta patterns for a given symbol."""
    try:
        # Get the beta patterns from data_fetcher
        patterns = data_fetcher.analyze_beta_patterns(symbol, start_timestamp, end_timestamp)
        if patterns is None:
            return None

        # Get historical prices for both the symbol and BTC
        symbol_prices = data_fetcher.get_historical_prices(symbol, start_timestamp, end_timestamp)
        btc_prices = data_fetcher.get_historical_prices('BTC', start_timestamp, end_timestamp)
        
        if symbol_prices is None or btc_prices is None or len(symbol_prices) < 2 or len(btc_prices) < 2:
            return None
            
        # Filter by session if specified
        if session and session != "None":
            symbol_prices = filter_by_session(symbol_prices, session)
            btc_prices = filter_by_session(btc_prices, session)
            
        # Ensure both price series have the same index
        common_index = symbol_prices.index.intersection(btc_prices.index)
        if len(common_index) < 2:
            return None
            
        symbol_prices = symbol_prices[common_index]
        btc_prices = btc_prices[common_index]
        
        # Calculate returns
        symbol_returns = symbol_prices.pct_change().fillna(0)
        btc_returns = btc_prices.pct_change().fillna(0)
        
        # Determine appropriate window size based on the time range
        time_range = pd.Timedelta(end_timestamp - start_timestamp, unit='s')
        if time_range <= pd.Timedelta(days=1):
            window_size = '1H'  # 1-hour window for intraday
        elif time_range <= pd.Timedelta(days=7):
            window_size = '4H'  # 4-hour window for up to a week
        else:
            window_size = '1D'  # 1-day window for longer periods
        
        # Calculate rolling beta using the determined window size
        rolling_cov = symbol_returns.rolling(window=window_size, min_periods=2).cov(btc_returns)
        rolling_var = btc_returns.rolling(window=window_size, min_periods=2).var()
        beta_series = (rolling_cov / rolling_var).fillna(method='ffill')
        
        # Remove extreme outliers (more than 3 standard deviations from mean)
        beta_mean = beta_series.mean()
        beta_std = beta_series.std()
        beta_series = beta_series.clip(
            lower=beta_mean - 3 * beta_std,
            upper=beta_mean + 3 * beta_std
        )
        
        # Calculate hourly and daily averages
        hourly_beta = beta_series.groupby(beta_series.index.hour).mean()
        daily_beta = beta_series.groupby(beta_series.index.dayofweek).mean()
        
        # Map day numbers to names
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_map = {i: day_names[i] for i in daily_beta.index}
        daily_beta.index = [day_map[i] for i in daily_beta.index]
        
        # Find highest and lowest beta periods
        if patterns:
            highest_beta = patterns.get('highest_beta')
            lowest_beta = patterns.get('lowest_beta')
        else:
            highest_beta = beta_series.nlargest(1).index[0]
            lowest_beta = beta_series.nsmallest(1).index[0]
        
        return {
            'beta_series': pd.DataFrame({'beta': beta_series}),
            'hourly_beta': hourly_beta,
            'daily_beta': daily_beta,
            'highest_beta': highest_beta,
            'lowest_beta': lowest_beta,
            'window_size': window_size
        }
        
    except Exception as e:
        print(f"Error in beta pattern analysis: {str(e)}")
        return None

def filter_results_by_session(btc_df, eth_df, data_fetcher, start_timestamp, end_timestamp, session):
    """Filter pre-calculated beta results by session."""
    # Get historical prices for filtering
    btc_prices = data_fetcher.get_historical_prices('BTC', start_timestamp, end_timestamp)
    eth_prices = data_fetcher.get_historical_prices('ETH', start_timestamp, end_timestamp)
    
    # Create new DataFrames for filtered results
    filtered_btc_df = btc_df.copy()
    filtered_eth_df = eth_df.copy()
    
    # Filter each symbol's beta
    for symbol in btc_df.index:
        if symbol not in ['BTC', 'ETH']:
            prices = data_fetcher.get_historical_prices(symbol, start_timestamp, end_timestamp)
            if prices is not None:
                # Filter prices by session
                filtered_prices = filter_by_session(prices, session)
                filtered_btc_prices = filter_by_session(btc_prices, session)
                filtered_eth_prices = filter_by_session(eth_prices, session)
                
                # Calculate new betas
                btc_beta = calculate_beta(filtered_prices, filtered_btc_prices)
                eth_beta = calculate_beta(filtered_prices, filtered_eth_prices)
                
                if btc_beta is not None:
                    filtered_btc_df.at[symbol, 'Beta'] = round(btc_beta, 3)
                if eth_beta is not None:
                    filtered_eth_df.at[symbol, 'Beta'] = round(eth_beta, 3)
    
    # Update risk levels for filtered results
    filtered_btc_df['Risk Level'] = pd.cut(
        filtered_btc_df['Beta'],
        bins=[-np.inf, 0.5, 0.8, 1.2, np.inf],
        labels=['Low', 'Medium', 'Normal', 'High']
    )
    
    return filtered_btc_df, filtered_eth_df

def filter_patterns_by_session(results, data_fetcher, symbol, start_timestamp, end_timestamp, session):
    """Filter pre-calculated pattern results by session."""
    # Get historical prices
    symbol_prices = data_fetcher.get_historical_prices(symbol, start_timestamp, end_timestamp)
    btc_prices = data_fetcher.get_historical_prices('BTC', start_timestamp, end_timestamp)
    
    if symbol_prices is None or btc_prices is None:
        return results
    
    # Filter prices by session
    filtered_symbol_prices = filter_by_session(symbol_prices, session)
    filtered_btc_prices = filter_by_session(btc_prices, session)
    
    # Calculate new beta series
    symbol_returns = filtered_symbol_prices.pct_change().dropna()
    btc_returns = filtered_btc_prices.pct_change().dropna()
    
    # Align the data
    common_index = symbol_returns.index.intersection(btc_returns.index)
    symbol_returns = symbol_returns[common_index]
    btc_returns = btc_returns[common_index]
    
    # Calculate rolling statistics
    window_size = '1H'
    rolling_cov = symbol_returns.rolling(window_size).cov(btc_returns)
    rolling_var = btc_returns.rolling(window_size).var()
    beta_series = rolling_cov / rolling_var
    
    # Calculate new hourly and daily averages
    hourly_beta = beta_series.groupby(beta_series.index.hour).mean()
    daily_beta = beta_series.groupby(beta_series.index.dayofweek).mean()
    
    # Map day numbers to names only for days that exist in the data
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_map = {i: day_names[i] for i in daily_beta.index}
    daily_beta.index = [day_map[i] for i in daily_beta.index]
    
    # Create filtered results
    filtered_results = {
        'beta_series': pd.DataFrame({'beta': beta_series}),
        'hourly_beta': hourly_beta,
        'daily_beta': daily_beta,
        'highest_beta': results['highest_beta'],  # Keep original patterns for now
        'lowest_beta': results['lowest_beta']
    }
    
    return filtered_results