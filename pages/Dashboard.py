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
LAST UPDATED: 2026-02-17
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
        'net_revenue'
    ]

    available_columns = [col for col in output_columns if col in merged.columns]
    result_df = merged[available_columns].copy()

    # Round monetary values
    result_df['gross_revenue'] = result_df['gross_revenue'].round(2)
    result_df['discount_amount'] = result_df['discount_amount'].round(2)

    # Fill missing UTM / coupon values
    for col in ['utm_source', 'utm_medium', 'utm_campaign']:
        if col in result_df.columns:
            result_df[col] = result_df[col].fillna('direct')

    if 'discount_coupon_code' in result_df.columns:
        result_df['discount_coupon_code'] = result_df['discount_coupon_code'].fillna('NO_COUPON')

    log_message(f"✓ Created {len(result_df)} session records")
    log_message(f"  Converted sessions: {result_df['converted'].sum()}")
    log_message(f"  Conversion rate: {result_df['converted'].mean()*100:.2f}%")
    log_message(f"  Total gross revenue: ${result_df['gross_revenue'].sum():,.2f}")
    log_message(f"  Total net revenue:   ${result_df['net_revenue'].sum():,.2f}")

    return result_df


# ==============================================================================
# AGGREGATION FUNCTION 3: SESSION FUNNEL
# ==============================================================================

def create_session_funnel(sessions_df, pageviews_df, cart_df, orders_df):
    """
    Tracks each session's progress through the 5-step conversion funnel

    PURPOSE:
    - Identify exactly where users drop off
    - Calculate conversion rate at each funnel step
    - Optimize low-performing steps

    FUNNEL STEPS & URL LOGIC (path matching uses str.contains — partial match):
    ┌─────┬──────────────────────┬──────────────────────────────────────────────────────┐
    │Step │ Field                │ Path pattern matched in pageview_table               │
    ├─────┼──────────────────────┼──────────────────────────────────────────────────────┤
    │  1  │ had_category_view    │ contains '/category/security-cameras'                │
    │  2  │ had_product_view     │ contains '/products/' (all 4 product pages)          │
    │     │                      │   /products/video-doorbell-pro-2                     │
    │     │                      │   /products/ring-alarm-8-piece                       │
    │     │                      │   /products/indoor-cam-(2nd-gen)                     │
    │     │                      │   /products/stick-up-cam-battery                     │
    │  3  │ had_cart_view        │ contains '/cart'                                     │
    │  4  │ had_checkout         │ contains '/checkout/payment'                         │
    │  5  │ had_thank_you        │ contains '/checkout/thankyou'                        │
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
        cart_df (DataFrame): Add-to-cart data (not used in current funnel)
        orders_df (DataFrame): Order data (used for time metrics)

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
    # STEP 1: CATEGORY VIEW
    # Did this session view the security cameras category page?
    # Path pattern: contains '/category/security-cameras'
    # -------------------------------------------------------------------------
    log_message("  Checking category views (/category/security-cameras)...")
    funnel['had_category_view'] = funnel['session_id'].isin(
        sessions_with_path('/category/security-cameras')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 2: PRODUCT VIEW
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
    # STEP 3: CART VIEW
    # Did this session view the cart page?
    # Path pattern: contains '/cart'
    # -------------------------------------------------------------------------
    log_message("  Checking cart views (/cart)...")
    funnel['had_cart_view'] = funnel['session_id'].isin(
        sessions_with_path('/cart')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 4: CHECKOUT
    # Did this session reach the checkout/payment page?
    # Path pattern: contains '/checkout/payment'
    # -------------------------------------------------------------------------
    log_message("  Checking checkout views (/checkout/payment)...")
    funnel['had_checkout'] = funnel['session_id'].isin(
        sessions_with_path('/checkout/payment')
    ).astype(int)

    # -------------------------------------------------------------------------
    # STEP 5: THANK YOU PAGE (ORDER CONFIRMED)
    # Did this session reach the thank you / order confirmed page?
    # Path pattern: contains '/checkout/thankyou'
    # NOTE: This is the definitive signal of a completed purchase.
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

    # Time from session start → first category page view
    if pageviews_df is not None:
        first_category = pageviews_df[
            pageviews_df['path'].str.contains('/category/security-cameras', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_category.columns = ['session_id', 'first_category_time']

        funnel = funnel.merge(first_category, on='session_id', how='left')
        funnel['time_to_category_minutes'] = (
            (funnel['first_category_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_category_time'])
    else:
        funnel['time_to_category_minutes'] = None

    # Time from session start → first product page view
    if pageviews_df is not None:
        first_product = pageviews_df[
            pageviews_df['path'].str.contains('/products/', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_product.columns = ['session_id', 'first_product_time']

        funnel = funnel.merge(first_product, on='session_id', how='left')
        funnel['time_to_product_minutes'] = (
            (funnel['first_product_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_product_time'])
    else:
        funnel['time_to_product_minutes'] = None

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

    # Time from session start → checkout page
    if pageviews_df is not None:
        first_checkout = pageviews_df[
            pageviews_df['path'].str.contains('/checkout/payment', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_checkout.columns = ['session_id', 'first_checkout_time']

        funnel = funnel.merge(first_checkout, on='session_id', how='left')
        funnel['time_to_checkout_minutes'] = (
            (funnel['first_checkout_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_checkout_time'])
    else:
        funnel['time_to_checkout_minutes'] = None

    # Time from session start → thank you page (order confirmed)
    if pageviews_df is not None:
        first_thankyou = pageviews_df[
            pageviews_df['path'].str.contains('/checkout/thankyou', case=False, na=False)
        ].groupby('session_id')['time'].min().reset_index()
        first_thankyou.columns = ['session_id', 'first_thankyou_time']

        funnel = funnel.merge(first_thankyou, on='session_id', how='left')
        funnel['time_to_thankyou_minutes'] = (
            (funnel['first_thankyou_time'] - funnel['time']).dt.total_seconds() / 60
        ).round(2)
        funnel = funnel.drop(columns=['first_thankyou_time'])
    else:
        funnel['time_to_thankyou_minutes'] = None

    # -------------------------------------------------------------------------
    # OUTPUT
    # -------------------------------------------------------------------------
    output_columns = [
        'session_id',
        'user_id',
        'date',
        'had_category_view',     # Step 1: /category/security-cameras
        'had_product_view',      # Step 2: /products/*
        'had_cart_view',         # Step 3: /cart
        'had_checkout',          # Step 4: /checkout/payment
        'had_thank_you',         # Step 5: /checkout/thankyou
        'time_to_category_minutes',
        'time_to_product_minutes',
        'time_to_cart_minutes',
        'time_to_checkout_minutes',
        'time_to_thankyou_minutes'
    ]

    result_df = funnel[output_columns].copy()

    # Log funnel breakdown
    total = len(result_df)
    funnel_steps = [
        ('Category View',       'had_category_view'),
        ('Product View',        'had_product_view'),
        ('Cart View',           'had_cart_view'),
        ('Checkout',            'had_checkout'),
        ('Thank You (Purchase)', 'had_thank_you'),
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
    else:
        product_metrics['times_added_to_cart'] = 0
        product_metrics['cart_to_purchase_rate'] = 0

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

    # Round monetary values
    for col in ['total_discount_given', 'gross_revenue', 'avg_order_value']:
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