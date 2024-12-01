import ccxt
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
import os
import pickle
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
import hashlib

class DataFetcher:
    TIMEFRAME_THRESHOLDS = [
        (timedelta(days=7), '1h'),     # > 7 days: 1h candles
        (timedelta(days=1), '15m'),    # > 1 day: 15m candles
        (timedelta(hours=12), '5m'),   # > 12 hours: 5m candles
        (timedelta(minutes=0), '5m'),  # minimum timeframe: 5m
    ]
    
    TIMEFRAME_MINUTES = {
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '12h': 720,
        '1d': 1440
    }
    
    # Define trading sessions in UTC
    TRADING_SESSIONS = {
        'US': {'start_hour': 13, 'end_hour': 20},     # 9:00-16:00 EST (13:00-20:00 UTC)
        'EU': {'start_hour': 7, 'end_hour': 16},      # 8:00-17:00 CET (7:00-16:00 UTC)
        'APAC': {'start_hour': 0, 'end_hour': 8}      # 9:00-17:00 JST (0:00-8:00 UTC)
    }
    
    def __init__(self, max_workers=10):
        self.exchange = ccxt.hyperliquid({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            },
            'rateLimit': 50
        })
        self.markets = self.exchange.load_markets()
        self.cache_dir = Path('cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.price_cache = self._load_cache()
        self.runtime_cache = {}
        self.runtime_cache_lock = threading.Lock()
        self.max_workers = max_workers
        self.cache_duration = 3600  # 1 hour cache duration
        self._cleanup_old_cache()  # Clean up old cache entries on initialization
        
    def _get_timeframe(self, start_dt, end_dt):
        """Determine appropriate timeframe based on time difference."""
        time_diff = end_dt - start_dt
        for threshold, timeframe in self.TIMEFRAME_THRESHOLDS:
            if time_diff > threshold:
                return timeframe
        return '5m'
        
    def _get_cache_key(self, symbol, date, timeframe):
        """Generate a cache key for a symbol, date, and timeframe."""
        return f"{symbol}_{date.strftime('%Y%m')}_{timeframe}"
        
    def _get_chunk_cache_key(self, symbol, start_dt, end_dt, timeframe):
        """Generate a cache key for a specific time chunk."""
        start_str = start_dt.strftime('%Y%m%d_%H%M')
        end_str = end_dt.strftime('%Y%m%d_%H%M')
        return f"{symbol}_{start_str}_{end_str}_{timeframe}"
        
    def _get_runtime_cache_key(self, symbol, start_timestamp, end_timestamp):
        """Generate a runtime cache key."""
        return f"{symbol}_{start_timestamp}_{end_timestamp}"
        
    def _load_cache(self):
        """Load cached data from disk."""
        cache_file = self.cache_dir / 'price_cache.pkl'
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return {}
        return {}
        
    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / 'price_cache.pkl'
        with open(cache_file, 'wb') as f:
            pickle.dump(self.price_cache, f)
            
    def _resample_data(self, df, target_timeframe):
        """Resample data to target timeframe."""
        if target_timeframe not in self.TIMEFRAME_MINUTES:
            return df
            
        target_minutes = self.TIMEFRAME_MINUTES[target_timeframe]
        
        # Get current timeframe from data frequency
        current_minutes = min(pd.Series(df.index).diff().dt.total_seconds().div(60).mode())
        
        if target_minutes <= current_minutes:
            return df  # Can't downsample to a lower timeframe
            
        # Resample to target timeframe
        resampled = df.resample(target_timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()  # Remove any NaN values after resampling
        
        return resampled
            
    def get_valid_pairs(self):
        valid_pairs = [
            symbol.split('/')[0] for symbol in self.markets.keys()
            if symbol.endswith('/USDC:USDC') and self.markets[symbol].get('swap', False)
        ]
        print(f"Found {len(valid_pairs)} trading pairs")
        return valid_pairs

    def _update_runtime_cache(self, key, data, expiry_time=300):  # 5 minutes expiry
        """Update runtime cache with expiry time."""
        with self.runtime_cache_lock:
            self.runtime_cache[key] = {
                'data': data,
                'expiry': time.time() + expiry_time
            }

    def _get_from_runtime_cache(self, key):
        """Get data from runtime cache if not expired."""
        with self.runtime_cache_lock:
            if key in self.runtime_cache:
                cache_item = self.runtime_cache[key]
                if time.time() < cache_item['expiry']:
                    return cache_item['data']
                else:
                    del self.runtime_cache[key]
            return None

    def _get_cache_key_with_time(self, symbol, start_timestamp, end_timestamp):
        """Generate a unique cache key including time range."""
        key_string = f"{symbol}_{start_timestamp}_{end_timestamp}"
        return hashlib.md5(key_string.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def _get_cached_price_change(self, symbol, start_timestamp, end_timestamp):
        """Cached version of price change calculation."""
        cache_key = self._get_cache_key_with_time(symbol, start_timestamp, end_timestamp)
        cached_data = self._get_from_runtime_cache(cache_key)
        if cached_data is not None:
            return cached_data

        result = self.get_price_change(symbol, start_timestamp, end_timestamp)
        self._update_runtime_cache(cache_key, result)
        return result

    def _filter_by_session(self, df, session=None):
        """Filter DataFrame to include only data from specified trading session."""
        if session is None or session not in self.TRADING_SESSIONS:
            return df
            
        session_hours = self.TRADING_SESSIONS[session]
        mask = (df.index.hour >= session_hours['start_hour']) & \
               (df.index.hour < session_hours['end_hour'])
        return df[mask]

    def get_price_changes_batch(self, symbols, start_timestamp, end_timestamp, session=None):
        """Fetch price changes for multiple symbols with improved caching."""
        cache_key = f"batch_{start_timestamp}_{end_timestamp}"
        cached_results = self._get_from_runtime_cache(cache_key)
        if cached_results is not None:
            return cached_results

        results = {}
        
        def fetch_symbol_data(symbol):
            try:
                # Use cached version of price change calculation
                return symbol, self.get_price_change(symbol, start_timestamp, end_timestamp, session)
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                return symbol, (None, None)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {executor.submit(fetch_symbol_data, symbol): symbol 
                              for symbol in symbols}
            for future in as_completed(future_to_symbol):
                symbol, result = future.result()
                results[symbol] = result

        # Cache the batch results
        self._update_runtime_cache(cache_key, results, expiry_time=300)
        return results

    def _clean_old_cache(self):
        """Clean expired cache entries."""
        current_time = time.time()
        with self.runtime_cache_lock:
            expired_keys = [
                key for key, item in self.runtime_cache.items()
                if current_time >= item['expiry']
            ]
            for key in expired_keys:
                del self.runtime_cache[key]

    def _update_runtime_cache(self, key, data, expiry_time=300):
        """Update runtime cache with automatic cleaning."""
        self._clean_old_cache()  # Clean old entries before adding new ones
        with self.runtime_cache_lock:
            self.runtime_cache[key] = {
                'data': data,
                'expiry': time.time() + expiry_time
            }

    def get_historical_prices(self, symbol, start_timestamp, end_timestamp, session=None):
        # Convert timestamps to datetime for cache keys
        start_dt = datetime.fromtimestamp(start_timestamp, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end_timestamp, tz=timezone.utc)
        
        # Check runtime cache first
        cache_key = self._get_runtime_cache_key(symbol, start_timestamp, end_timestamp)
        cached_data = self._get_from_runtime_cache(cache_key)
        if cached_data is not None:
            return self._filter_by_session(pd.Series(cached_data), session)

        try:
            all_data = []
            current_start = start_dt
            
            while current_start < end_dt:
                # Calculate chunk end (7 days or final end_dt)
                chunk_end = min(current_start + timedelta(days=7), end_dt)
                
                # Try to get data from cache first
                chunk_data = self._get_cached_chunk(symbol, current_start, chunk_end)
                
                if chunk_data is None:
                    # If no cached data, fetch from exchange
                    chunk_data = self._fetch_and_cache_chunk(symbol, current_start, chunk_end)
                
                if chunk_data is not None and len(chunk_data) > 0:
                    all_data.append(chunk_data)
                
                current_start = chunk_end

            if not all_data:
                print(f"No data available for {symbol}")
                return None
            
            # Combine all chunks and sort by index
            combined_df = pd.concat(all_data)
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            combined_df.sort_index(inplace=True)
            
            # Update runtime cache
            self._update_runtime_cache(cache_key, combined_df['close'])
            
            # Apply session filter and return
            filtered_df = self._filter_by_session(combined_df, session)
            return filtered_df['close']
            
        except Exception as e:
            print(f"Error fetching {symbol}: {str(e)}")
            return None

    def _get_cached_chunk(self, symbol, start_dt, end_dt):
        """Get cached data for a specific time chunk."""
        cache_key = self._get_chunk_cache_key(symbol, start_dt, end_dt, '5m')
        
        if cache_key in self.price_cache:
            df = self.price_cache[cache_key]
            # Verify the cached data covers our time range
            if df.index.min() <= start_dt and df.index.max() >= end_dt:
                mask = (df.index >= start_dt) & (df.index <= end_dt)
                return df[mask]
        return None

    def _fetch_and_cache_chunk(self, symbol, start_dt, end_dt):
        """Fetch and cache data for a specific time chunk."""
        print(f"Fetching new data for {symbol} from {start_dt} to {end_dt}")
        formatted_symbol = f"{symbol}/USDC:USDC"
        
        # Add padding to ensure we get enough data
        padded_start = start_dt - timedelta(minutes=30)
        padded_end = end_dt + timedelta(minutes=30)
        
        ohlcv = self.exchange.fetch_ohlcv(
            formatted_symbol,
            timeframe='5m',
            since=int(padded_start.timestamp() * 1000),
            limit=2000
        )
        
        if not ohlcv:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        
        # Cache the new data
        cache_key = self._get_chunk_cache_key(symbol, start_dt, end_dt, '5m')
        self.price_cache[cache_key] = df
        self._save_cache()
        
        # Filter to exact timeframe
        mask = (df.index >= start_dt) & (df.index <= end_dt)
        return df[mask]

    def get_price_change(self, symbol, start_timestamp, end_timestamp, session=None):
        try:
            prices = self.get_historical_prices(symbol, start_timestamp, end_timestamp, session)
            if prices is None or len(prices) < 2:
                return None, None
                
            start_price = prices.iloc[0]
            end_price = prices.iloc[-1]
            
            # Get current price
            ticker = self.exchange.fetch_ticker(f"{symbol}/USDC:USDC")
            current_price = ticker['last']
            
            # Calculate price change percentage
            price_change = ((end_price - start_price) / start_price) * 100
            
            return price_change, current_price
            
        except Exception as e:
            print(f"Error getting price change for {symbol}: {str(e)}")
            return None, None

    def to_csv(self, results, filename="market_beta_analysis.csv"):
        """Convert results to CSV without affecting the original data."""
        try:
            # Create a DataFrame from the results
            df = pd.DataFrame(results).round(2)
            df.columns = ['Beta', 'R2', 'Current Price']
            
            # Save to CSV
            csv_path = Path('downloads')
            csv_path.mkdir(exist_ok=True)
            full_path = csv_path / filename
            df.to_csv(full_path)
            return str(full_path)
        except Exception as e:
            print(f"Error saving CSV: {str(e)}")
            return None

    def analyze_beta_patterns(self, symbol, start_timestamp, end_timestamp):
        """Analyze beta patterns for different time windows."""
        try:
            # Get historical prices for both the symbol and BTC
            symbol_prices = self.get_historical_prices(symbol, start_timestamp, end_timestamp)
            btc_prices = self.get_historical_prices('BTC', start_timestamp, end_timestamp)
            
            if symbol_prices is None or btc_prices is None:
                print(f"Could not fetch prices for {symbol} or BTC")
                return None
            
            # Ensure both price series have the same index
            common_index = symbol_prices.index.intersection(btc_prices.index)
            if len(common_index) == 0:
                print(f"No overlapping data points between {symbol} and BTC")
                return None
                
            symbol_prices = symbol_prices[common_index]
            btc_prices = btc_prices[common_index]
            
            # Convert to percentage changes
            symbol_returns = symbol_prices.pct_change().dropna()
            btc_returns = btc_prices.pct_change().dropna()
            
            # Realign after calculating returns
            common_index = symbol_returns.index.intersection(btc_returns.index)
            if len(common_index) == 0:
                print("No overlapping return data points")
                return None
                
            symbol_returns = symbol_returns[common_index]
            btc_returns = btc_returns[common_index]
            
            # Calculate current time window's average beta
            current_utc = datetime.now(timezone.utc)
            current_day = current_utc.weekday()  # 0 = Monday, 6 = Sunday
            current_hour = current_utc.hour
            
            print(f"Calculating beta for current time window: {current_utc} (Day: {current_day}, Hour: {current_hour})")
            
            # Filter data for current day and hour
            current_mask = (symbol_returns.index.dayofweek == current_day) & \
                          (symbol_returns.index.hour == current_hour)
            
            current_symbol_returns = symbol_returns[current_mask]
            current_btc_returns = btc_returns[current_mask]
            
            print(f"Found {len(current_symbol_returns)} samples for current time window")
            
            current_beta = None
            if len(current_symbol_returns) >= 5:
                current_beta = self._calculate_beta(current_symbol_returns, current_btc_returns)
                print(f"Current window beta: {current_beta}")
            else:
                print("Insufficient samples for current window beta calculation")
            
            # Initialize containers for patterns
            beta_patterns = []
            
            # Analyze each hour of each day
            for day in range(7):  # 0 = Monday, 6 = Sunday
                for hour in range(24):
                    # Filter data for this day and hour
                    mask = (symbol_returns.index.dayofweek == day) & \
                          (symbol_returns.index.hour == hour)
                    
                    hour_symbol_returns = symbol_returns[mask]
                    hour_btc_returns = btc_returns[mask]
                    
                    if len(hour_symbol_returns) >= 5:  # Require minimum number of samples
                        # Calculate beta for this time window
                        beta = self._calculate_beta(hour_symbol_returns, hour_btc_returns)
                        if beta is not None:
                            beta_patterns.append({
                                'day': day,
                                'hour': hour,
                                'beta': beta,
                                'samples': len(hour_symbol_returns)
                            })
            
            if not beta_patterns:
                print("No valid beta patterns found")
                return None
                
            # Sort patterns by beta
            beta_patterns.sort(key=lambda x: x['beta'], reverse=True)
            
            # Get top and bottom 50 patterns
            top_50 = beta_patterns[:50]
            bottom_50 = beta_patterns[-50:]
            
            # Convert day numbers to names
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            def format_pattern(pattern, rank):
                return {
                    'rank': rank,
                    'day': day_names[pattern['day']],
                    'time': f"{pattern['hour']:02d}:00-{(pattern['hour']+1):02d}:00",
                    'beta': round(pattern['beta'], 2),
                    'samples': pattern['samples']
                }
            
            result = {
                'current_window': {
                    'day': day_names[current_day],
                    'time': f"{current_hour:02d}:00-{(current_hour+1):02d}:00",
                    'beta': round(current_beta, 2) if current_beta is not None else None,
                    'samples': len(current_symbol_returns)
                },
                'highest_beta': [format_pattern(p, i+1) for i, p in enumerate(top_50)],
                'lowest_beta': [format_pattern(p, i+1) for i, p in enumerate(bottom_50)]
            }
            
            print("Final result:", result)
            return result
            
        except Exception as e:
            print(f"Error analyzing beta patterns: {str(e)}")
            return None

    def _calculate_beta(self, symbol_returns, btc_returns):
        """Calculate beta between symbol returns and BTC returns."""
        try:
            if len(symbol_returns) < 5:  # Require minimum number of samples
                return None
            
            # Calculate beta using covariance and variance
            covariance = symbol_returns.cov(btc_returns)
            variance = btc_returns.var()
            
            if variance == 0:
                return None
            
            beta = covariance / variance
            return beta
            
        except Exception as e:
            print(f"Error calculating beta: {str(e)}")
            return None

    def _cleanup_old_cache(self, max_age_days=30):
        """Remove cache entries older than max_age_days."""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for key in self.price_cache:
            # Extract date from cache key
            try:
                date_str = key.split('_')[1]
                cache_date = datetime.strptime(date_str, '%Y%m%d').replace(tzinfo=timezone.utc)
                if (current_time - cache_date).days > max_age_days:
                    expired_keys.append(key)
            except:
                continue
        
        for key in expired_keys:
            del self.price_cache[key]
        
        if expired_keys:
            self._save_cache()