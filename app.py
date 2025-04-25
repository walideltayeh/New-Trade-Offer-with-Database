import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import xlsxwriter
import base64
from datetime import datetime
from utils import load_csv, validate_csv, generate_order_summary, is_eligible_for_gift, calculate_gift_value, get_max_gift_quantities
from algorithms import recommend_gift, optimize_budget, calculate_roi, calculate_budget_from_roi
from models import CustomerType
from database import save_order

# Default price data if not provided
DEFAULT_PRICES = pd.DataFrame({
    "Size": ["50g", "250g", "1kg"],
    "Price/Pack": [32.80, 176.81, 638.83]
})

def create_excel_download_link(df, filename, link_text="Download as Excel"):
    """
    Create a download link for a pandas DataFrame as an Excel file

    Args:
        df (pandas.DataFrame): DataFrame to export
        filename (str): Name of the file
        link_text (str): Text to display for the link

    Returns:
        str: HTML string containing the download link
    """
    # Create a BytesIO buffer
    buffer = io.BytesIO()

    # Create ExcelWriter object with XlsxWriter engine
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Write DataFrame to Excel
        df.to_excel(writer, index=False, sheet_name='Sheet1')

        # Close the Pandas Excel writer
        writer.close()

    # Get the value of the BytesIO buffer
    excel_data = buffer.getvalue()

    # Generate a base64 encoded string
    b64 = base64.b64encode(excel_data).decode()

    # Generate download link
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{link_text}</a>'

    return href

def display_gift_summary(gifts, budget, customer_type, order_data, gift_values=None):
    """
    Display a summary of the gift allocation

    Args:
        gifts (dict): Dictionary of gift quantities
        budget (float): Available budget
        customer_type (CustomerType): Type of customer
        order_data (dict): Order summary data
        gift_values (dict, optional): Dictionary of gift values. Defaults to None.
    """
    if gift_values is None:
        gift_values = {
            "Pack FOC": gifts.get("Pack FOC", 0) * 38,
            "Hookah": gifts.get("Hookah", 0) * 400
        }

    # Create DataFrame for gift summary
    gift_df = pd.DataFrame({
        "Gift Type": list(gift_values.keys()),
        "Quantity": [gifts.get(gift, 0) for gift in gift_values.keys()],
        "Value": [gift_values[gift] for gift in gift_values.keys()]
    })

    # Display gift summary in a table
    st.write("### Gift Summary")
    st.dataframe(gift_df, use_container_width=True)

    # Calculate total gift value and remaining budget
    total_gift_value = sum(gift_values.values())
    remaining_budget = budget - total_gift_value

    # Display budget metrics
    budget_cols = st.columns(4)
    with budget_cols[0]:
        st.metric("Available Budget", f"${budget:.2f}")
    with budget_cols[1]:
        st.metric("Total Gift Value", f"${total_gift_value:.2f}")
    with budget_cols[2]:
        st.metric("Remaining Budget", f"${remaining_budget:.2f}")
    with budget_cols[3]:
        # Calculate actual ROI
        actual_roi = calculate_roi(order_data, gifts, budget)
        st.metric("Actual ROI", f"{actual_roi:.2f}%")

    # Create a pie chart showing gift value distribution
    gift_values_filtered = {k: v for k, v in gift_values.items() if v > 0}
    if gift_values_filtered:
        fig = px.pie(
            values=list(gift_values_filtered.values()),
            names=list(gift_values_filtered.keys()),
            title="Gift Value Distribution"
        )
        # Add a unique key to prevent duplicate chart ID errors
        chart_key = f"chart_{hash(str(gifts))}_{hash(str(budget))}"
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

    # Create export data
    export_data = pd.DataFrame([
        {"Category": "Customer Information", "Item": "Customer Name", "Value": st.session_state.customer_name if 'customer_name' in st.session_state and st.session_state.customer_name else "N/A"},
        {"Category": "Customer Information", "Item": "Customer Address", "Value": st.session_state.customer_address if 'customer_address' in st.session_state and st.session_state.customer_address else "N/A"},
        {"Category": "Customer Information", "Item": "Customer Type", "Value": "Tobacco Shop" if customer_type == CustomerType.TOBACCO_SHOP else "Retailer"},
        {"Category": "Order Information", "Item": "Total Order Value", "Value": f"${order_data['total_value']:.2f}"},
        {"Category": "Order Information", "Item": "Number of 50g Packs", "Value": str(order_data['quantities'].get('50g', 0))},
        {"Category": "Order Information", "Item": "Number of 250g Packs", "Value": str(order_data['quantities'].get('250g', 0))},
        {"Category": "Order Information", "Item": "Number of 1kg Packs", "Value": str(order_data['quantities'].get('1kg', 0))},
        {"Category": "Gift Details", "Item": "Pack FOC Quantity", "Value": str(gifts.get("Pack FOC", 0))},
        {"Category": "Gift Details", "Item": "Hookah Quantity", "Value": str(gifts.get("Hookah", 0))},
        {"Category": "Budget Information", "Item": "Available Budget", "Value": f"${budget:.2f}"},
        {"Category": "Budget Information", "Item": "Total Gift Value", "Value": f"${total_gift_value:.2f}"},
        {"Category": "Budget Information", "Item": "Remaining Budget", "Value": f"${remaining_budget:.2f}"},
        {"Category": "Budget Information", "Item": "Actual ROI", "Value": f"{actual_roi:.2f}%"}
    ])

    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create download link
    download_link = create_excel_download_link(export_data, f"al_fakher_offer_{timestamp}.xlsx")

    # Display download link
    st.markdown(download_link, unsafe_allow_html=True)

