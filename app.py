import streamlit as st
import auth
import notebook
import main_page
import os
from dotenv import load_dotenv
import db_utils

db_utils.init_db()


load_dotenv()


required_keys = [
    'page',
    'authentication_status',
    'user',
    'name',
    'notebooks',
    'current_notebook',
    'chat_history',
    'faiss_index_path',
    'processing_done'
]

default_values = {
    'page': "login",
    'authentication_status': None,
    'user': None,
    'name': None,
    'notebooks': {},
    'current_notebook': None,
    'chat_history': [],
    'faiss_index_path': None,
    'processing_done': False
}

for key in required_keys:
    if key not in st.session_state:
        st.session_state[key] = default_values[key]


if st.session_state.page == "login":
    auth.login_page()

elif st.session_state.page == "notebook":
    notebook.notebook_management()

elif st.session_state.page == "main":
   
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("🔴 Google API Key not found! Please set it in your .env file.")
        st.stop()
    else:
        main_page.main_notebook_page()
