from supabase_connection import fetch_table_data, supabase_client

import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_next_outbound_id, generate_outbound_table, current_stock_table, generate_invoice, generate_invoice_outbound_order

current_date = datetime.now().strftime("%Y-%m-%d")

def show_page_outbound():
    st.title("Record Outbound Order")
    # Fetch and prepare data
    #clients = fetch_table_data('clients')
    stock = fetch_table_data('stock')
    skus = fetch_table_data('skus')
    #stock = stock.merge(clients[['client_id', 'Name']], on='client_id')
    outbount = fetch_table_data('outbound')
    outbound_table = generate_outbound_table(outbount, skus)
    current_stock = current_stock_table(stock, skus)

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.form("record_outbound_form"):
            #client_name = st.selectbox("Client Name", clients['Name'])
            invoice = st.text_input("Invoice Number (please enter only numbers)")
            col1_1, col1_2 = st.columns(2)
            # Grouping SKUs by invoice number
            with col1_1:
                # Selectbox for up to 10 SKUs, default value set to None or "" to prevent accidental selection
                skus_selected = [
                    st.selectbox(f"{i+1}. SKU", [""] + skus['SKU'].tolist(), key=f"sku_{i}")
                    for i in range(10)
                ]

            with col1_2:
                # Number inputs for lengths of up to 10 items
                lengths = [
                    st.number_input(f"Length item {i+1}", min_value=0, key=f"length_{i}")
                    for i in range(10)
                ]

            submitted = st.form_submit_button("Record Outbound")

            if submitted:
                if not invoice.isnumeric():
                    st.error("Invoice Number must be numeric.")
                else:
                    # Filter out items where SKU is empty or quantity is 0
                    outbound_data = []
                    invoice_data = []
                    for i in range(10):
                        if skus_selected[i] and lengths[i] > 0:
                            sku_id = int(skus.loc[skus['SKU'] == skus_selected[i], 'sku_id'].values[0])
                            length = lengths[i]

                            # FIJO CLIENT ID
                            #client_id = int(clients.loc[clients['Name'] == client_name, 'client_id'].values[0])
                            client_id = 5
                            
                            existing_stock = stock.loc[(stock['sku_id'] == sku_id) & (stock['client_id'] == client_id)]
                            unit_length = skus.loc[skus['sku_id'] == sku_id, 'Length'].values[0]
                            quantity = int(length / unit_length)

                            if existing_stock.empty:
                                #st.error(f"No stock available for SKU {skus_selected[i]} and Client {client_name}.")
                                st.error(f"No stock available for SKU {skus_selected[i]}")
                            else:
                                current_quantity = int(existing_stock['Quantity'].values[0])

                                # Check for sufficient stock
                                if quantity > current_quantity:
                                    st.error(f"The quantity to subtract exceeds the current stock for SKU {skus_selected[i]}.")
                                else:
                                    # Calculate the new stock quantity
                                    new_quantity = current_quantity - quantity
                                    update_response = supabase_client.from_("stock").update({
                                        "Quantity": new_quantity
                                    }).match({
                                        "sku_id": sku_id,
                                        "client_id": client_id
                                    }).execute()
                                    
                                    if update_response.data:
                                        # Store data for outbound record
                                        status = "Pending"
                                        outbound_data.append({
                                            'sku_id': sku_id,
                                            'client_id': client_id,
                                            'Date': current_date,
                                            'Quantity': quantity,
                                            'Invoice Number': invoice,
                                            'Status': status
                                        })
                                        # Store data for invoice
                                        invoice_data.append({
                                            'sku_id': sku_id,
                                            'SKU': skus_selected[i],
                                            'Date': current_date,
                                            'Quantity': quantity,
                                            'total_length': length,
                                            'Invoice Number': invoice
                                        })

                                    else:
                                        st.error("Failed to update stock.")
                    
                    # Insert outbound records in batch if there are valid items
                    if outbound_data:
                        for record in outbound_data:
                            outbound_response = supabase_client.from_("outbound").insert([record]).execute()
                            if outbound_response.data:
                                st.success(f"Outbound record for Invoice {invoice} created successfully!")
                            else:
                                st.error(f"Failed to create outbound record for SKU {record['sku_id']}.")
                        #Generate invoice for outbound order
                        pdf = generate_invoice_outbound_order(invoice, invoice_data)
                        pdf_output = pdf.output(dest='S').encode('latin1')
                        st.session_state.pdf_output = pdf_output
                        st.session_state.invoice = invoice
                    else:
                        st.warning("No valid items selected or lengths exceed available stock.")
                    # Reload the current stock and outbound tables
                    stock = fetch_table_data('stock')
                    current_stock = current_stock_table(stock, skus)
                    outbound = fetch_table_data('outbound')
                    outbound_table = generate_outbound_table(outbound, skus)

        if 'pdf_output' in st.session_state and 'invoice' in st.session_state:
            st.download_button(
                label="Download Outbound Order",
                data=st.session_state.pdf_output,
                file_name=f"DGM_Outbound_Order_{st.session_state.invoice}.pdf",
                mime="application/pdf"
            )
    with col2: 
        st.subheader("Current Stock")
        st.dataframe(current_stock, hide_index=True, use_container_width=True)

        st.subheader("Validate Outbound Order")
        outbound_table_pending = outbound_table.loc[outbound_table['Status'] != 'Validated']
        invoice_numbers = [""] + outbound_table_pending['Invoice Number'].fillna(0).astype(int).unique().tolist()
        selected_invoice = st.selectbox("Select Invoice Number", invoice_numbers)
        if selected_invoice:
            outbound_id = selected_invoice
        if st.button("Validate Outbound"):
            if outbound_id:
                outbound_validation_response = supabase_client.from_("outbound").update({
                    "Status": "Validated"}).match({"Invoice Number": outbound_id}).execute()
            if outbound_validation_response.data:
                st.success(f"Outbound {outbound_id} has been validated.")
                # Reload the current stock and outbound tables
                stock = fetch_table_data('stock')
                current_stock = current_stock_table(stock, skus)
                outbount = fetch_table_data('outbound')
                outbound_table = generate_outbound_table(outbount, skus)
                invoice_data = [{
                    "sku_id": record["sku_id"],
                    "SKU": f"SKU-{record['sku_id']}",  # Example SKU mapping
                    "Quantity": record["Quantity"],
                    "total_length": record["Quantity"] * 5,  # Example calculation
                    "Invoice Number": record["Invoice Number"]
                } for record in outbound_validation_response.data]
                
                pdf = generate_invoice(outbound_id, invoice_data)
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.session_state.pdf_output = pdf_output
                st.session_state.invoice = invoice
                if 'pdf_output' in st.session_state and 'invoice' in st.session_state:
                    st.download_button(
                        label="Download Invoice",
                        data=st.session_state.pdf_output,
                        file_name=f"DGM_Outbound_Invoice_{st.session_state.invoice}.pdf",
                        mime="application/pdf")
            else:
                st.error(f"Failed to validate outbound {outbound_id}.")
        
        username = st.session_state.get("username", "")
        if username in ["Diego", "Santiago"]:
            st.subheader("Delete Outbound Record")
            invoices_to_delete_numbers = [""] + outbound_table['Invoice Number'].fillna(0).astype(int).unique().tolist()
            invoice_to_delete = st.selectbox("Select Invoice Number to delete", invoices_to_delete_numbers)
            if st.button("Delete Outbound"):
                if invoice_to_delete:
                    delete_response = supabase_client.from_("outbound").delete().match({"Invoice Number": invoice_to_delete}).execute()
                    if delete_response.data:
                        st.success(f"Outbound record for Invoice {invoice_to_delete} has been deleted.")
                        # Reload the outbound table
                        outbound = fetch_table_data('outbound')
                        outbound_table = generate_outbound_table(outbound, skus)
                        # Add corresponding units to stock when outbound is deleted
                        for record in delete_response.data:
                            sku_id = record['sku_id']
                            client_id = record['client_id']
                            quantity = record['Quantity']
                            existing_stock = stock.loc[(stock['sku_id'] == sku_id) & (stock['client_id'] == client_id)]
                            current_quantity = int(existing_stock['Quantity'].values[0])
                            new_quantity = current_quantity + quantity
                            supabase_client.from_("stock").update({"Quantity": new_quantity}).match({
                                "sku_id": sku_id, "client_id": client_id
                            }).execute()
                    else:
                        st.error(f"Failed to delete outbound record for Invoice {invoice_to_delete}.")
    st.subheader("Outbound from Stock")
    outbound_table = outbound_table.sort_values(by='Date', ascending=False)
    st.dataframe(outbound_table, hide_index=True, use_container_width=True)
