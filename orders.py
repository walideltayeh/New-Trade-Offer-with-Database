import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_all_orders, orders_to_dataframe

def main():
    st.title("Order History")
    
    # Load orders from database
    try:
        df = orders_to_dataframe()
        
        if df.empty:
            st.info("No orders found in the database. Create orders using the Trade Offer Calculator.")
            return
            
        # Display total metrics
        total_orders = len(df)
        total_value = df["Order Value"].sum()
        total_gift_value = df["Total Gift Value"].sum()
        avg_roi = df["ROI %"].mean()
        
        # Create 4 metrics in a row
        metrics_cols = st.columns(4)
        with metrics_cols[0]:
            st.metric("Total Orders", f"{total_orders}")
        with metrics_cols[1]:
            st.metric("Total Order Value", f"${total_value:,.2f}")
        with metrics_cols[2]:
            st.metric("Total Gift Value", f"${total_gift_value:,.2f}")
        with metrics_cols[3]:
            st.metric("Average ROI", f"{avg_roi:.2f}%")
            
        # Filters
        st.subheader("Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            min_date = df["Date"].min().date()
            max_date = df["Date"].max().date()
            
            date_range = st.date_input(
                "Date Range",
                value=(max(min_date, max_date - timedelta(days=30)), max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)
                df_filtered = df.loc[mask]
            else:
                df_filtered = df
        
        with col2:
            # Customer type filter
            customer_types = ["All"] + sorted(df["Customer Type"].unique().tolist())
            selected_customer_type = st.selectbox("Customer Type", options=customer_types)
            
            if selected_customer_type != "All":
                df_filtered = df_filtered[df_filtered["Customer Type"] == selected_customer_type]
        
        with col3:
            # Tier filter
            tiers = ["All"] + sorted(df["Tier"].unique().tolist())
            selected_tier = st.selectbox("Tier", options=tiers)
            
            if selected_tier != "All":
                df_filtered = df_filtered[df_filtered["Tier"] == selected_tier]
        
        # Data visualizations
        st.subheader("Order Analysis")
        
        tab1, tab2, tab3 = st.tabs(["Orders by Tier", "Orders by Customer Type", "Orders Over Time"])
        
        with tab1:
            # Create a pie chart for tiers
            tier_counts = df_filtered["Tier"].value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            
            fig1 = px.pie(
                tier_counts, 
                names="Tier", 
                values="Count",
                title="Orders by Tier",
                color="Tier",
                color_discrete_map={
                    "Silver": "#C0C0C0",
                    "Gold": "#FFD700",
                    "Diamond": "#B9F2FF",
                    "Platinum": "#E5E4E2"
                }
            )
            st.plotly_chart(fig1, use_container_width=True)
            
        with tab2:
            # Create a pie chart for customer types
            customer_counts = df_filtered["Customer Type"].value_counts().reset_index()
            customer_counts.columns = ["Customer Type", "Count"]
            
            fig2 = px.pie(
                customer_counts, 
                names="Customer Type", 
                values="Count",
                title="Orders by Customer Type"
            )
            st.plotly_chart(fig2, use_container_width=True)
            
        with tab3:
            # Create a line chart for orders over time
            df_filtered["Date"] = pd.to_datetime(df_filtered["Date"]).dt.date
            orders_by_date = df_filtered.groupby("Date").agg({
                "Order Value": "sum",
                "Total Gift Value": "sum",
                "Order ID": "count"
            }).reset_index()
            orders_by_date.rename(columns={"Order ID": "Number of Orders"}, inplace=True)
            
            fig3 = px.line(
                orders_by_date,
                x="Date",
                y="Order Value",
                title="Order Value Over Time"
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            fig4 = px.line(
                orders_by_date,
                x="Date",
                y="Number of Orders",
                title="Number of Orders Over Time"
            )
            st.plotly_chart(fig4, use_container_width=True)
        
        # Order table
        st.subheader("Order List")
        
        # Select columns to display
        display_columns = [
            "Order ID", "Date", "Customer Name", "Customer Type", 
            "Order Value", "Total Weight (kg)", "Tier", "ROI %",
            "Pack FOC", "Hookah", "Total Gift Value"
        ]
        
        # Format the dataframe
        formatted_df = df_filtered[display_columns].copy()
        formatted_df["Date"] = formatted_df["Date"].dt.strftime("%Y-%m-%d %H:%M")
        formatted_df["Order Value"] = formatted_df["Order Value"].map("${:,.2f}".format)
        formatted_df["Total Gift Value"] = formatted_df["Total Gift Value"].map("${:,.2f}".format)
        formatted_df["ROI %"] = formatted_df["ROI %"].map("{:.2f}%".format)
        
        # Display the dataframe
        st.dataframe(formatted_df, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading orders: {str(e)}")

# Function to create a developer footer for the app
def add_developer_footer():
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 10px;'>"
        "Developed by Walid El Tayeh"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
    # Add developer footer
    add_developer_footer()