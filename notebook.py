import streamlit as st

def notebook_management():
    st.title(f"PaperSage: Notebook Management (User: {st.session_state.get('name', 'N/A')})")


    st.subheader("Create a New Notebook")
    new_notebook_name = st.text_input("Enter Notebook Name", key="new_nb_name_local")
    if st.button("Create Notebook"):
        if new_notebook_name:
            if new_notebook_name in st.session_state.notebooks:
                st.warning(f"Notebook '{new_notebook_name}' already exists.")
            else:
                
                st.session_state.notebooks[new_notebook_name] = {
                    "pdfs": [],       
                    "notes": [],        
                    "processed": False, 
                    "faiss_path": None  
                }
                st.success(f"Notebook '{new_notebook_name}' created!")
               
                
                st.rerun() 
        else:
            st.error("Please enter a notebook name.")

  
    st.subheader("Existing Notebooks")
    if not st.session_state.notebooks:
        st.info("No notebooks available. Create one above.")
    else:
        
        notebook_names = list(st.session_state.notebooks.keys())

        for nb_name in notebook_names:
            col1, col2 = st.columns([3, 1])
            with col1:
                
                if st.button(nb_name, key=f"select_{nb_name}"):
                    st.session_state.current_notebook = nb_name 
                    st.session_state.page = "main"
                    
                    st.session_state.chat_history = []
                    st.session_state.processing_done = st.session_state.notebooks[nb_name].get("processed", False)
                    st.session_state.faiss_index_path = st.session_state.notebooks[nb_name].get("faiss_path", None)
                    st.rerun()
            with col2:
    
                if st.button("Delete", key=f"delete_{nb_name}"):
                    
                    if nb_name in st.session_state.notebooks:
                        del st.session_state.notebooks[nb_name]
                        
                        if st.session_state.current_notebook == nb_name:
                            st.session_state.current_notebook = None
                            st.session_state.processing_done = False
                            st.session_state.faiss_index_path = None
                        st.success(f"Notebook '{nb_name}' deleted!")
                        st.rerun() 

    
    st.write("---")

    if st.button("Logout", key="logout_notebook_page_local"):
        st.session_state.page = "login"
        st.session_state.authentication_status = None
        st.session_state.user = None
        st.session_state.name = None

        st.session_state.current_notebook = None
        st.session_state.chat_history = []
        st.session_state.processing_done = False
        st.session_state.faiss_index_path = None
        
        st.warning("Logged out. Please note notebooks might persist in this browser session until cleared.")
        st.rerun()