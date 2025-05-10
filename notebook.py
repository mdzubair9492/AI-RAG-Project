import streamlit as st
import db_utils


def notebook_management():
    
    st.title(f"PaperSage: Notebook Management (User: {st.session_state.get('name', 'N/A')})")

    
    st.subheader("Create a New Notebook")
    new_notebook_name = st.text_input("Enter Notebook Name", key="new_nb_name_local")
    if st.button("Create Notebook"):
        if new_notebook_name:
            user = st.session_state.user
            # Check for existing notebooks in database
            existing = [nb['name'] for nb in db_utils.get_notebooks(user)]
            if new_notebook_name in existing:
                st.warning(f"Notebook '{new_notebook_name}' already exists.")
            else:
                db_utils.create_notebook(user, new_notebook_name)
                st.success(f"Notebook '{new_notebook_name}' created!")
                st.rerun()
        else:
            st.error("Please enter a notebook name.")


    st.subheader("Existing Notebooks")
    user = st.session_state.user
    notebooks = db_utils.get_notebooks(user)
    if not notebooks:
        st.info("No notebooks available. Create one above.")
    else:
        for nb in notebooks:
            nb_id = nb['id']
            nb_name = nb['name']
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(nb_name, key=f"select_{nb_name}"):
                    
                    st.session_state.current_notebook = nb_name
                    st.session_state.current_notebook_id = nb_id
                    st.session_state.page = "main"
                    st.session_state.chat_history = []
                    st.session_state.processing_done = bool(nb['processed'])
                    st.session_state.faiss_index_path = nb['faiss_path']
                    st.rerun()
            with col2:
                if st.button("Delete", key=f"delete_{nb_name}"):
                    
                    db_utils.delete_notebook(user, nb_name)
                    st.success(f"Notebook '{nb_name}' deleted!")
                    
                    if st.session_state.current_notebook == nb_name:
                        st.session_state.current_notebook = None
                        st.session_state.current_notebook_id = None
                        st.session_state.processing_done = False
                        st.session_state.faiss_index_path = None
                    st.rerun()

    
    st.write("---")


    if st.button("Logout", key="logout_notebook_page_local"):
        
        for key in ['authentication_status', 'user', 'name', 'current_notebook', 'current_notebook_id', 'chat_history', 'processing_done', 'faiss_index_path']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.page = "login"
        st.warning("Logged out. Notebooks remain in database until explicitly deleted.")
        st.rerun()

