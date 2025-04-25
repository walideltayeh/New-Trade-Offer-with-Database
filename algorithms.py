import math
from models import CustomerType
from utils import calculate_gift_value, get_max_gift_quantities

def recommend_gift(order_data, customer_type, budget):
    """
    Recommend gifts based on order data, customer type, and budget
    
    Args:
        order_data (dict): Order summary data
        customer_type (CustomerType): Type of customer
        budget (float): Available budget
        
    Returns:
        dict: Recommended gift quantities
    """
    # Initialize gift quantities
    gift_quantities = {"Pack FOC": 0, "Hookah": 0}
    
    # Calculate total order weight
    total_order_weight_g = sum([
        order_data["quantities"].get("50g", 0) * 50,
        order_data["quantities"].get("250g", 0) * 250,
        order_data["quantities"].get("1kg", 0) * 1000
    ])
    
    # Convert to kg for easier comparison
    total_order_weight_kg = total_order_weight_g / 1000
    
    # Define gift prices
    pack_foc_price = 38
    hookah_price = 400
    
    # For Tobacco Shops, prioritize allocating hookahs based on order weight
    if customer_type == CustomerType.TOBACCO_SHOP:
        if total_order_weight_kg > 100 and budget >= 2 * hookah_price:
            # 2 hookahs for orders over 100kg if budget allows
            gift_quantities["Hookah"] = 2
            budget -= 2 * hookah_price
        elif total_order_weight_kg > 50 and budget >= hookah_price:
            # 1 hookah for orders over 50kg if budget allows
            gift_quantities["Hookah"] = 1
            budget -= hookah_price
    
    # Use ALL remaining budget for Pack FOC gifts
    # Calculate how many packs we can get with the remaining budget
    pack_count = int(budget / pack_foc_price)
    gift_quantities["Pack FOC"] = pack_count
    
    # Calculate how much budget is left after allocating whole packs
    budget_left = budget - (pack_count * pack_foc_price)
    
    # If there's still significant budget left (over 80% of a pack price), add one more pack
    if budget_left >= 0.8 * pack_foc_price:
        gift_quantities["Pack FOC"] += 1
    
    return gift_quantities

def calculate_budget_from_roi(order_data, target_roi_percentage):
    """
    Calculate the budget needed to achieve a target ROI
    
    Args:
        order_data (dict): Order summary data
        target_roi_percentage (float): Target ROI percentage
        
    Returns:
        float: Budget needed to achieve the target ROI
    """
    # Calculate budget as a percentage of total order value
    budget = order_data["total_value"] * (target_roi_percentage / 100)
    
    # Round to 2 decimal places
    budget = round(budget, 2)
    
    return budget

def optimize_budget(order_data, customer_type, target_roi_percentage):
    """
    Optimize gift allocation to achieve a target ROI
    
    Args:
        order_data (dict): Order summary data
        customer_type (CustomerType): Type of customer
        target_roi_percentage (float): Target ROI percentage
        
    Returns:
        dict: Optimized gift quantities
    """
    # Calculate budget based on target ROI
    budget = calculate_budget_from_roi(order_data, target_roi_percentage)
    
    # Simply use the improved recommend_gift function to allocate the entire budget
    # The recommend_gift function is now designed to fully utilize the budget
    gifts = recommend_gift(order_data, customer_type, budget)
    
    # The ROI should naturally approach the target given our improved budget utilization
    # No need for fine-tuning as we're already maximizing budget usage
    
    return gifts

def calculate_roi(order_data, gifts, budget):
    """
    Calculate ROI (Return on Investment) for the gifts
    
    Args:
        order_data (dict): Order summary data
        gifts (dict): Gift allocation
        budget (float): Budget allocated
        
    Returns:
        float: ROI percentage
    """
    # Calculate total gift value
    gift_value = (
        calculate_gift_value("Pack FOC", gifts.get("Pack FOC", 0)) +
        calculate_gift_value("Hookah", gifts.get("Hookah", 0))
    )
    
    # Calculate ROI as a percentage
    if order_data["total_value"] > 0:
        roi_percentage = (gift_value / order_data["total_value"]) * 100
    else:
        roi_percentage = 0
    
    return round(roi_percentage, 2)