def adjust_gifts_for_tier_roi(order_data, eligible_tier, custom_gifts, budget):
    """
    Adjust gift quantities to maintain the ROI percentage of the eligible tier

    Args:
        order_data (dict): Order summary data
        eligible_tier (str): Name of the eligible tier (e.g., 'Silver', 'Gold')
        custom_gifts (dict): Current custom gift quantities
        budget (float): Available budget

    Returns:
        dict: Adjusted gift quantities
    """
    if not eligible_tier:
        return custom_gifts

    # Define tier ROI percentages
    tier_roi = {
        'Silver': 13.0,
        'Gold': 14.5,
        'Diamond': 16.0,
        'Platinum': 18.0
    }

    # Calculate current ROI with custom gifts
    current_roi = calculate_roi(order_data, custom_gifts, budget)

    # Get target ROI for the tier
    target_roi = tier_roi.get(eligible_tier, 13.0)

    # If current ROI is already lower than or equal to target, no adjustment needed
    if current_roi <= target_roi:
        return custom_gifts

    # Clone the gifts to avoid modifying the original
    adjusted_gifts = custom_gifts.copy()

    # Gradually reduce Pack FOC until ROI is below or equal to target
    while calculate_roi(order_data, adjusted_gifts, budget) > target_roi:
        if adjusted_gifts.get("Pack FOC", 0) > 0:
            adjusted_gifts["Pack FOC"] = max(0, adjusted_gifts["Pack FOC"] - 1)
        else:
            # If Pack FOC is also 0, reduce Hookah if present
            if adjusted_gifts.get("Hookah", 0) > 0:
                adjusted_gifts["Hookah"] = max(0, adjusted_gifts["Hookah"] - 1)
            else:
                # Cannot reduce further
                break

    return adjusted_gifts

def reset_all_calculations():
    """
    Reset all calculation-related session state variables but keep customer info and price data
    """
    # Get current price data and customer info
    price_data = st.session_state.get('price_data', DEFAULT_PRICES)
    customer_name = st.session_state.get('customer_name', "")
    customer_address = st.session_state.get('customer_address', "")
    customer_type = st.session_state.get('customer_type', CustomerType.RETAILER)

    # Get list of keys to preserve
    preserve_keys = ['price_data', 'customer_name', 'customer_address', 'customer_type']

    # Clear all custom gift related session state
    custom_gift_keys = [
        'custom_pack_foc', 'custom_hookah',
        'original_gifts', 'custom_gifts', 'applied_custom_gifts'
    ]
    for key in custom_gift_keys:
        if key in st.session_state:
            del st.session_state[key]

    # Clear other calculation variables
    for key in list(st.session_state.keys()):
        if key not in preserve_keys and not key.startswith('_'):
            try:
                del st.session_state[key]
            except:
                pass  # Ignore any keys that can't be deleted

    # Restore price data and customer info
    st.session_state.price_data = price_data
    st.session_state.customer_name = customer_name
    st.session_state.customer_address = customer_address
    st.session_state.customer_type = customer_type

