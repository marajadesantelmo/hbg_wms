from supabase_connection import supabase_client, fetch_table_data

import streamlit as st
import pandas as pd
from utils import current_stock_table, generate_inbound_table
from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")

def show_page_inbound():
    clients = fetch_table_data('clients')
    stock = fetch_table_data('stock')
    skus = fetch_table_data('skus')
    inbound = fetch_table_data('inbound')
    inbound_table = generate_inbound_table(inbound, skus)
    st.title("Record Inbound")
    col1, col3 = st.columns([2, 1])
    
    with col1:
        with st.form("add_stock_form"):
            container = st.text_input("Container")
            #client_name = st.selectbox("Client Name", clients['Name'])

            col1_inner, col2_inner = st.columns(2)

            with col1_inner:
                # Selectbox for up to 10 SKUs, default value set to None or "" to prevent accidental selection
                skus_selected = [
                    st.selectbox(f"{i+1}. SKU", [""] + sorted(skus['SKU'].tolist()), key=f"sku_{i}")
                    for i in range(10)
                ]

            with col2_inner:
                # Number inputs for quantities of up to 10 items
                quantities = [
                    st.number_input(f"Quantity item {i+1}", min_value=0, key=f"qty_{i}")
                    for i in range(10)
                ]

            submitted = st.form_submit_button("Record Inbound")

            if submitted:
                # Filter out items where SKU is empty or quantity is 0
                inbound_data = []
                for i in range(10):
                    # Check that the SKU is selected (not empty) and quantity is greater than 0
                    if skus_selected[i] and skus_selected[i] != "" and quantities[i] > 0:
                        sku_id = int(skus.loc[skus['SKU'] == skus_selected[i], 'sku_id'].values[0])
                        quantity = quantities[i]

                        # Get client_id
                        #client_id = int(clients.loc[clients['Name'] == client_name, 'client_id'].values[0])
                        client_id = 5
                        # Check if stock already exists for the given SKU and client
                        if not stock.empty:
                            existing_stock = stock.loc[(stock['sku_id'] == sku_id) & (stock['client_id'] == client_id)]
                        if stock.empty:
                            existing_stock = stock
                            
                        if not existing_stock.empty:
                            # Update existing stock quantity
                            existing_quantity = int(existing_stock['Quantity'].values[0])
                            new_quantity = existing_quantity + quantity
                            supabase_client.from_("stock").update({"Quantity": new_quantity}).match({
                                "sku_id": sku_id, "client_id": client_id
                            }).execute()
                        else:
                            # Insert new stock record
                            supabase_client.from_("stock").insert([{
                                "sku_id": sku_id, "client_id": client_id, "Quantity": quantity
                            }]).execute()

                        # Add inbound record
                        inbound_data.append({
                            "Container": container, "sku_id": sku_id, "client_id": client_id,
                            "Date": current_date, "Quantity": quantity
                        })

                # Insert inbound records in batch
                if inbound_data:
                    supabase_client.from_("inbound").insert(inbound_data).execute()
                    st.success("Inbound records added successfully!")
                    # Reload the inbound table
                    inbound = fetch_table_data('inbound')
                    inbound_table = generate_inbound_table(inbound, skus)
                else:
                    st.warning("No valid items were selected.")

    username = st.session_state.get("username", "")

    with col3:
        st.subheader("Inbound to Stock")
        st.dataframe(inbound_table, hide_index=True)
        username = st.session_state.get("username", "")
        if username in ["Diego", "Santiago"]:
            st.subheader("Delete Inbound Record")
            containers_to_delete_id = [""] + inbound_table['Container'].unique().tolist()
            container_to_delete = st.selectbox("Select Container to Delete", containers_to_delete_id)
            delete_button = st.button("Delete Inbound Record")
            if delete_button:
                # Delete inbound record
                delete_response = supabase_client.from_("inbound").delete().eq("Container", container_to_delete).execute()
                st.success(f"Deleted inbound record for container {container_to_delete}")
                # Delete items from stock
                if delete_response.data:
                    for record in delete_response.data:
                        sku_id = record['sku_id']
                        client_id = record['client_id']
                        quantity = record['Quantity']
                        existing_stock = stock.loc[(stock['sku_id'] == sku_id) & (stock['client_id'] == client_id)]
                        existing_quantity = int(existing_stock['Quantity'].values[0])
                        new_quantity = existing_quantity - quantity
                        supabase_client.from_("stock").update({"Quantity": new_quantity}).match({
                            "sku_id": sku_id, "client_id": client_id
                        }).execute()
                    st.success(f"All items deleted from stock for container {container_to_delete}")

                # Reload the inbound table
                inbound = fetch_table_data('inbound')
                inbound_table = generate_inbound_table(inbound, skus)
                # Reload the stock table
                stock = fetch_table_data('stock')








