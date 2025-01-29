from supabase import create_client, Client
import pandas as pd
import os

#De aca agarra las keys streamlit. En caso de correr manual no correr estos comandos
url_supabase = os.getenv("url_supabase")
key_supabase= os.getenv("key_supabase")

supabase_client = create_client(url_supabase, key_supabase)

def fetch_table_data(table_name):
    query = (
        supabase_client
        .from_(table_name)
        .select('*')
        .execute()
    )
    return pd.DataFrame(query.data)

