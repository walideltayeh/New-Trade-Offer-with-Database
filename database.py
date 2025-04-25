import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get Supabase client instance.
    
    Returns:
        Client: Supabase client or None if not configured
    """
    supabase_url = os.environ.get('SUPABASE_URL', 'https://annhckycdhpbqwhvcrrd.supabase.co')
    supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFubmhja3ljZGhwYnF3aHZjcnJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU1MzEzNjAsImV4cCI6MjA2MTEwNzM2MH0.xcgjkXn5jayBZqBaiaF83brRhO-H6t4M8nnCgIbXJ_s')
    
    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")
        print("The app will run in demo mode with database features disabled.")
        print("To enable database functionality:")
        print("1. Make sure your SUPABASE_URL and SUPABASE_KEY are correct")
        print("2. Run the SQL statements below in your Supabase SQL editor")
        print_table_creation_sql()
        return None

# Check tables and display SQL for creating them if needed
def check_tables():
    """
    Check if the necessary tables exist in Supabase.
    If they don't, print the SQL needed to create them.
    
    Tables needed:
    1. orders - to store order information
    2. gifts - to store gift information related to orders
    """
    supabase = get_supabase_client()
    
    # If no supabase client, just return (error already logged)
    if not supabase:
        return
        
    tables_exist = True
    
    try:
        # Check if orders table exists
        try:
            orders_check = supabase.table('orders').select('count').limit(1).execute()
            print("Orders table exists")
        except Exception as e:
            tables_exist = False
            print(f"Orders table does not exist: {str(e)}")
                
        # Check if gifts table exists
        try:
            gifts_check = supabase.table('gifts').select('count').limit(1).execute()
            print("Gifts table exists")
        except Exception as e:
            tables_exist = False
            print(f"Gifts table does not exist: {str(e)}")
        
        # If tables don't exist, print the SQL to create them
        if not tables_exist:
            print_table_creation_sql()
                
    except Exception as e:
        print(f"Error checking tables: {str(e)}")
        print_table_creation_sql()

# Print SQL for creating tables
def print_table_creation_sql():
    """
    Print the SQL statements needed to create the tables in Supabase.
    """
    # SQL for orders table
    orders_table_sql = """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        customer_name VARCHAR(255) NOT NULL,
        customer_address TEXT,
        customer_type VARCHAR(50) NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_order_value FLOAT NOT NULL,
        quantities JSONB NOT NULL,
        prices JSONB NOT NULL,
        total_weight_g INTEGER NOT NULL,
        eligible_tier VARCHAR(50),
        roi_percentage FLOAT,
        budget FLOAT
    );
    """
    
    # SQL for gifts table
    gifts_table_sql = """
    CREATE TABLE IF NOT EXISTS gifts (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL,
        gift_type VARCHAR(50) NOT NULL,
        quantity INTEGER NOT NULL,
        value FLOAT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    """
    
    print("\n=========== IMPORTANT: DATABASE SETUP ===========")
    print("Please execute these SQL statements in your Supabase SQL editor:")
    print("\n1. Create orders table:")
    print(orders_table_sql)
    print("\n2. Create gifts table:")
    print(gifts_table_sql)
    print("===============================================")

# Helper functions for orders
def save_order(customer_name, customer_address, customer_type, 
               total_order_value, quantities, prices, total_weight_g, 
               eligible_tier, roi_percentage, budget, gifts):
    """
    Save an order to the Supabase database
    
    Args:
        customer_name (str): Name of the customer
        customer_address (str): Address of the customer
        customer_type (str): Type of customer ('Retailer' or 'Tobacco Shop')
        total_order_value (float): Total value of the order
        quantities (dict): Quantities of each size
        prices (dict): Prices of each size
        total_weight_g (int): Total weight in grams
        eligible_tier (str): Eligible tier ('Silver', 'Gold', etc.)
        roi_percentage (float): ROI percentage
        budget (float): Budget allocated
        gifts (dict): Gift quantities (e.g., {"Pack FOC": 5, "Hookah": 1})
        
    Returns:
        int: ID of the saved order or -1 if tables don't exist
    """
    supabase = get_supabase_client()
    
    if not supabase:
        # This is a demonstration without a real connection
        import time
        
        # Create a dummy order in the demo mode
        # This will help simulate the order history page working too
        from app import create_excel_download_link
        
        # Save order to a global list for demo mode
        if not hasattr(save_order, 'demo_orders'):
            save_order.demo_orders = []
            
        order_id = int(time.time())
        demo_order = {
            "id": order_id,
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_type": customer_type,
            "order_date": datetime.now().isoformat(),
            "total_order_value": total_order_value,
            "quantities": quantities,
            "prices": prices,
            "total_weight_g": total_weight_g,
            "eligible_tier": eligible_tier,
            "roi_percentage": roi_percentage,
            "budget": budget
        }
        
        save_order.demo_orders.append(demo_order)
        
        # Create demo gifts
        if not hasattr(save_order, 'demo_gifts'):
            save_order.demo_gifts = []
            
        for gift_type, quantity in gifts.items():
            if quantity > 0:
                gift_value = quantity * (38 if gift_type == "Pack FOC" else 400)
                
                gift_data = {
                    "id": len(save_order.demo_gifts) + 1,
                    "order_id": order_id,
                    "gift_type": gift_type,
                    "quantity": quantity,
                    "value": gift_value
                }
                
                save_order.demo_gifts.append(gift_data)
        
        # Return a fake ID
        return order_id
    
    try:
        # First check if tables exist
        try:
            tables_check = supabase.table('orders').select('count').limit(1).execute()
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Tables don't exist yet, show a clear message
                print("\n===== DATABASE TABLES NOT CREATED =====")
                print("The database tables haven't been created in Supabase yet.")
                print("Please create the tables as instructed in the SQL statements below:")
                print_table_creation_sql()
                print("======================================\n")
                raise ValueError("Database tables not created yet. Please create the tables in Supabase first using the SQL statements shown above.")
            else:
                # Some other error
                raise e
    
        # Create new order
        order_data = {
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_type": customer_type,
            "order_date": datetime.now().isoformat(),
            "total_order_value": total_order_value,
            "quantities": quantities,
            "prices": prices,
            "total_weight_g": total_weight_g,
            "eligible_tier": eligible_tier,
            "roi_percentage": roi_percentage,
            "budget": budget
        }
        
        # Insert order into Supabase
        response = supabase.table('orders').insert(order_data).execute()
        
        # Get the inserted order's ID
        order_id = response.data[0]['id']
        
        # Create gift records
        for gift_type, quantity in gifts.items():
            if quantity > 0:
                # Calculate gift value
                gift_value = quantity * (38 if gift_type == "Pack FOC" else 400)
                
                gift_data = {
                    "order_id": order_id,
                    "gift_type": gift_type,
                    "quantity": quantity,
                    "value": gift_value
                }
                
                # Insert gift into Supabase
                supabase.table('gifts').insert(gift_data).execute()
        
        return order_id
    
    except Exception as e:
        # Log the error with detailed information
        import traceback
        error_details = traceback.format_exc()
        print(f"Error saving order: {str(e)}")
        print(f"Error details:\n{error_details}")
        
        # Re-raise with a more user-friendly message
        if "relation" in str(e) and "does not exist" in str(e):
            raise ValueError("Database tables not created yet. Please create the tables in Supabase first.")
        else:
            raise e

def get_all_orders():
    """
    Get all orders from the database
    
    Returns:
        list: List of order dictionaries
    """
    supabase = get_supabase_client()
    
    # If no supabase client, return demo orders if any
    if not supabase:
        if hasattr(save_order, 'demo_orders'):
            return save_order.demo_orders
        return []
    
    try:
        # Get all orders from Supabase, ordered by date descending
        response = supabase.table('orders').select('*').order('order_date', desc=True).execute()
        return response.data
    
    except Exception as e:
        print(f"Error getting orders: {str(e)}")
        return []

def get_order_by_id(order_id):
    """
    Get an order by ID
    
    Args:
        order_id (int): ID of the order
        
    Returns:
        dict: Order data or None if not found
    """
    supabase = get_supabase_client()
    
    # If no supabase client, return None (demo mode)
    if not supabase:
        return None
    
    try:
        response = supabase.table('orders').select('*').eq('id', order_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    
    except Exception as e:
        print(f"Error getting order by ID: {str(e)}")
        return None

def get_gifts_for_order(order_id):
    """
    Get gifts for an order
    
    Args:
        order_id (int): ID of the order
        
    Returns:
        list: List of gift dictionaries
    """
    supabase = get_supabase_client()
    
    # If no supabase client, return demo gifts if any
    if not supabase:
        if hasattr(save_order, 'demo_gifts'):
            return [gift for gift in save_order.demo_gifts if gift['order_id'] == order_id]
        return []
    
    try:
        response = supabase.table('gifts').select('*').eq('order_id', order_id).execute()
        return response.data
    
    except Exception as e:
        print(f"Error getting gifts for order: {str(e)}")
        return []

def orders_to_dataframe():
    """
    Convert all orders to a pandas DataFrame
    
    Returns:
        pandas.DataFrame: DataFrame of orders
    """
    orders = get_all_orders()
    
    # Create a list to store order data
    order_data = []
    
    for order in orders:
        # Get gifts for the order
        gifts = get_gifts_for_order(order['id'])
        
        # Calculate total gift value
        total_gift_value = sum(gift['value'] for gift in gifts)
        
        # Convert quantities from JSON to string
        quantities_str = ", ".join([f"{size}: {qty}" for size, qty in order['quantities'].items() if qty > 0])
        
        # Get gift quantities
        gift_dict = {gift['gift_type']: gift['quantity'] for gift in gifts}
        
        # Add order to the list
        order_data.append({
            "Order ID": order['id'],
            "Date": order['order_date'],
            "Customer Name": order['customer_name'],
            "Customer Type": order['customer_type'],
            "Order Value": order['total_order_value'],
            "Quantities": quantities_str,
            "Total Weight (kg)": order['total_weight_g'] / 1000,
            "Tier": order['eligible_tier'],
            "ROI %": order['roi_percentage'],
            "Budget": order['budget'],
            "Pack FOC": gift_dict.get("Pack FOC", 0),
            "Hookah": gift_dict.get("Hookah", 0),
            "Total Gift Value": total_gift_value
        })
    
    # Convert to DataFrame
    return pd.DataFrame(order_data) if order_data else pd.DataFrame()

# Initialize the database tables if needed and print SQL to create tables if they don't exist
print_table_creation_sql()
check_tables()