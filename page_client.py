import streamlit as st
from supabase_connection import supabase_client
from utils import get_next_client_id
from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")

def show_page_client():
    st.title("Add Client")
    
    # Form to add new client
    with st.form("add_client_form"):
        client_name = st.text_input("Client Name")
        contact = st.text_input("Contact")
        email = st.text_input("e-mail")
        
        submitted = st.form_submit_button("Add Client")
        
        if submitted:
            id= int(get_next_client_id())
            client_response = supabase_client.from_("clients").insert({
                "Name": client_name,
                "Phone": contact,
                "email": email,
                "client_id": id
            }).execute()
            
            if client_response.data:
                st.success("Client added successfully!")
            else:
                st.error("Failed to add client.")