import pandas as pd
import glob
import os

# Define directory containing stock data files
data_dir = os.path.join(os.getcwd(), "d_us_txt/data/daily/us/nasdaq etfs")

# RSI calculation function
def calculate_rsi(df, period=14):
    delta = df['CLOSE'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# MACD calculation function
def calculate_macd(df, short_period=12, long_period=26, signal_period=9):
    df['EMA_12'] = df['CLOSE'].ewm(span=short_period, adjust=False).mean()
    df['EMA_26'] = df['CLOSE'].ewm(span=long_period, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
    return df

# Function to calculate summary metrics, including RSI and MACD
def calculate_summary_metrics(df):
    # Calculate daily returns for volatility
    df['daily_return'] = df['CLOSE'].pct_change()
    
    # Calculate RSI and MACD
    df = calculate_rsi(df)
    df = calculate_macd(df)
    
    # Summary dictionary for each stock
    summary = {
        'TICKER': df['TICKER'].iloc[0],
        
        # 5-day metrics
        '5_day_avg_close': df['CLOSE'].tail(5).mean() if len(df) >= 5 else None,
        '5_day_volatility': df['daily_return'].tail(5).std() if len(df) >= 5 else None,
        '5_day_avg_volume': df['VOL'].tail(5).mean() if len(df) >= 5 else None,
        '5_day_return': ((df['CLOSE'].iloc[-1] / df['CLOSE'].iloc[-5] - 1) * 100) if len(df) >= 5 else None,
        
        # 10-day metrics
        '10_day_avg_close': df['CLOSE'].tail(10).mean() if len(df) >= 10 else None,
        '10_day_volatility': df['daily_return'].tail(10).std() if len(df) >= 10 else None,
        '10_day_avg_volume': df['VOL'].tail(10).mean() if len(df) >= 10 else None,
        '10_day_return': ((df['CLOSE'].iloc[-1] / df['CLOSE'].iloc[-10] - 1) * 100) if len(df) >= 10 else None,
        
        # 1-month metrics (approx. 21 trading days)
        '1_month_avg_close': df['CLOSE'].tail(21).mean() if len(df) >= 21 else None,
        '1_month_volatility': df['daily_return'].tail(21).std() if len(df) >= 21 else None,
        '1_month_avg_volume': df['VOL'].tail(21).mean() if len(df) >= 21 else None,
        '1_month_return': ((df['CLOSE'].iloc[-1] / df['CLOSE'].iloc[-21] - 1) * 100) if len(df) >= 21 else None,
        
        # 6-month metrics (approx. 126 trading days)
        '6_month_avg_close': df['CLOSE'].tail(126).mean() if len(df) >= 126 else None,
        '6_month_volatility': df['daily_return'].tail(126).std() if len(df) >= 126 else None,
        '6_month_avg_volume': df['VOL'].tail(126).mean() if len(df) >= 126 else None,
        '6_month_return': ((df['CLOSE'].iloc[-1] / df['CLOSE'].iloc[-126] - 1) * 100) if len(df) >= 126 else None,
        
        # 1-year metrics (approx. 252 trading days)
        '1_year_avg_close': df['CLOSE'].tail(252).mean() if len(df) >= 252 else None,
        '1_year_volatility': df['daily_return'].tail(252).std() if len(df) >= 252 else None,
        '1_year_avg_volume': df['VOL'].tail(252).mean() if len(df) >= 252 else None,
        '1_year_return': ((df['CLOSE'].iloc[-1] / df['CLOSE'].iloc[-252] - 1) * 100) if len(df) >= 252 else None,
        
        # Latest RSI and MACD values
        'RSI': df['RSI'].iloc[-1] if 'RSI' in df.columns else None,
        'MACD': df['MACD'].iloc[-1] if 'MACD' in df.columns else None,
        'Signal_Line': df['Signal_Line'].iloc[-1] if 'Signal_Line' in df.columns else None
    }
    
    return summary


# List to hold summary data for each stock
summary_data = []

# Loop through each file in the directory
for file_path in glob.glob(os.path.join(data_dir, '*.txt')):
    # Read the data into a DataFrame with specified column names
    df = pd.read_csv(file_path, names=['TICKER', 'PER', 'DATE', 'TIME', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOL', 'OPENINT'])
    
    # Convert DATE to datetime format with error handling
    df['DATE'] = pd.to_datetime(df['DATE'], format='%Y%m%d', errors='coerce')
    
    # Drop rows where DATE conversion failed
    df = df.dropna(subset=['DATE'])
    
    # Convert CLOSE and VOL columns to numeric, setting errors='coerce' to handle non-numeric values
    df['CLOSE'] = pd.to_numeric(df['CLOSE'], errors='coerce')
    df['VOL'] = pd.to_numeric(df['VOL'], errors='coerce')
    
    # Drop rows with NaN values in CLOSE or VOL columns after conversion
    df = df.dropna(subset=['CLOSE', 'VOL'])
    
    # Sort data by date
    df = df.sort_values(by='DATE')

    # Calculate summary metrics for each stock if there are enough data points
    if len(df) >= 5:  # Ensure there's at least 5 rows for the 5-day metrics
        stock_summary = calculate_summary_metrics(df)
        summary_data.append(stock_summary)

# Convert the list of dictionaries to a DataFrame
final_summary_df = pd.DataFrame(summary_data)

# Save the final summary data to a CSV file
final_summary_df.to_csv('summary_etf_data.csv', index=False)