def main():
    # Use the session state for price data
    if 'price_data' not in st.session_state or st.session_state.price_data is None:
        st.session_state.price_data = DEFAULT_PRICES

    # Initialize customer information in session state if not present
    if 'customer_name' not in st.session_state:
        st.session_state.customer_name = ""
    if 'customer_address' not in st.session_state:
        st.session_state.customer_address = ""

    # Customer information section
    st.header("Customer Information")
    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input("Customer Name", value=st.session_state.customer_name)
        st.session_state.customer_name = customer_name

    with col2:
        customer_address = st.text_area("Customer Address", value=st.session_state.customer_address, height=100)
        st.session_state.customer_address = customer_address

    # Order input section
    st.header("Order Information")

    # Customer type selection with reset callback
    def reset_on_customer_type_change():
        # Clear gift calculations when customer type changes
        if 'original_gifts' in st.session_state:
            del st.session_state['original_gifts']
        if 'custom_gifts' in st.session_state:
            del st.session_state['custom_gifts']
        if 'applied_custom_gifts' in st.session_state:
            del st.session_state['applied_custom_gifts']
        if 'custom_pack_foc' in st.session_state:
            del st.session_state['custom_pack_foc']
        if 'custom_hookah' in st.session_state:
            del st.session_state['custom_hookah']
    
    # Get current index
    current_index = 0
    if 'customer_type' in st.session_state:
        if st.session_state.customer_type == CustomerType.TOBACCO_SHOP:
            current_index = 1
    
    customer_type_str = st.radio(
        "Customer Type",
        ["Retailer", "Tobacco Shop"],
        index=current_index,
        horizontal=True,
        key="customer_type_radio",
        on_change=reset_on_customer_type_change
    )
    customer_type = CustomerType.RETAILER if customer_type_str == "Retailer" else CustomerType.TOBACCO_SHOP
    
    # Store customer type in session state
    st.session_state.customer_type = customer_type

    # Package quantities
    st.subheader("Enter Package Quantities")

    # Create 3 columns for the 3 package sizes
    col1, col2, col3 = st.columns(3)

    # Define callback functions to reset calculations when quantities change
    def reset_on_qty_change():
        # Clear gift calculations when quantities change
        if 'original_gifts' in st.session_state:
            del st.session_state['original_gifts']
        if 'custom_gifts' in st.session_state:
            del st.session_state['custom_gifts']
        if 'applied_custom_gifts' in st.session_state:
            del st.session_state['applied_custom_gifts']
        if 'custom_pack_foc' in st.session_state:
            del st.session_state['custom_pack_foc']
        if 'custom_hookah' in st.session_state:
            del st.session_state['custom_hookah']
    
    with col1:
        qty_50g = st.number_input("50g Packs", min_value=0, value=0, step=1, 
                                  key="qty_50g", on_change=reset_on_qty_change)

    with col2:
        qty_250g = st.number_input("250g Packs", min_value=0, value=0, step=1, 
                                  key="qty_250g", on_change=reset_on_qty_change)

    with col3:
        qty_1kg = st.number_input("1kg Packs", min_value=0, value=0, step=1, 
                                 key="qty_1kg", on_change=reset_on_qty_change)

    # Create order quantities dictionary
    quantities = {
        "50g": qty_50g,
        "250g": qty_250g,
        "1kg": qty_1kg
    }

    # Generate order summary
    order_data = generate_order_summary(st.session_state.price_data, quantities)

    # Calculate total grams ordered
    total_grams = 0
    for size, quantity in order_data["quantities"].items():
        if size == "50g":
            total_grams += quantity * 50
        elif size == "250g":
            total_grams += quantity * 250
        elif size == "1kg":
            total_grams += quantity * 1000

    # Check if 1kg size was ordered for tier eligibility
    has_1kg_order = order_data["quantities"].get("1kg", 0) > 0

    # Get eligible tier
    if total_grams < 6000:
        # Not eligible for any gifts
        is_eligible = False
        eligible_tier = "Silver"  # Default to Silver, but won't be shown if not eligible
    else:
        is_eligible = True
        eligible_tier = "Silver"
        if total_grams >= 246050 and has_1kg_order:
            eligible_tier = "Platinum"
        elif total_grams >= 126050 and has_1kg_order:
            eligible_tier = "Diamond"
        elif total_grams >= 66050 and has_1kg_order:
            eligible_tier = "Gold"

    # Display order summary
    st.subheader("Order Summary")

    # Show total order value and tier status
    if is_eligible:
        st.success(f"Order Total: ${order_data['total_value']:.2f} - Total Weight: {total_grams/1000:.1f}kg")
        st.success(f"Eligible for **{eligible_tier}** tier")
    else:
        st.warning(f"Order Total: ${order_data['total_value']:.2f} - Total Weight: {total_grams/1000:.1f}kg")
        st.warning("This order is not eligible for gifts yet. Minimum order requirement: 6kg or more.")

    # Check gift eligibility based on specific product quantities
    product_eligible = is_eligible_for_gift(order_data)
    
    # Show the gift eligibility status
    if is_eligible and product_eligible:
        st.success("This order qualifies for promotional gifts!")
    elif is_eligible and not product_eligible:
        st.warning("This order meets weight requirements but doesn't meet product quantity requirements (10+ packs of 50g, 3+ packs of 250g, or 2+ packs of 1kg).")
    
    # Gift calculation section
    if is_eligible and product_eligible:
        st.header("Gift Calculation")
        
        # ROI percentage based on tier (fixed values)
        roi_options = {
            'Silver': 5.0,
            'Gold': 7.0,
            'Diamond': 9.0,
            'Platinum': 13.0
        }
        
        # Get the ROI for this tier
        target_roi = roi_options.get(eligible_tier, 5.0)
        
        cols = st.columns([2, 1])
        
        with cols[0]:
            st.subheader("Tier Information")
            st.info(f"**{eligible_tier} Tier**")
            st.markdown(f"""
            - ROI Percentage: **{target_roi}%**
            - This tier's ROI percentage is automatically applied based on the order's eligible tier.
            - No manual ROI adjustment is needed.
            """)
        
        with cols[1]:
            # Calculate budget based on ROI
            budget = calculate_budget_from_roi(order_data, target_roi)
            st.subheader("Budget")
            st.metric("Available Budget", f"${budget:.2f}")
            
            # Button to reset all custom gift calculations
            if st.button("Reset Calculations"):
                reset_all_calculations()
                st.rerun()
        
        # Gift recommendation and allocation
        if 'original_gifts' not in st.session_state:
            # Get gift recommendation
            recommended_gifts = recommend_gift(order_data, customer_type, budget)
            
            # Store original recommendation
            st.session_state.original_gifts = recommended_gifts
            st.session_state.custom_gifts = recommended_gifts.copy()
            st.session_state.applied_custom_gifts = False
            
            # Set custom gift quantities in session
            st.session_state.custom_pack_foc = recommended_gifts.get("Pack FOC", 0)
            st.session_state.custom_hookah = recommended_gifts.get("Hookah", 0)
            
        # Display recommended gifts
        st.subheader("Recommended Gifts")
        st.write(f"Based on the order value of ${order_data['total_value']:.2f} and target ROI of {target_roi:.1f}%, we recommend:")
        
        # Display original recommendation
        original_gift_values = {
            "Pack FOC": st.session_state.original_gifts.get("Pack FOC", 0) * 38,
            "Hookah": st.session_state.original_gifts.get("Hookah", 0) * 400
        }
        
        display_gift_summary(
            st.session_state.original_gifts, 
            budget,
            customer_type, 
            order_data,
            original_gift_values
        )
        
        # Add a prominent save order button right after the recommendation
        save_col1, save_col2 = st.columns([1, 2])
        with save_col1:
            if st.button("💾 Save Order", key="save_recommended_order", type="primary"):
                try:
                    # Get customer information
                    customer_name = st.session_state.customer_name
                    customer_address = st.session_state.customer_address
                    customer_type_str = "Tobacco Shop" if customer_type == CustomerType.TOBACCO_SHOP else "Retailer"
                    
                    # Use the recommended gifts
                    current_gifts = st.session_state.original_gifts
                    # Calculate total weight directly from quantities
                    total_grams = sum([
                        order_data["quantities"].get("50g", 0) * 50,
                        order_data["quantities"].get("250g", 0) * 250,
                        order_data["quantities"].get("1kg", 0) * 1000
                    ])
                    
                    # Save to database
                    order_id = save_order(
                        customer_name=customer_name,
                        customer_address=customer_address,
                        customer_type=customer_type_str,
                        total_order_value=order_data['total_value'],
                        quantities=order_data['quantities'],
                        prices=order_data['prices'],
                        total_weight_g=total_grams,
                        eligible_tier=eligible_tier,
                        roi_percentage=target_roi,
                        budget=budget,
                        gifts=current_gifts
                    )
                    
                    # Show success message
                    st.success(f"Order saved successfully with ID: {order_id}. View it in the Order History page.")
                    
                    # Reset calculation
                    reset_all_calculations()
                    
                    # Rerun to update UI
                    st.rerun()
                    
                except ValueError as e:
                    # Special handling for database table errors
                    st.error(str(e))
                    st.info("To use database functionality, you need to create the required tables in Supabase. Check the console for SQL statements.")
                except Exception as e:
                    st.error(f"Error saving order: {str(e)}")
        with save_col2:
            st.info("💡 Save this order with the recommended gift allocation, or customize below.")
        
        # Custom gift allocation section
        st.header("Custom Gift Allocation")
        st.write("Adjust gift quantities below to customize the offer:")
        
        # Calculate maximum quantities
        max_quantities = get_max_gift_quantities(budget, customer_type, order_data['total_value'])
        
        # Custom gift inputs
        col1, col2 = st.columns(2)
        
        with col1:
            pack_foc = st.slider("Pack FOC Quantity", 
                            min_value=0, 
                            max_value=max_quantities["Pack FOC"],
                            value=st.session_state.custom_pack_foc,
                            step=1)
            
            st.session_state.custom_pack_foc = pack_foc
        
        with col2:
            # Only show hookah slider for tobacco shops
            if customer_type == CustomerType.TOBACCO_SHOP:
                hookah = st.slider("Hookah Quantity", 
                            min_value=0, 
                            max_value=min(2, max_quantities["Hookah"]),
                            value=st.session_state.custom_hookah,
                            step=1)
            else:
                hookah = 0
                st.info("Hookah gifts are only available for Tobacco Shops")
            
            st.session_state.custom_hookah = hookah
        
        # Update custom gifts
        custom_gifts = {
            "Pack FOC": pack_foc,
            "Hookah": hookah
        }
        
        st.session_state.custom_gifts = custom_gifts
        
        # Apply custom gifts button
        if st.button("Apply Custom Allocation"):
            # Check if the custom allocation exceeds budget
            custom_gift_value = calculate_gift_value("Pack FOC", pack_foc) + calculate_gift_value("Hookah", hookah)
            
            if custom_gift_value > budget:
                st.error(f"Custom allocation exceeds budget! Value: ${custom_gift_value:.2f}, Budget: ${budget:.2f}")
            else:
                # Adjust gifts to comply with tier ROI limits if needed
                adjusted_gifts = adjust_gifts_for_tier_roi(order_data, eligible_tier, custom_gifts, budget)
                
                # Check if adjustments were made
                if adjusted_gifts != custom_gifts:
                    st.warning(f"Gift allocation adjusted to comply with {eligible_tier} tier ROI limits.")
                    st.session_state.custom_gifts = adjusted_gifts
                    # Update sliders on next rerun
                    st.session_state.custom_pack_foc = adjusted_gifts.get("Pack FOC", 0)
                    st.session_state.custom_hookah = adjusted_gifts.get("Hookah", 0)
                
                st.session_state.applied_custom_gifts = True
                
                # Display success message
                st.success("Custom gift allocation applied successfully!")
                
                # Rerun to update the UI
                st.rerun()
        
        # Display custom allocation if applied
        if st.session_state.get('applied_custom_gifts', False):
            st.subheader("Custom Gift Allocation")
            custom_gift_values = {
                "Pack FOC": st.session_state.custom_gifts.get("Pack FOC", 0) * 38,
                "Hookah": st.session_state.custom_gifts.get("Hookah", 0) * 400
            }
            
            display_gift_summary(
                st.session_state.custom_gifts, 
                budget,
                customer_type, 
                order_data,
                custom_gift_values
            )
            
            # Save to database button
            if st.button("Save Order to Database"):
                try:
                    # Get customer information
                    customer_name = st.session_state.customer_name
                    customer_address = st.session_state.customer_address
                    customer_type_str = "Tobacco Shop" if customer_type == CustomerType.TOBACCO_SHOP else "Retailer"
                    
                    # Get the currently applied gifts (either original or custom)
                    current_gifts = st.session_state.custom_gifts if st.session_state.get('applied_custom_gifts', False) else st.session_state.original_gifts
                    
                    # Calculate total weight directly from quantities
                    total_grams = sum([
                        order_data["quantities"].get("50g", 0) * 50,
                        order_data["quantities"].get("250g", 0) * 250,
                        order_data["quantities"].get("1kg", 0) * 1000
                    ])
                    
                    # Save to database
                    order_id = save_order(
                        customer_name=customer_name,
                        customer_address=customer_address,
                        customer_type=customer_type_str,
                        total_order_value=order_data['total_value'],
                        quantities=order_data['quantities'],
                        prices=order_data['prices'],
                        total_weight_g=total_grams,
                        eligible_tier=eligible_tier,
                        roi_percentage=target_roi,
                        budget=budget,
                        gifts=current_gifts
                    )
                    
                    # Show success message
                    st.success(f"Order saved successfully with ID: {order_id}")
                    
                    # Reset calculation
                    reset_all_calculations()
                    
                    # Rerun to update UI
                    st.rerun()
                    
                except ValueError as e:
                    # Special handling for database table errors
                    st.error(str(e))
                    st.info("To use database functionality, you need to create the required tables in Supabase. Check the console for SQL statements.")
                except Exception as e:
                    st.error(f"Error saving order: {str(e)}")

if __name__ == "__main__":
    main()
