import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController
from supabase_connection import fetch_table_data
import page_dashboard
import page_inbound
import page_outbound
import page_add_sku
from io import BytesIO
import os

users = fetch_table_data('users')

# Page configuration
st.set_page_config(page_title="DGM - Warehouse Management System", 
                   page_icon="📊", 
                   layout="wide")

# Style
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize the cookie controller
controller = CookieController()



def login(username, password):
    user = users[(users['name'] == username) & (users['pass'] == password)]
    if not user.empty:
        st.session_state.username = username
        return True
    return False

# Function to convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

# Function to update the status of an outbound record
def update_outbound_status(outbound_id, status):
    # Assuming you have a function to update the status in your database
    page_outbound.update_status(outbound_id, status)

# Check if user is logged in via cookies
logged_in_cookie = controller.get("logged_in")
username_cookie = controller.get("username")

if not logged_in_cookie:
    # Login form
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            # Set cookies to manage login state
            controller.set("logged_in", True)
            controller.set("username", username)
            st.rerun()
        else:
            st.error("Invalid username or password")
else:
    # User is logged in, show the main app
    username = username_cookie
    st.session_state.username = username
    st.sidebar.title(f"Welcome, {username}!")
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Record Inbound", "Record Outbound", "Add SKU"])
    
    # Logout button
    if st.sidebar.button("Logout", key="logout1"):
        controller.remove("logged_in")
        controller.remove("username")
        st.rerun()

    # Load the selected page
    if page == "Dashboard":
        current_stock, inbound_table, outbound_table = page_dashboard.show_page_dashboard()
    elif page == "Record Inbound":
        page_inbound.show_page_inbound()
    elif page == "Record Outbound":
        page_outbound.show_page_outbound()
    elif page == "Add SKU":
        page_add_sku.show_page_add_sku()

    # Download button
    if page == "Dashboard" and current_stock is not None and inbound_table is not None and outbound_table is not None:
        def to_excel_multiple_sheets(current_stock, inbound_table, outbound_table):
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            current_stock.to_excel(writer, index=False, sheet_name='Current Stock')
            inbound_table.to_excel(writer, index=False, sheet_name='Inbound Records')
            outbound_table.to_excel(writer, index=False, sheet_name='Outbound Records')
            writer.close()
            processed_data = output.getvalue()
            return processed_data

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.sidebar.download_button(
            label=f"Download as Excel",
            data=to_excel_multiple_sheets(current_stock, inbound_table, outbound_table),
            file_name=f'DGM_Warehouse_Report_{current_time}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

