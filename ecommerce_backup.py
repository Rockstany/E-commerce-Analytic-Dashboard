"""
E-COMMERCE DATA AGGREGATION SCRIPT
===================================

PURPOSE:
This script reads raw e-commerce tracking data (CSV files) and creates
aggregated summary tables for fast dashboard loading.

WHAT IT DOES:
1. Loads 8 raw CSV files (user, session, order, etc.)
2. Performs calculations and aggregations
3. Creates 7 aggregated summary tables
4. Exports results as CSV files

WHY WE NEED THIS:
- Dashboards load 10-100x faster by reading pre-calculated summaries
- Consistent metrics across all dashboards
- Reduces database load

WHEN TO RUN:
- Daily at 1 AM (automated via cron job or task scheduler)
- After any raw data updates
- When adding new calculated fields

HOW TO MODIFY:
- See DATABASE_DESIGN_DOCUMENTATION.md for detailed instructions
- Each function has comments explaining what can be changed

BUSINESS RULES:
- HOLIDAY10 coupon = 10% discount on total_price
- RING20 coupon     = 20% discount on total_price
- No coupon         = 0% discount
- total_price       = sum of (product_price x product_qty), BEFORE discount, EXCLUDING shipping
- product_price     = unit price only, never pre-multiplied by qty

PRODUCTS & UNIT PRICES:
- Video Doorbell Pro 2    = $249.99
- Ring Alarm 8-piece      = $249.99
- Indoor Cam (2nd Gen)    = $59.99
- Stick Up Cam Battery    = $99.99

AUTHOR: Data Engineering Team
LAST UPDATED: 2026-02-18
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# CONFIGURATION SECTION
# ==============================================================================

class Config:
    """
    Configuration settings for the data processing pipeline
    MODIFY THESE PATHS based on your folder structure
    """
    # Input folder - where raw CSV files are stored
    RAW_DATA_DIR = 'raw_data/'

    # Output folder - where aggregated CSV files will be saved
    AGGREGATED_DATA_DIR = 'aggregated_data/'

    # Log folder - where processing logs are saved
    LOG_DIR = 'logs/'

    # Date range to process
    # None = process all data
    # Set specific date to process only that day: datetime(2025, 1, 1)
    START_DATE = None
    END_DATE = None

    # COUPON RULES
    # Maps coupon code → discount percentage (as decimal)
    # HOLIDAY10 = 10%, RING20 = 20%, no coupon = 0%
    COUPON_DISCOUNT_MAP = {
        'HOLIDAY10': 0.10,
        'RING20':    0.20,
    }

    # PRODUCT UNIT PRICES
    # Used to validate product_price values loaded from CSVs
    PRODUCT_PRICES = {
        'Video Doorbell Pro 2':   249.99,
        'Ring Alarm 8-piece':     249.99,
        'Indoor Cam (2nd Gen)':   59.99,
        'Stick Up Cam Battery':   99.99,
    }

    # PURCHASE FREQUENCY BUCKET THRESHOLDS
    # Used in create_user_lifetime_metrics() → purchase_frequency_bucket field
    # Buckets: 1 order, 2 orders, 3-5 orders, 6-10 orders, 11+ orders
    FREQUENCY_BUCKET_BINS   = [0, 1, 2, 5, 10, float('inf')]
    FREQUENCY_BUCKET_LABELS = ['1 order', '2 orders', '3-5 orders', '6-10 orders', '11+ orders']

    @staticmethod
    def setup_directories():
        """Creates necessary folders if they don't exist"""
        for directory in [Config.RAW_DATA_DIR,
                          Config.AGGREGATED_DATA_DIR,
                          Config.LOG_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Created directory: {directory}")


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def log_message(message, log_file='aggregation_log.txt'):
    """
    Writes messages to both console and log file

    WHY: Track when script runs and if errors occur

    Args:
        message (str): Message to log
        log_file (str): Name of log file
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    log_path = os.path.join(Config.LOG_DIR, log_file)
    with open(log_path, 'a') as f:
        f.write(log_entry + '\n')


def load_csv_safe(filename, required_columns=None):
    """
    Safely loads a CSV file with error handling

    WHY: Prevents script from crashing if file is missing or corrupted

    Args:
        filename (str): Name of CSV file to load
        required_columns (list): Columns that must exist

    Returns:
        DataFrame or None if file not found
    """
    filepath = os.path.join(Config.RAW_DATA_DIR, filename)

    try:
        df = pd.read_csv(filepath)
        log_message(f"✓ Loaded {filename}: {len(df)} rows")

        if required_columns:
            missing = set(required_columns) - set(df.columns)
            if missing:
                log_message(f"⚠ Warning: {filename} missing columns: {missing}")

        return df

    except FileNotFoundError:
        log_message(f"✗ Error: {filename} not found in {Config.RAW_DATA_DIR}")
        return None

    except Exception as e:
        log_message(f"✗ Error loading {filename}: {str(e)}")
        return None


def parse_dates(df, date_columns):
    """
    Converts string dates to datetime format

    Args:
        df (DataFrame): DataFrame to process
        date_columns (list): Column names containing dates

    Returns:
        DataFrame with parsed dates
    """
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df


def validate_and_fix_discounts(orders_df):
    """
    Validates and corrects the discount field in orders based on coupon rules.

    BUSINESS RULES:
    - HOLIDAY10 → discount = total_price * 10%
    - RING20     → discount = total_price * 20%
    - No coupon  → discount = 0

    WHY THIS MATTERS:
    - total_price = gross product amount (before discount, no shipping)
    - The discount field must exactly match the coupon rule
    - Any mismatch is corrected and flagged in the log

    HOW IT WORKS:
    1. Calculate what the discount SHOULD be based on coupon code
    2. Compare to what the discount IS in the data
    3. If they differ → overwrite with correct value and log a warning

    Args:
        orders_df (DataFrame): Order data with columns:
            - discount_coupon_code: coupon code or NaN if none
            - total_price: gross order amount before discount
            - discount: discount amount to validate

    Returns:
        DataFrame: orders_df with corrected discount column
    """
    log_message("  Validating coupon discount amounts...")

    # Fill missing coupon codes with 'NO_COUPON' for clarity
    orders_df['discount_coupon_code'] = orders_df['discount_coupon_code'].fillna('NO_COUPON')

    # Calculate what discount SHOULD be for each row based on coupon code
    # Logic: look up coupon in COUPON_DISCOUNT_MAP, multiply by total_price
    # If coupon not in map (or NO_COUPON) → expected discount = 0
    orders_df['expected_discount'] = orders_df.apply(
        lambda row: round(
            row['total_price'] * Config.COUPON_DISCOUNT_MAP.get(row['discount_coupon_code'], 0.0),
            2
        ),
        axis=1
    )

    # Find rows where actual discount does not match expected discount
    # WHY: Mismatches indicate bad data that would corrupt coupon performance metrics
    mismatch_mask = (orders_df['discount'].round(2) != orders_df['expected_discount'])
    mismatch_count = mismatch_mask.sum()

    if mismatch_count > 0:
        log_message(f"  ⚠ Found {mismatch_count} order(s) with incorrect discount amounts — correcting...")

        # Log a sample of mismatches for audit trail
        sample = orders_df[mismatch_mask][['order_id', 'discount_coupon_code',
                                           'total_price', 'discount',
                                           'expected_discount']].head(5)
        for _, row in sample.iterrows():
            log_message(
                f"    Order {row['order_id']}: coupon={row['discount_coupon_code']}, "
                f"total={row['total_price']}, "
                f"discount was {row['discount']} → corrected to {row['expected_discount']}"
            )

        # Overwrite incorrect discount values with correct ones
        orders_df.loc[mismatch_mask, 'discount'] = orders_df.loc[mismatch_mask, 'expected_discount']
    else:
        log_message("  ✓ All discount amounts are correct")

    # Drop helper column — not needed in output
    orders_df = orders_df.drop(columns=['expected_discount'])

    return orders_df


def validate_product_prices(order_items_df):
    """
    Validates that product_price in order_line_item_table matches known unit prices.

    BUSINESS RULES:
    - product_price is always the UNIT price for a single item
    - It must NOT be pre-multiplied by product_qty
    - Known prices: Video Doorbell Pro 2 / Ring Alarm 8-piece = $249.99,
                    Indoor Cam (2nd Gen) = $59.99, Stick Up Cam Battery = $99.99

    WHY THIS MATTERS:
    - line_revenue = product_price x product_qty
    - If product_price is already multiplied, revenue calculations are wrong

    HOW IT WORKS:
    1. For each known product, check if product_price matches expected unit price
    2. If not → log a warning (we do not auto-correct prices as they may reflect
       legitimate promotions not captured in Config.PRODUCT_PRICES)

    Args:
        order_items_df (DataFrame): Order line items with columns:
            - product_name, product_price, product_qty

    Returns:
        DataFrame: order_items_df unchanged (warnings logged only)
    """
    log_message("  Validating product unit prices...")

    issues_found = 0

    for product_name, expected_price in Config.PRODUCT_PRICES.items():
        # Filter rows for this product
        product_rows = order_items_df[order_items_df['product_name'] == product_name]

        if product_rows.empty:
            continue

        # Find rows where price doesn't match expected unit price
        # WHY round to 2dp: avoid floating point comparison issues
        wrong_price_mask = (product_rows['product_price'].round(2) != round(expected_price, 2))
        wrong_count = wrong_price_mask.sum()

        if wrong_count > 0:
            issues_found += wrong_count
            log_message(
                f"  ⚠ '{product_name}': {wrong_count} row(s) have unexpected price "
                f"(expected ${expected_price}). Check if product_price has been pre-multiplied by qty."
            )

            # Show sample of bad rows
            bad_sample = product_rows[wrong_price_mask][
                ['order_id', 'product_name', 'product_price', 'product_qty']
            ].head(3)
            for _, row in bad_sample.iterrows():
                log_message(
                    f"    Order {row['order_id']}: price={row['product_price']}, qty={row['product_qty']}"
                )

    if issues_found == 0:
        log_message("  ✓ All product prices match expected unit prices")

    return order_items_df


# ==============================================================================
# DATA LOADING FUNCTIONS
# ==============================================================================

def load_all_raw_data():
    """
    Loads all 8 raw CSV files into memory

    TABLE SCHEMAS (confirmed):
    - user_table:           user_id, has_purchase_last_year, has_purchase_last_qtr
    - session_table:        user_id, session_id, time, platform, device_type, country,
                            region, city, IP, referrer, landing_page, landing_page_query,
                            landing_page_hash, browser, utm_source, utm_medium, utm_campaign
    - order_table:          event_id, user_id, session_id, order_id, time, total_price,
                            shipping_price, discount, discount_coupon_code, total_items, total_qty
    - add_to_cart_table:    event_id, user_id, session_id, time, domain, path, hash, query,
                            previous_page, product_name, product_price, product_qty
    - scroll_table:         event_id, user_id, session_id, time, scroll_percent, domain,
                            path, hash, query, previous_page
    - click_table:          event_id, user_id, session_id, time, domain, path, hash, query,
                            href, target_id, target_tag, target_text, previous_page
    - pageview_table:       event_id, user_id, session_id, time, domain, path, hash,
                            query, previous_page
    - order_line_item_table: event_id, user_id, session_id, order_id, time,
                             product_name, product_price, product_qty

    Returns:
        dict: Dictionary with DataFrames for each table
    """
    log_message("="*60)
    log_message("STARTING DATA LOAD")
    log_message("="*60)

    data = {}

    # 1. USER TABLE
    log_message("\n1. Loading user_table.csv...")
    data['users'] = load_csv_safe(
        'user_table.csv',
        required_columns=['user_id', 'has_purchase_last_year', 'has_purchase_last_qtr']
    )

    # 2. SESSION TABLE
    log_message("\n2. Loading session_table.csv...")
    data['sessions'] = load_csv_safe(
        'session_table.csv',
        required_columns=['user_id', 'session_id', 'time', 'platform', 'device_type',
                          'country', 'utm_source', 'utm_medium', 'utm_campaign']
    )
    if data['sessions'] is not None:
        data['sessions'] = parse_dates(data['sessions'], ['time'])

    # 3. ORDER TABLE
    log_message("\n3. Loading order_table.csv...")
    data['orders'] = load_csv_safe(
        'order_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'order_id', 'time',
                          'total_price', 'shipping_price', 'discount',
                          'discount_coupon_code', 'total_items', 'total_qty']
    )
    if data['orders'] is not None:
        data['orders'] = parse_dates(data['orders'], ['time'])
        # VALIDATE coupon discount amounts against business rules
        data['orders'] = validate_and_fix_discounts(data['orders'])

    # 4. ORDER LINE ITEM TABLE
    log_message("\n4. Loading order_line_item_table.csv...")
    data['order_items'] = load_csv_safe(
        'order_line_item_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'order_id',
                          'time', 'product_name', 'product_price', 'product_qty']
    )
    if data['order_items'] is not None:
        data['order_items'] = parse_dates(data['order_items'], ['time'])
        # VALIDATE product unit prices against known prices
        data['order_items'] = validate_product_prices(data['order_items'])

    # 5. ADD TO CART TABLE
    log_message("\n5. Loading add_to_cart_table.csv...")
    data['cart'] = load_csv_safe(
        'add_to_cart_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'time', 'domain',
                          'path', 'product_name', 'product_price', 'product_qty']
    )
    if data['cart'] is not None:
        data['cart'] = parse_dates(data['cart'], ['time'])

    # 6. PAGEVIEW TABLE
    log_message("\n6. Loading pageview_table.csv...")
    data['pageviews'] = load_csv_safe(
        'pageview_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'time',
                          'domain', 'path', 'previous_page']
    )
    if data['pageviews'] is not None:
        data['pageviews'] = parse_dates(data['pageviews'], ['time'])

    # 7. SCROLL TABLE
    log_message("\n7. Loading scroll_table.csv...")
    data['scrolls'] = load_csv_safe(
        'scroll_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'time',
                          'scroll_percent', 'domain', 'path']
    )
    if data['scrolls'] is not None:
        data['scrolls'] = parse_dates(data['scrolls'], ['time'])

    # 8. CLICK TABLE
    log_message("\n8. Loading click_table.csv...")
    data['clicks'] = load_csv_safe(
        'click_table.csv',
        required_columns=['event_id', 'user_id', 'session_id', 'time', 'domain',
                          'path', 'href', 'target_id', 'target_tag', 'target_text']
    )
    if data['clicks'] is not None:
        data['clicks'] = parse_dates(data['clicks'], ['time'])

    log_message("\n" + "="*60)
    log_message("DATA LOAD COMPLETE")
    log_message("="*60)

    return data


# ==============================================================================
# AGGREGATION FUNCTION 1: DAILY BUSINESS METRICS
# ==============================================================================

def create_daily_business_metrics(orders_df, sessions_df, users_df):
    """
    Creates high-level daily KPIs for executive dashboard

    PURPOSE:
    - Provides daily snapshot of business health
    - Fast loading for executive dashboard
    - Historical trend analysis

    CALCULATES:
    - Total revenue per day (gross, before discount)
    - Total discount given per day
    - Net revenue per day (total_price - discount)
    - Number of orders per day
    - Number of sessions (website visits) per day
    - Conversion rate (% of sessions that become orders)
    - Average order value
    - New vs repeat customers

    HOW TO ADD NEW FIELD:
    Example - Add "Total Shipping Revenue":
    1. Add: metrics['total_shipping'] = orders_df.groupby('date')['shipping_price'].sum()
    2. Add 'total_shipping' to the DataFrame creation at the end

    Args:
        orders_df (DataFrame): Order data
        sessions_df (DataFrame): Session data
        users_df (DataFrame): User data

    Returns:
        DataFrame: Daily aggregated metrics
    """
    log_message("\n" + "="*60)
    log_message("CREATING: daily_business_metrics")
    log_message("="*60)

    if orders_df is None or sessions_df is None:
        log_message("⚠ Skipping - missing required data")
        return None

    orders_df['date'] = orders_df['time'].dt.date
    sessions_df['date'] = sessions_df['time'].dt.date

    metrics = {}

    # 1. GROSS REVENUE PER DAY
    # WHY: total_price = product amounts before discount, no shipping
    log_message("  Calculating gross revenue...")
    metrics['gross_revenue'] = orders_df.groupby('date')['total_price'].sum()

    # 2. TOTAL DISCOUNT GIVEN PER DAY
    # WHY: Tracks cost of coupon promotions per day
    # discount is validated at load time against HOLIDAY10/RING20 rules
    log_message("  Calculating total discounts...")
    metrics['total_discount'] = orders_df.groupby('date')['discount'].sum()

    # 3. NET REVENUE PER DAY
    # WHY: Actual revenue after coupon discounts (still excludes shipping)
    # FORMULA: gross_revenue - total_discount
    log_message("  Calculating net revenue...")
    metrics['net_revenue'] = metrics['gross_revenue'] - metrics['total_discount']

    # 4. TOTAL ORDERS PER DAY
    log_message("  Calculating total orders...")
    metrics['total_orders'] = orders_df.groupby('date')['order_id'].nunique()

    # 5. TOTAL SESSIONS PER DAY
    log_message("  Calculating total sessions...")
    metrics['total_sessions'] = sessions_df.groupby('date')['session_id'].nunique()

    # 6. TOTAL UNIQUE USERS PER DAY
    log_message("  Calculating total users...")
    metrics['total_users'] = sessions_df.groupby('date')['user_id'].nunique()

    # 7. CONVERSION RATE
    # FORMULA: (orders / sessions) * 100
    log_message("  Calculating conversion rate...")
    metrics['conversion_rate'] = (
        metrics['total_orders'] / metrics['total_sessions'] * 100
    ).fillna(0)

    # 8. AVERAGE ORDER VALUE (AOV) — based on gross revenue
    # FORMULA: gross_revenue / total_orders
    log_message("  Calculating average order value...")
    metrics['avg_order_value'] = (
        metrics['gross_revenue'] / metrics['total_orders']
    ).fillna(0)

    # 9. NEW VS REPEAT CUSTOMERS
    # WHY: has_purchase_last_year flag from user_table
    #      0 = new customer, 1 = repeat customer
    if users_df is not None and 'has_purchase_last_year' in users_df.columns:
        log_message("  Calculating new vs repeat customers...")

        orders_with_user = orders_df.merge(
            users_df[['user_id', 'has_purchase_last_year']],
            on='user_id',
            how='left'
        )

        metrics['new_customers'] = orders_with_user[
            orders_with_user['has_purchase_last_year'] == 0
        ].groupby('date')['user_id'].nunique()

        metrics['repeat_customers'] = orders_with_user[
            orders_with_user['has_purchase_last_year'] == 1
        ].groupby('date')['user_id'].nunique()

    log_message("  Combining metrics...")
    result_df = pd.DataFrame(metrics).reset_index()
    result_df.columns.name = None

    # Round monetary values
    for col in ['gross_revenue', 'total_discount', 'net_revenue', 'avg_order_value']:
        if col in result_df.columns:
            result_df[col] = result_df[col].round(2)

    result_df['conversion_rate'] = result_df['conversion_rate'].round(2)

    log_message(f"✓ Created {len(result_df)} daily records")
    log_message(f"  Date range: {result_df['date'].min()} to {result_df['date'].max()}")
    log_message(f"  Total gross revenue: ${result_df['gross_revenue'].sum():,.2f}")
    log_message(f"  Total discount given: ${result_df['total_discount'].sum():,.2f}")
    log_message(f"  Total net revenue:    ${result_df['net_revenue'].sum():,.2f}")

    return result_df


# ==============================================================================
# AGGREGATION FUNCTION 2: SESSION ATTRIBUTION
# ==============================================================================

def create_session_attribution(sessions_df, orders_df):
    """
    Links each session to its marketing source and conversion outcome

    PURPOSE:
    - Marketing attribution (which campaigns drive sales)
    - ROI calculation for ad spend
    - Channel performance comparison

    SESSION TABLE FIELDS USED:
    user_id, session_id, time, platform, device_type, country, region, city,
    IP, referrer, landing_page, landing_page_query, landing_page_hash,
    browser, utm_source, utm_medium, utm_campaign

    HOW IT WORKS:
    1. Take all sessions
    2. LEFT JOIN with orders on session_id
    3. converted=1 if order exists, else 0
    4. revenue = total_price (gross, before discount) if converted, else 0

    NEW FIELD — revenue_per_session_by_source:
    - Calculated as gross_revenue / total sessions, grouped by utm_source
    - Appended as a lookup join so every session row carries the aggregate
      value for its source channel
    - WHY: lets dashboards instantly compare revenue efficiency across
      channels (e.g. paid search vs email vs direct) without a separate query
    - FORMULA: sum(gross_revenue) / count(session_id) per utm_source,
      then left-joined back onto session rows

    Args:
        sessions_df (DataFrame): Session data
        orders_df (DataFrame): Order data

    Returns:
        DataFrame: Session-level attribution data
    """
    log_message("\n" + "="*60)
    log_message("CREATING: session_attribution")
    log_message("="*60)

    if sessions_df is None:
        log_message("⚠ Skipping - missing session data")
        return None

    log_message("  Merging sessions with orders...")

    # LEFT JOIN: keep all sessions, attach order data where it exists
    if orders_df is not None:
        order_cols = orders_df[['session_id', 'order_id', 'total_price',
                                'discount', 'discount_coupon_code', 'time']].copy()
    else:
        order_cols = pd.DataFrame()

    merged = sessions_df.merge(
        order_cols,
        on='session_id',
        how='left',
        suffixes=('_session', '_order')
    )

    # Extract date from session time
    merged['date'] = merged['time_session'].dt.date

    # Conversion flag: 1 if order exists for this session, else 0
    log_message("  Calculating conversion flags...")
    merged['converted'] = merged['order_id'].notna().astype(int)

    # Gross revenue: total_price before discount (0 if not converted)
    merged['gross_revenue'] = merged['total_price'].fillna(0)

    # Discount amount (0 if not converted or no coupon)
    merged['discount_amount'] = merged['discount'].fillna(0)

    # Net revenue: gross minus discount
    merged['net_revenue'] = (merged['gross_revenue'] - merged['discount_amount']).round(2)

    # Fill missing UTM / coupon values before source grouping
    for col in ['utm_source', 'utm_medium', 'utm_campaign']:
        if col in merged.columns:
            merged[col] = merged[col].fillna('direct')

    if 'discount_coupon_code' in merged.columns:
        merged['discount_coupon_code'] = merged['discount_coupon_code'].fillna('NO_COUPON')

    # -------------------------------------------------------------------------
    # NEW FIELD: revenue_per_session_by_source
    # PURPOSE: Measures how much gross revenue each marketing source generates
    #          per session it drives — a channel efficiency metric.
    # FORMULA: sum(gross_revenue) / count(sessions) grouped by utm_source,
    #          then left-joined back so every session row has the value for
    #          its own source.
    # NOTE:    This is the channel-level aggregate, not a per-session revenue.
    #          Sessions with no conversion contribute 0 to the numerator but
    #          count in the denominator, so channels with low conversion rates
    #          will score lower even if their converting orders are large.
    # -------------------------------------------------------------------------
    log_message("  Calculating revenue_per_session_by_source...")
    source_rps = (
        merged.groupby('utm_source')
        .agg(
            _src_total_revenue=('gross_revenue', 'sum'),
            _src_total_sessions=('session_id', 'count')
        )
        .reset_index()
    )
    source_rps['revenue_per_session_by_source'] = (
        source_rps['_src_total_revenue'] / source_rps['_src_total_sessions']
    ).round(2)
    source_rps = source_rps[['utm_source', 'revenue_per_session_by_source']]

    merged = merged.merge(source_rps, on='utm_source', how='left')

    # Select output columns
    log_message("  Selecting columns...")
    output_columns = [
        'session_id',
        'user_id',
        'date',
        'platform',
        'device_type',
        'country',
        'region',
        'city',
        'browser',
        'referrer',
        'landing_page',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'converted',
        'order_id',
        'discount_coupon_code',
        'gross_revenue',
        'discount_amount',
        'net_revenue',
        'revenue_per_session_by_source',    # NEW: channel-level revenue efficiency
    ]

    available_columns = [col for col in output_columns if col in merged.columns]
    result_df = merged[available_columns].copy()

    # Round monetary values
    result_df['gross_revenue'] = result_df['gross_revenue'].round(2)
    result_df['discount_amount'] = result_df['discount_amount'].round(2)

    log_message(f"✓ Created {len(result_df)} session records")
    log_message(f"  Converted sessions: {result_df['converted'].sum()}")
    log_message(f"  Conversion rate: {result_df['converted'].mean()*100:.2f}%")
    log_message(f"  Total gross revenue: ${result_df['gross_revenue'].sum():,.2f}")
    log_message(f"  Total net revenue:   ${result_df['net_revenue'].sum():,.2f}")

    log_message("  Revenue per session by source:")
    for _, row in source_rps.sort_values('revenue_per_session_by_source', ascending=False).iterrows():
        log_message(f"    {row['utm_source']}: ${row['revenue_per_session_by_source']:.2f}")

    return result_df


# ==============================================================================
# AGGREGATION FUNCTION 3: SESSION FUNNEL
# ==============================================================================

def create_session_funnel(sessions_df, pageviews_df, cart_df, orders_df):
    """
    Tracks each session's progress through the 6-step conversion funnel

    PURPOSE:
    - Identify exactly where users drop off
    - Calculate conversion rate at each funnel step
    - Optimize low-performing steps

    FUNNEL STEPS & URL LOGIC (path matching uses str.contains — partial match):
    ┌─────┬──────────────────────┬──────────────────────────────────────────────────────┐
    │Step │ Field                │ Path pattern matched in pageview_table               │
    ├─────┼──────────────────────┼──────────────────────────────────────────────────────┤
    │  1  │ had_session          │ Always 1 — every session counts                      │
    │  2  │ had_category_view    │ contains '/category/security-cameras'                │
    │  3  │ had_product_view     │ contains '/products/' (all 4 product pages)          │
    │     │                      │   /products/video-doorbell-pro-2                     │
    │     │                      │   /products/ring-alarm-8-piece                       │
    │     │                      │   /products/indoor-cam-(2nd-gen)                     │
    │     │                      │   /products/stick-up-cam-battery                     │
    │  4  │ had_cart_view        │ contains '/cart'                                     │
    │  5  │ had_checkout_payment │ contains '/checkout/payment'                         │
    │  6  │ had_thank_you        │ contains '/checkout/thankyou'                        │
    └─────┴──────────────────────┴──────────────────────────────────────────────────────┘

    NOTE: user_id is resolved via session_id join from session_table
          (not taken directly from event tables)

    HOW TO ADD A NEW FUNNEL STEP:
    1. Add a new path pattern below following the same pattern as existing steps
    2. Add the new field name to output_columns
    3. Add it to the funnel_steps list in the logging section

    Args:
        sessions_df (DataFrame): Session data
        pageviews_df (DataFrame): Pageview data
        cart_df (DataFrame): Add-to-cart data (used for time metrics only)
        orders_df (DataFrame): Order data

    Returns:
        DataFrame: Session-level funnel data with one row per session
    """
    log_message("\n" + "="*60)
    log_message("CREATING: session_funnel")
    log_message("="*60)

    if sessions_df is None:
        log_message("⚠ Skipping - missing session data")
        return None

    log_message("  Building funnel base...")
    funnel = sessions_df[['session_id', 'user_id', 'time']].copy()
    funnel['date'] = funnel['time'].dt.date

    # -------------------------------------------------------------------------
    # STEP 1: SESSION START
    # Every session counts — this is always 1 (the 100% baseline)
    # -------------------------------------------------------------------------
    funnel['had_session'] = 1

    # Helper: get session_ids that visited pages matching a given path pattern
    def sessions_with_path(pattern):
        """
        Returns set of session_ids where at least one pageview path
        contains the given pattern (case-insensitive partial match).

        Args:
            pattern (str): URL substring to search for e.g. '/cart'

        Returns:
            numpy array of matching session_ids
        """
        if pageviews_df is None or 'path' not in pageviews_df.columns:
            return []
        return pageviews_df[
            pageviews_df['path'].str.contains(pattern, case=False, na=False)
        ]['session_id'].unique()

    # -------------------------------------------------------------------------
    # STEP 2: CATEGORY VIEW
    # Did this session view the security cameras category page?
    # Path pattern: contains '/category/security-cameras'
    # -------------------------------------------------------------------------
    log_message("  Checking category views (/category/security-cameras)...")
    funnel['had_category_view'] = funnel['session_id'].isin(
        sessions_with_path('/category/security-cameras')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 3: PRODUCT VIEW
    # Did this session view any individual product page?
    # Path pattern: contains '/products/' — matches all 4 product URLs:
    #   /products/video-doorbell-pro-2
    #   /products/ring-alarm-8-piece
    #   /products/indoor-cam-(2nd-gen)
    #   /products/stick-up-cam-battery
    # -------------------------------------------------------------------------
    log_message("  Checking product views (/products/)...")
    funnel['had_product_view'] = funnel['session_id'].isin(
        sessions_with_path('/products/')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 4: CART VIEW
    # Did this session view the cart page?
    # Path pattern: contains '/cart'
    # -------------------------------------------------------------------------
    log_message("  Checking cart views (/cart)...")
    funnel['had_cart_view'] = funnel['session_id'].isin(
        sessions_with_path('/cart')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 5: CHECKOUT / PAYMENT
    # Did this session reach the payment step?
    # Path pattern: contains '/checkout/payment'
    # -------------------------------------------------------------------------
    log_message("  Checking checkout/payment views (/checkout/payment)...")
    funnel['had_checkout_payment'] = funnel['session_id'].isin(
        sessions_with_path('/checkout/payment')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 6: THANK YOU PAGE (ORDER CONFIRMED)
    # Did this session reach the thank you / order confirmed page?
    # Path pattern: contains '/checkout/thankyou'
    # NOTE: This is the strongest signal of a completed purchase from pageviews.
    #       Cross-referenced with order_table below for time metrics.
    # -------------------------------------------------------------------------
    log_message("  Checking thank you page views (/checkout/thankyou)...")
    funnel['had_thank_you'] = funnel['session_id'].isin(
        sessions_with_path('/checkout/thankyou')
    ).astype(int)

    # -------------------------------------------------------------------------
    # TIME METRICS
    # How long (in minutes) from session start to key events?
    # -------------------------------------------------------------------------
    log_message("  Calculating time metrics...")

    # Time from session start → first cart page view
    if pageviews_df is not None:
        first_cart_view = pageviews_df[
            pageviews_df['path'].str.contains('/cart', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_cart_view.columns = ['session_id', 'first_cart_view_time']

        funnel = funnel.merge(first_cart_view, on='session_id', how='left')
        funnel['time_to_cart_minutes'] = (
            (funnel['first_cart_view_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_cart_view_time'])
    else:
        funnel['time_to_cart_minutes'] = None

    # Time from session start → checkout/payment page
    if pageviews_df is not None:
        first_payment = pageviews_df[
            pageviews_df['path'].str.contains('/checkout/payment', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_payment.columns = ['session_id', 'first_payment_time']

        funnel = funnel.merge(first_payment, on='session_id', how='left')
        funnel['time_to_payment_minutes'] = (
            (funnel['first_payment_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_payment_time'])
    else:
        funnel['time_to_payment_minutes'] = None

    # Time from session start → thank you page (order confirmed)
    if orders_df is not None:
        order_time = orders_df.groupby('session_id')['time'].min().reset_index()
        order_time.columns = ['session_id', 'order_time']
        funnel = funnel.merge(order_time, on='session_id', how='left')
        funnel['time_to_order_minutes'] = (
            (funnel['order_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['order_time'])
    else:
        funnel['time_to_order_minutes'] = None

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------
    output_columns = [
        'session_id',
        'user_id',
        'date',
        'had_session',           # Step 1: Session start        (always 1)
        'had_category_view',     # Step 2: /category/security-cameras
        'had_product_view',      # Step 3: /products/*
        'had_cart_view',         # Step 4: /cart
        'had_checkout_payment',  # Step 5: /checkout/payment
        'had_thank_you',         # Step 6: /checkout/thankyou
        'time_to_cart_minutes',
        'time_to_payment_minutes',
        'time_to_order_minutes'
    ]

    result_df = funnel[output_columns].copy()

    # Log funnel breakdown
    total = len(result_df)
    funnel_steps = [
        ('Session Start',       'had_session'),
        ('Category View',       'had_category_view'),
        ('Product View',        'had_product_view'),
        ('Cart View',           'had_cart_view'),
        ('Checkout/Payment',    'had_checkout_payment'),
        ('Thank You (Ordered)', 'had_thank_you'),
    ]

    log_message(f"✓ Created {total} session funnel records")
    log_message(f"  Funnel breakdown:")
    for label, col in funnel_steps:
        count = result_df[col].sum()
        log_message(f"    {label:<25} {count:>6} ({count/total*100:.1f}%)")

    return result_df


# ==============================================================================
# AGGREGATION FUNCTION 4: PRODUCT PERFORMANCE
# ==============================================================================

def create_product_performance_daily(order_items_df, cart_df, pageviews_df):
    """
    Daily performance metrics for each product

    PURPOSE:
    - Identify best/worst selling products
    - Track product trends over time
    - Optimize inventory and merchandising

    PRICING RULE:
    - product_price = unit price only (never pre-multiplied)
    - line_revenue  = product_price x product_qty

    KNOWN PRODUCTS & UNIT PRICES:
    - Video Doorbell Pro 2   = $249.99
    - Ring Alarm 8-piece     = $249.99
    - Indoor Cam (2nd Gen)   = $59.99
    - Stick Up Cam Battery   = $99.99

    METRICS PER PRODUCT PER DAY:
    - times_purchased: count of line item rows (each row = one order line)
    - total_quantity_sold: sum of product_qty
    - total_revenue: sum of (product_price x product_qty)
    - times_added_to_cart: count from add_to_cart_table
    - cart_to_purchase_rate: (times_purchased / times_added_to_cart) * 100

    NEW FIELD — cart_abandonment_rate:
    - The inverse of cart_to_purchase_rate: the % of cart adds that did NOT
      result in a purchase.
    - FORMULA: 100 - cart_to_purchase_rate
    - WHY: Abandonment framing is more intuitive for optimisation work —
      a high number means lost revenue opportunity and prompts action.
    - NOTE: Requires times_added_to_cart > 0; rows with no cart data → 0.

    Args:
        order_items_df (DataFrame): Order line items
        cart_df (DataFrame): Cart additions
        pageviews_df (DataFrame): Page views (reserved for future product view metric)

    Returns:
        DataFrame: Product-level daily metrics
    """
    log_message("\n" + "="*60)
    log_message("CREATING: product_performance_daily")
    log_message("="*60)

    if order_items_df is None:
        log_message("⚠ Skipping - missing order items data")
        return None

    order_items_df['date'] = order_items_df['time'].dt.date

    log_message("  Aggregating order line item data...")

    # Times purchased = count of line item rows per product per day
    times_purchased = order_items_df.groupby(
        ['date', 'product_name']
    )['event_id'].count()

    # Total quantity sold = sum of product_qty
    quantity_sold = order_items_df.groupby(
        ['date', 'product_name']
    )['product_qty'].sum()

    # Line revenue = product_price (unit) x product_qty
    # product_price is always unit price — confirmed by validate_product_prices()
    order_items_df['line_revenue'] = (
        order_items_df['product_price'] * order_items_df['product_qty']
    )
    revenue = order_items_df.groupby(['date', 'product_name'])['line_revenue'].sum()

    product_metrics = pd.DataFrame({
        'times_purchased':    times_purchased,
        'total_quantity_sold': quantity_sold,
        'total_revenue':      revenue
    }).reset_index()

    # Cart additions per product per day
    log_message("  Adding cart data...")
    if cart_df is not None:
        cart_df['date'] = cart_df['time'].dt.date
        cart_adds = cart_df.groupby(
            ['date', 'product_name']
        )['event_id'].count().reset_index()
        cart_adds.columns = ['date', 'product_name', 'times_added_to_cart']

        product_metrics = product_metrics.merge(
            cart_adds, on=['date', 'product_name'], how='left'
        )
        product_metrics['times_added_to_cart'] = (
            product_metrics['times_added_to_cart'].fillna(0).astype(int)
        )

        # Cart-to-purchase rate: what % of cart adds resulted in purchase?
        product_metrics['cart_to_purchase_rate'] = (
            product_metrics['times_purchased'] /
            product_metrics['times_added_to_cart'] * 100
        ).fillna(0).round(2)

        # ---------------------------------------------------------------------
        # NEW FIELD: cart_abandonment_rate
        # PURPOSE: % of cart adds that did NOT result in a purchase.
        # FORMULA: 100 - cart_to_purchase_rate
        # NOTE:    Rows where times_added_to_cart = 0 → abandonment rate = 0
        #          (no cart adds means no abandonment to measure).
        # ---------------------------------------------------------------------
        log_message("  Calculating cart_abandonment_rate...")
        product_metrics['cart_abandonment_rate'] = (
            100 - product_metrics['cart_to_purchase_rate']
        ).clip(lower=0).round(2)

    else:
        product_metrics['times_added_to_cart'] = 0
        product_metrics['cart_to_purchase_rate'] = 0
        product_metrics['cart_abandonment_rate'] = 0

    product_metrics['total_revenue'] = product_metrics['total_revenue'].round(2)

    product_metrics = product_metrics.sort_values(
        ['date', 'total_revenue'], ascending=[True, False]
    )

    log_message(f"✓ Created {len(product_metrics)} product-day records")
    log_message(f"  Unique products: {product_metrics['product_name'].nunique()}")
    log_message(f"  Date range: {product_metrics['date'].min()} to {product_metrics['date'].max()}")
    log_message(f"  Total revenue: ${product_metrics['total_revenue'].sum():,.2f}")

    top_products = product_metrics.groupby('product_name')['total_revenue'].sum().nlargest(5)
    log_message("  Top products by revenue:")
    for product, rev in top_products.items():
        log_message(f"    {product}: ${rev:,.2f}")

    log_message("  Cart abandonment rate by product (overall avg):")
    avg_abandon = product_metrics.groupby('product_name')['cart_abandonment_rate'].mean().sort_values(ascending=False)
    for product, rate in avg_abandon.items():
        log_message(f"    {product}: {rate:.1f}%")

    return product_metrics


# ==============================================================================
# AGGREGATION FUNCTION 5: USER LIFETIME METRICS
# ==============================================================================

def create_user_lifetime_metrics(users_df, orders_df):
    """
    One row per user with lifetime statistics

    PURPOSE:
    - Customer segmentation (VIP, regular, at-risk)
    - Calculate customer lifetime value (LTV)
    - Identify customers for retention campaigns

    REVENUE NOTE:
    - total_revenue here = sum of gross total_price (before discount)
    - This reflects full basket value the customer generated

    METRICS PER USER:
    - first_order_date, last_order_date
    - total_orders (frequency)
    - total_revenue (gross monetary value)
    - avg_order_value
    - days_since_last_order (recency)
    - RFM scores and segment

    RFM SCORING:
    R (Recency):   5=last 30d, 4=31-90d, 3=91-180d, 2=181-365d, 1=365d+
    F (Frequency): 5=10+ orders, 4=5-9, 3=3-4, 2=2, 1=1
    M (Monetary):  5=$1000+, 4=$500-999, 3=$200-499, 2=$50-199, 1=<$50

    NEW FIELDS:
    ┌──────────────────────────────┬──────────────────────────────────────────────────────────┐
    │ Field                        │ Description                                              │
    ├──────────────────────────────┼──────────────────────────────────────────────────────────┤
    │ purchase_frequency_bucket    │ Human-readable order-count tier for segmentation/        │
    │                              │ reporting. Buckets: '1 order', '2 orders', '3-5 orders', │
    │                              │ '6-10 orders', '11+ orders'. Thresholds configurable in  │
    │                              │ Config.FREQUENCY_BUCKET_BINS / LABELS.                  │
    │                              │ Source: total_orders (already in this table)             │
    ├──────────────────────────────┼──────────────────────────────────────────────────────────┤
    │ days_between_order_1_and_2   │ Calendar days between a user's 1st and 2nd order.        │
    │                              │ NULL for users with only 1 order (no 2nd order yet).     │
    │                              │ WHY: Early repeat-purchase speed is the strongest        │
    │                              │ predictor of long-term LTV — used for retention timing.  │
    │                              │ Source: order_table (time of 1st and 2nd order per user) │
    └──────────────────────────────┴──────────────────────────────────────────────────────────┘

    Args:
        users_df (DataFrame): User data
        orders_df (DataFrame): Order data

    Returns:
        DataFrame: User-level lifetime metrics
    """
    log_message("\n" + "="*60)
    log_message("CREATING: user_lifetime_metrics")
    log_message("="*60)

    if orders_df is None or users_df is None:
        log_message("⚠ Skipping - missing required data")
        return None

    log_message("  Calculating user metrics...")

    user_metrics = orders_df.groupby('user_id').agg(
        first_order_date=('time', 'min'),
        last_order_date=('time', 'max'),
        total_orders=('order_id', 'nunique'),
        total_revenue=('total_price', 'sum'),       # gross revenue (before discount)
        total_discount=('discount', 'sum'),          # total discount received
        avg_order_value=('total_price', 'mean')
    ).reset_index()

    # Net revenue per user = gross - discount
    user_metrics['net_revenue'] = (
        user_metrics['total_revenue'] - user_metrics['total_discount']
    ).round(2)

    user_metrics['total_revenue'] = user_metrics['total_revenue'].round(2)
    user_metrics['total_discount'] = user_metrics['total_discount'].round(2)
    user_metrics['avg_order_value'] = user_metrics['avg_order_value'].round(2)

    # Recency: days since last order
    log_message("  Calculating recency...")
    today = pd.Timestamp(datetime.now().date())
    user_metrics['days_since_last_order'] = (
        today - user_metrics['last_order_date']
    ).dt.days

    user_metrics['first_order_date'] = user_metrics['first_order_date'].dt.date
    user_metrics['last_order_date'] = user_metrics['last_order_date'].dt.date

    # RFM SCORING
    log_message("  Calculating RFM scores...")

    user_metrics['rfm_recency_score'] = pd.cut(
        user_metrics['days_since_last_order'],
        bins=[-1, 30, 90, 180, 365, float('inf')],
        labels=[5, 4, 3, 2, 1]
    ).astype(int)

    user_metrics['rfm_frequency_score'] = pd.cut(
        user_metrics['total_orders'],
        bins=[0, 1, 2, 4, 9, float('inf')],
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    user_metrics['rfm_monetary_score'] = pd.cut(
        user_metrics['total_revenue'],
        bins=[0, 50, 200, 500, 1000, float('inf')],
        labels=[1, 2, 3, 4, 5]
    ).astype(int)

    user_metrics['rfm_score'] = (
        user_metrics['rfm_recency_score'].astype(str) +
        user_metrics['rfm_frequency_score'].astype(str) +
        user_metrics['rfm_monetary_score'].astype(str)
    )

    # SEGMENT ASSIGNMENT
    log_message("  Assigning customer segments...")

    def assign_segment(rfm_score):
        r, f, m = int(rfm_score[0]), int(rfm_score[1]), int(rfm_score[2])
        if r >= 4 and f >= 4 and m >= 4:
            return 'Champion'
        elif r >= 3 and f >= 4:
            return 'Loyal Customer'
        elif r >= 3 and f >= 2:
            return 'Potential Loyalist'
        elif r <= 2 and f >= 3:
            return 'At Risk'
        elif r == 1 and f <= 2:
            return 'Lost'
        elif r <= 2 and f <= 2:
            return 'Needs Attention'
        elif f <= 2:
            return 'New Customer'
        else:
            return 'Regular'

    user_metrics['rfm_segment'] = user_metrics['rfm_score'].apply(assign_segment)

    # -------------------------------------------------------------------------
    # NEW FIELD 1: purchase_frequency_bucket
    # PURPOSE: Human-readable tier label based on total lifetime orders.
    #          Easier to use in dashboard filters and cohort reports than the
    #          raw total_orders integer.
    # FORMULA: pd.cut on total_orders using Config.FREQUENCY_BUCKET thresholds
    # BUCKETS: '1 order' | '2 orders' | '3-5 orders' | '6-10 orders' | '11+ orders'
    # TO CHANGE BUCKETS: update Config.FREQUENCY_BUCKET_BINS and _LABELS
    # -------------------------------------------------------------------------
    log_message("  Calculating purchase_frequency_bucket...")
    user_metrics['purchase_frequency_bucket'] = pd.cut(
        user_metrics['total_orders'],
        bins=Config.FREQUENCY_BUCKET_BINS,
        labels=Config.FREQUENCY_BUCKET_LABELS,
        right=True
    ).astype(str)

    # -------------------------------------------------------------------------
    # NEW FIELD 2: days_between_order_1_and_order_2
    # PURPOSE: Measures how quickly a customer made their second purchase after
    #          their first. Strong early predictor of long-term LTV.
    #          NULL for users with only 1 order (no 2nd purchase yet).
    # FORMULA: For each user, rank orders by time ascending. Find time of
    #          rank-1 order and rank-2 order, compute the difference in days.
    # SOURCE:  order_table — uses the 'time' and 'user_id' columns directly.
    # NOTE:    Uses order time (not order_id) for ranking — if two orders share
    #          the exact same timestamp they both rank as 1st; this is rare but
    #          the min/nsmallest approach handles it gracefully.
    # -------------------------------------------------------------------------
    log_message("  Calculating days_between_order_1_and_order_2...")

    # Get per-user, per-order timestamps (deduplicated to one row per order_id)
    order_times = (
        orders_df[['user_id', 'order_id', 'time']]
        .drop_duplicates(subset=['user_id', 'order_id'])
        .sort_values(['user_id', 'time'])
    )

    # Rank orders within each user by ascending time (1 = earliest order)
    order_times['order_rank'] = (
        order_times.groupby('user_id')['time'].rank(method='first').astype(int)
    )

    # Extract 1st order time per user
    first_orders = (
        order_times[order_times['order_rank'] == 1]
        [['user_id', 'time']]
        .rename(columns={'time': 'time_order_1'})
    )

    # Extract 2nd order time per user (will be empty for 1-order users)
    second_orders = (
        order_times[order_times['order_rank'] == 2]
        [['user_id', 'time']]
        .rename(columns={'time': 'time_order_2'})
    )

    # Join both onto user_metrics
    user_metrics = user_metrics.merge(first_orders,  on='user_id', how='left')
    user_metrics = user_metrics.merge(second_orders, on='user_id', how='left')

    # Compute gap in calendar days; NULL if no 2nd order
    user_metrics['days_between_order_1_and_order_2'] = (
        (user_metrics['time_order_2'] - user_metrics['time_order_1'])
        .dt.days
    )

    # Drop helper columns — not needed in final output
    user_metrics = user_metrics.drop(columns=['time_order_1', 'time_order_2'])

    # Merge original user flags
    merge_cols = ['user_id']
    for col in ['has_purchase_last_year', 'has_purchase_last_qtr']:
        if col in users_df.columns:
            merge_cols.append(col)

    user_metrics = user_metrics.merge(
        users_df[merge_cols], on='user_id', how='left'
    )

    user_metrics = user_metrics.sort_values('total_revenue', ascending=False)

    log_message(f"✓ Created {len(user_metrics)} user records")
    log_message(f"  Total gross revenue: ${user_metrics['total_revenue'].sum():,.2f}")
    log_message(f"  Total discounts:     ${user_metrics['total_discount'].sum():,.2f}")
    log_message(f"  Total net revenue:   ${user_metrics['net_revenue'].sum():,.2f}")
    log_message(f"  Average LTV (gross): ${user_metrics['total_revenue'].mean():,.2f}")

    log_message("  Customer segment breakdown:")
    for segment, count in user_metrics['rfm_segment'].value_counts().items():
        pct = count / len(user_metrics) * 100
        log_message(f"    {segment}: {count} ({pct:.1f}%)")

    log_message("  Purchase frequency bucket breakdown:")
    for bucket, count in user_metrics['purchase_frequency_bucket'].value_counts().sort_index().items():
        pct = count / len(user_metrics) * 100
        log_message(f"    {bucket}: {count} ({pct:.1f}%)")

    has_second_order = user_metrics['days_between_order_1_and_order_2'].notna().sum()
    avg_days = user_metrics['days_between_order_1_and_order_2'].mean()
    log_message(f"  Users with 2+ orders: {has_second_order}")
    log_message(f"  Avg days between order 1 and 2: {avg_days:.1f}" if not pd.isna(avg_days) else "  Avg days between order 1 and 2: N/A")

    return user_metrics


# ==============================================================================
# AGGREGATION FUNCTION 6: PAGE ENGAGEMENT METRICS
# ==============================================================================

def create_page_engagement_metrics(pageviews_df, scrolls_df, clicks_df):
    """
    Daily engagement metrics for each page

    PURPOSE:
    - Identify high/low performing pages
    - UX optimization insights
    - Content effectiveness measurement

    TABLE FIELDS USED:
    - pageview_table:  event_id, user_id, session_id, time, domain, path, previous_page
    - scroll_table:    event_id, user_id, session_id, time, scroll_percent, domain, path
    - click_table:     event_id, user_id, session_id, time, domain, path, href,
                       target_id, target_tag, target_text

    METRICS PER PAGE PER DAY:
    - pageviews: total count of pageview events
    - unique_users: distinct user_id count (via session join)
    - sessions_with_page: distinct session_id count
    - avg_scroll_depth: mean scroll_percent from scroll_table
    - total_clicks: count of click events on this page

    NOTE: user_id is taken directly from pageview_table (confirmed in schema)

    Args:
        pageviews_df (DataFrame): Pageview data
        scrolls_df (DataFrame): Scroll data
        clicks_df (DataFrame): Click data

    Returns:
        DataFrame: Page-level daily metrics
    """
    log_message("\n" + "="*60)
    log_message("CREATING: page_engagement_metrics")
    log_message("="*60)

    if pageviews_df is None:
        log_message("⚠ Skipping - missing pageview data")
        return None

    pageviews_df['date'] = pageviews_df['time'].dt.date

    log_message("  Aggregating pageview data...")

    pageviews_count = pageviews_df.groupby(['date', 'path'])['event_id'].count()

    # user_id available directly in pageview_table schema
    unique_users = pageviews_df.groupby(['date', 'path'])['user_id'].nunique()

    sessions_count = pageviews_df.groupby(['date', 'path'])['session_id'].nunique()

    page_metrics = pd.DataFrame({
        'pageviews':          pageviews_count,
        'unique_users':       unique_users,
        'sessions_with_page': sessions_count
    }).reset_index()

    # Average scroll depth per page per day
    log_message("  Adding scroll data...")
    if scrolls_df is not None:
        scrolls_df['date'] = scrolls_df['time'].dt.date
        avg_scroll = scrolls_df.groupby(
            ['date', 'path']
        )['scroll_percent'].mean().reset_index()
        avg_scroll.columns = ['date', 'path', 'avg_scroll_depth']
        avg_scroll['avg_scroll_depth'] = avg_scroll['avg_scroll_depth'].round(2)

        page_metrics = page_metrics.merge(avg_scroll, on=['date', 'path'], how='left')
        page_metrics['avg_scroll_depth'] = page_metrics['avg_scroll_depth'].fillna(0)
    else:
        page_metrics['avg_scroll_depth'] = 0

    # Total clicks per page per day
    log_message("  Adding click data...")
    if clicks_df is not None:
        clicks_df['date'] = clicks_df['time'].dt.date
        clicks_count = clicks_df.groupby(
            ['date', 'path']
        )['event_id'].count().reset_index()
        clicks_count.columns = ['date', 'path', 'total_clicks']

        page_metrics = page_metrics.merge(clicks_count, on=['date', 'path'], how='left')
        page_metrics['total_clicks'] = page_metrics['total_clicks'].fillna(0).astype(int)
    else:
        page_metrics['total_clicks'] = 0

    page_metrics = page_metrics.sort_values(
        ['date', 'pageviews'], ascending=[True, False]
    )

    log_message(f"✓ Created {len(page_metrics)} page-day records")
    log_message(f"  Unique pages: {page_metrics['path'].nunique()}")
    log_message(f"  Total pageviews: {page_metrics['pageviews'].sum():,}")

    top_pages = page_metrics.groupby('path')['pageviews'].sum().nlargest(5)
    log_message("  Top 5 pages by pageviews:")
    for path, views in top_pages.items():
        log_message(f"    {path}: {views:,} views")

    return page_metrics


# ==============================================================================
# AGGREGATION FUNCTION 7: COUPON PERFORMANCE
# ==============================================================================

def create_coupon_performance(orders_df):
    """
    Daily performance metrics for discount coupons

    PURPOSE:
    - Measure promotion effectiveness
    - Calculate ROI of discount campaigns
    - Identify popular coupons

    COUPON RULES:
    - HOLIDAY10: 10% discount on total_price
    - RING20:    20% discount on total_price
    - NO_COUPON: 0% discount

    NOTE: discount values are validated at load time in validate_and_fix_discounts()
    so all discount amounts here are guaranteed to be correct.

    METRICS PER COUPON PER DAY:
    - usage_count: number of orders using this coupon
    - total_discount_given: sum of discount amounts
    - gross_revenue: sum of total_price (before discount)
    - net_revenue: gross_revenue - total_discount_given
    - avg_order_value: mean total_price
    - discount_percentage: (total_discount / gross_revenue) * 100

    NEW FIELD — gross_order_value_before_discount:
    - Alias for gross_revenue at the coupon-day grain, named explicitly to
      make the "before discount" nature of the number unambiguous for anyone
      querying this table directly.
    - FORMULA: sum(total_price) per coupon per day — same source as gross_revenue
      but kept as a separate, clearly-named column so dashboard consumers don't
      confuse it with net revenue.
    - WHY: coupon_performance is often used by Finance / Marketing to evaluate
      promotion cost. Having both gross_order_value_before_discount and
      net_revenue in the same table makes the P&L impact immediately readable
      without joins.

    Args:
        orders_df (DataFrame): Order data (discounts already validated)

    Returns:
        DataFrame: Coupon-level daily metrics
    """
    log_message("\n" + "="*60)
    log_message("CREATING: coupon_performance")
    log_message("="*60)

    if orders_df is None or 'discount_coupon_code' not in orders_df.columns:
        log_message("⚠ Skipping - missing order data or coupon field")
        return None

    orders_df['date'] = orders_df['time'].dt.date

    # discount_coupon_code already filled with 'NO_COUPON' by validate_and_fix_discounts()

    log_message("  Aggregating coupon data...")

    coupon_metrics = orders_df.groupby(['date', 'discount_coupon_code']).agg(
        usage_count=('order_id', 'count'),
        total_discount_given=('discount', 'sum'),
        gross_revenue=('total_price', 'sum'),
        avg_order_value=('total_price', 'mean')
    ).reset_index()

    # Net revenue = gross minus discount
    coupon_metrics['net_revenue'] = (
        coupon_metrics['gross_revenue'] - coupon_metrics['total_discount_given']
    ).round(2)

    # Discount percentage = (discount / gross) * 100
    coupon_metrics['discount_percentage'] = (
        coupon_metrics['total_discount_given'] /
        coupon_metrics['gross_revenue'] * 100
    ).round(2)

    # -------------------------------------------------------------------------
    # NEW FIELD: gross_order_value_before_discount
    # PURPOSE: An explicitly-named copy of gross_revenue (sum of total_price
    #          before any coupon discount) to remove ambiguity for Finance /
    #          Marketing consumers of this table.
    # FORMULA: gross_revenue (already computed above — same sum(total_price))
    # WHY SEPARATE COLUMN: gross_revenue exists but its name alone doesn't
    #   communicate "before discount". Renaming gross_revenue would break
    #   existing downstream queries, so we add a clear alias alongside it.
    # -------------------------------------------------------------------------
    log_message("  Adding gross_order_value_before_discount...")
    coupon_metrics['gross_order_value_before_discount'] = coupon_metrics['gross_revenue']

    # Round monetary values
    for col in ['total_discount_given', 'gross_revenue', 'avg_order_value',
                'gross_order_value_before_discount']:
        coupon_metrics[col] = coupon_metrics[col].round(2)

    coupon_metrics = coupon_metrics.sort_values(
        ['date', 'usage_count'], ascending=[True, False]
    )

    log_message(f"✓ Created {len(coupon_metrics)} coupon-day records")
    log_message(f"  Unique coupons: {coupon_metrics['discount_coupon_code'].nunique()}")
    log_message(f"  Total discount given: ${coupon_metrics['total_discount_given'].sum():,.2f}")
    log_message(f"  Total gross revenue:  ${coupon_metrics['gross_revenue'].sum():,.2f}")
    log_message(f"  Total net revenue:    ${coupon_metrics['net_revenue'].sum():,.2f}")

    log_message("  Coupon breakdown:")
    summary = coupon_metrics.groupby('discount_coupon_code').agg(
        usage_count=('usage_count', 'sum'),
        total_discount=('total_discount_given', 'sum')
    ).sort_values('usage_count', ascending=False)

    for code, row in summary.iterrows():
        log_message(f"    {code}: {row['usage_count']} uses, ${row['total_discount']:,.2f} discount")

    return coupon_metrics


# ==============================================================================
# SAVE & MAIN
# ==============================================================================

def save_to_csv(df, filename):
    """
    Saves DataFrame to CSV with error handling

    Args:
        df (DataFrame): Data to save
        filename (str): Output filename
    """
    if df is None or df.empty:
        log_message(f"⚠ Skipping save - {filename} has no data")
        return

    try:
        filepath = os.path.join(Config.AGGREGATED_DATA_DIR, filename)
        df.to_csv(filepath, index=False)
        log_message(f"✓ Saved: {filename} ({len(df)} rows)")
    except Exception as e:
        log_message(f"✗ Error saving {filename}: {str(e)}")


def main():
    """
    Main execution function - orchestrates entire pipeline

    WORKFLOW:
    1. Setup directories
    2. Load all raw data (with coupon & price validation)
    3. Create each aggregated table
    4. Save all aggregated tables
    5. Log summary

    TO RUN:
        python ecommerce_data_processor.py

    TO SCHEDULE DAILY (Linux/Mac):
        crontab -e
        Add: 0 1 * * * /usr/bin/python3 /path/to/ecommerce_data_processor.py

    TO SCHEDULE DAILY (Windows):
        Use Task Scheduler to run at 1 AM daily
    """
    start_time = datetime.now()

    log_message("\n" + "="*60)
    log_message("E-COMMERCE DATA AGGREGATION PIPELINE")
    log_message("="*60)
    log_message(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    Config.setup_directories()

    # STEP 1: Load all raw data
    data = load_all_raw_data()

    if data['sessions'] is None or data['orders'] is None:
        log_message("\n✗ CRITICAL: Missing core data (sessions or orders)")
        log_message("Cannot continue without minimum required data")
        return

    # STEP 2: Create aggregated tables
    daily_metrics  = create_daily_business_metrics(data['orders'], data['sessions'], data['users'])
    session_attr   = create_session_attribution(data['sessions'], data['orders'])
    funnel         = create_session_funnel(data['sessions'], data['pageviews'], data['cart'], data['orders'])
    product_perf   = create_product_performance_daily(data['order_items'], data['cart'], data['pageviews'])
    user_ltv       = create_user_lifetime_metrics(data['users'], data['orders'])
    page_engagement = create_page_engagement_metrics(data['pageviews'], data['scrolls'], data['clicks'])
    coupon_perf    = create_coupon_performance(data['orders'])

    # STEP 3: Save all aggregated tables
    log_message("\n" + "="*60)
    log_message("SAVING AGGREGATED TABLES")
    log_message("="*60)

    save_to_csv(daily_metrics,   'daily_business_metrics.csv')
    save_to_csv(session_attr,    'session_attribution.csv')
    save_to_csv(funnel,          'session_funnel.csv')
    save_to_csv(product_perf,    'product_performance_daily.csv')
    save_to_csv(user_ltv,        'user_lifetime_metrics.csv')
    save_to_csv(page_engagement, 'page_engagement_metrics.csv')
    save_to_csv(coupon_perf,     'coupon_performance.csv')

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    log_message("\n" + "="*60)
    log_message("PIPELINE COMPLETE")
    log_message("="*60)
    log_message(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"Duration: {duration:.2f} seconds")
    log_message(f"Aggregated files saved to: {Config.AGGREGATED_DATA_DIR}")
    log_message("="*60)


# ==============================================================================
# RUN
# ==============================================================================

if __name__ == "__main__":
    main()