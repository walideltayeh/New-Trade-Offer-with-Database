import os
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get Supabase client instance.
    
    Returns:
        Client: Supabase client
    """
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    
    return create_client(supabase_url, supabase_key)

# Create tables if they don't exist
def create_tables():
    """
    This function doesn't create tables as in Supabase you would typically
    create tables through the web interface or migrations.
    For this app, you should manually create the tables in Supabase.
    
    Tables needed:
    1. orders - to store order information
    2. gifts - to store gift information related to orders
    """
    # In a production environment, you might implement SQL migrations here
    # But for simplicity, we assume the tables exist in Supabase
    pass

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
        int: ID of the saved order
    """
    supabase = get_supabase_client()
    
    try:
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
        # Log the error
        print(f"Error saving order: {str(e)}")
        raise e

def get_all_orders():
    """
    Get all orders from the database
    
    Returns:
        list: List of order dictionaries
    """
    supabase = get_supabase_client()
    
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

# Initialize the database tables if needed
# Note: in Supabase, tables should be created manually
# This is just a placeholder to match the original structure
create_tables()