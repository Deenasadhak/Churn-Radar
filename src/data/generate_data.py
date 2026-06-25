import pandas as pd
import numpy as np
from faker import Faker
import os
from datetime import datetime, timedelta

# 1. Configuration & Setup
fake = Faker()
Faker.seed(42)  # Ensures reproducibility
np.random.seed(42)

NUM_CUSTOMERS = 12000
# Dynamically resolve the path to the data/raw folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')

# Workhorse Business Parameters
REGIONS = ['India', 'SEA', 'US']
TIERS = {'Starter': 99, 'Growth': 499, 'Enterprise': 2499}

def generate_dim_customer():
    print("Generating dim_customer...")
    customer_ids = [f"CUST-{str(i).zfill(5)}" for i in range(NUM_CUSTOMERS)]
    
    data = {
        'customer_id': customer_ids,
        'company_name': [fake.company() for _ in range(NUM_CUSTOMERS)],
        'region': np.random.choice(REGIONS, NUM_CUSTOMERS, p=[0.4, 0.2, 0.4]),
        'subscription_tier': np.random.choice(list(TIERS.keys()), NUM_CUSTOMERS, p=[0.5, 0.35, 0.15]),
        'signup_date': [fake.date_between(start_date='-2y', end_date='-6m') for _ in range(NUM_CUSTOMERS)],
        'is_active': np.random.choice([True, False], NUM_CUSTOMERS, p=[0.85, 0.15]) # ~15% historic churn
    }
    
    df = pd.DataFrame(data)
    df['monthly_revenue'] = df['subscription_tier'].map(TIERS)
    return df

def generate_dim_date():
    print("Generating dim_date...")
    start_date = datetime.now() - timedelta(days=730) # 2 years ago
    date_list = [start_date + timedelta(days=x) for x in range(730)]
    
    df = pd.DataFrame({'calendar_date': date_list})
    df['date_id'] = df['calendar_date'].dt.strftime('%Y%m%d').astype(int)
    df['day_of_week'] = df['calendar_date'].dt.day_name()
    df['month'] = df['calendar_date'].dt.month
    df['year'] = df['calendar_date'].dt.year
    return df

def generate_fact_usage_event(customers_df):
    print("Generating fact_usage_event (This simulates 30 days of logs, it may take a moment)...")
    active_customers = customers_df[customers_df['is_active']]['customer_id'].tolist()
    
    # Simulate the last 30 days of usage for active customers
    base_date = datetime.now() - timedelta(days=30)
    dates = [base_date + timedelta(days=x) for x in range(30)]
    
    records = []
    for cust_id in active_customers:
        # Introduce "Quiet Quitters" - 10% of active users have dropping usage
        is_quiet_quitter = np.random.random() < 0.10 
        base_logins = np.random.randint(5, 25)
        
        for i, d in enumerate(dates):
            # If quiet quitter, logins drop as days go on
            daily_logins = max(0, base_logins - int(i/2)) if is_quiet_quitter else np.random.poisson(base_logins)
            
            if daily_logins > 0:
                records.append({
                    'event_id': fake.uuid4(),
                    'customer_id': cust_id,
                    'activity_date': d.date(),
                    'logins': daily_logins,
                    'features_clicked': daily_logins * np.random.randint(1, 5)
                })
                
    return pd.DataFrame(records)

def generate_fact_support_ticket(customers_df):
    print("Generating fact_support_ticket...")
    # Simulate tickets over the last year
    num_tickets = int(NUM_CUSTOMERS * 2.5) 
    
    df = pd.DataFrame({
        'ticket_id': [f"TKT-{str(i).zfill(6)}" for i in range(num_tickets)],
        'customer_id': np.random.choice(customers_df['customer_id'], num_tickets),
        'created_date': [fake.date_between(start_date='-1y', end_date='today') for _ in range(num_tickets)],
        'category': np.random.choice(['Billing', 'Technical Bug', 'Feature Request', 'Onboarding'], num_tickets),
        'priority': np.random.choice(['Low', 'Medium', 'High', 'Urgent'], num_tickets, p=[0.4, 0.4, 0.15, 0.05]),
        'resolution_days': np.random.exponential(scale=2.0, size=num_tickets).astype(int)
    })
    return df

def generate_fact_subscription_event(customers_df):
    print("Generating fact_subscription_event...")
    # Generate baseline signup events for everyone
    events = []
    for _, row in customers_df.iterrows():
        events.append({
            'event_id': fake.uuid4(),
            'customer_id': row['customer_id'],
            'event_date': row['signup_date'],
            'event_type': 'Activation',
            'mrr_change': row['monthly_revenue']
        })
        
        # If they churned, add a cancellation event
        if not row['is_active']:
            cancel_date = row['signup_date'] + timedelta(days=np.random.randint(30, 365))
            if cancel_date < datetime.now().date():
                events.append({
                    'event_id': fake.uuid4(),
                    'customer_id': row['customer_id'],
                    'event_date': cancel_date,
                    'event_type': 'Cancellation',
                    'mrr_change': -row['monthly_revenue']
                })
                
    return pd.DataFrame(events)

if __name__ == "__main__":
    print(f"Starting Data Generation. Saving to: {RAW_DATA_DIR}")
    
    # Ensure directory exists
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    # Generate DataFrames
    df_customers = generate_dim_customer()
    df_dates = generate_dim_date()
    df_usage = generate_fact_usage_event(df_customers)
    df_support = generate_fact_support_ticket(df_customers)
    df_subs = generate_fact_subscription_event(df_customers)
    
    # Export to CSV
    df_customers.to_csv(os.path.join(RAW_DATA_DIR, 'dim_customer.csv'), index=False)
    df_dates.to_csv(os.path.join(RAW_DATA_DIR, 'dim_date.csv'), index=False)
    df_usage.to_csv(os.path.join(RAW_DATA_DIR, 'fact_usage_event.csv'), index=False)
    df_support.to_csv(os.path.join(RAW_DATA_DIR, 'fact_support_ticket.csv'), index=False)
    df_subs.to_csv(os.path.join(RAW_DATA_DIR, 'fact_subscription_event.csv'), index=False)
    
    print("\n✅ Success! All 5 raw CSV files have been generated.")