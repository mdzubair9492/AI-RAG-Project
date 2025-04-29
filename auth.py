import streamlit as st
import streamlit_authenticator as stauth
import os
import yaml
from yaml.loader import SafeLoader

def load_credentials(file_path="credentials.yaml"):
    """
    Load the credentials YAML. If not found, create a default structure.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            config = yaml.load(file, Loader=SafeLoader)
    else:
        st.warning(f"{file_path} not found. Creating default structure.")
        config = {
            'credentials': {'usernames': {}},
            'cookie': {
                'expiry_days': 30,
                'key': 'some_signature_key',
                'name': 'some_cookie_name'
            }
        }
        save_credentials(config, file_path)
    
    
    config.setdefault('credentials', {'usernames': {}})
    config.setdefault('cookie', {
        'expiry_days': 30,
        'key': 'some_signature_key',
        'name': 'some_cookie_name'
    })
    return config

def save_credentials(config, file_path="credentials.yaml"):
    """
    Save the credentials YAML back to disk.
    """
    try:
        with open(file_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False)
        return True
    except Exception as e:
        st.error(f"Failed to save credentials: {e}")
        return False

def hash_password(password: str) -> str:
    """
    Hash a password using streamlit_authenticator's bcrypt wrapper.
    Falls back to SHA‑256 only if bcrypt isn't available.
    """
    try:
        
        return stauth.Hasher.hash(password)
    except Exception:
       
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash.
    Returns False if anything goes wrong.
    """
    try:
        return stauth.Hasher.check_pw(password, hashed_password)
    except Exception:
        st.error("Password verification failed. Please contact support.")
        return False

def login_page():
    """
    Show login and registration UI.
    """
    st.title("PaperSage: User Registration / Login")
    
   
    config = load_credentials()
    
    
    users_exist = bool(config['credentials']['usernames'])
    
   
    if 'registration_submitted' not in st.session_state:
        st.session_state.registration_submitted = False
    
   
    action = st.selectbox("Select Action", ["Login", "Register"])
   
    if action == "Register":
        st.header("User Registration")
        
        
        with st.form("registration_form"):
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            
            register_submitted = st.form_submit_button("Register")
            
            if register_submitted:
                st.session_state.registration_submitted = True
                st.session_state.form_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'username': username,
                    'password': password
                }
        
       
        if st.session_state.registration_submitted:
           
            st.session_state.registration_submitted = False
            
            
            data = st.session_state.form_data
            
          
            if not all([data['first_name'], data['last_name'], data['username'], data['password'], data['email']]):
                st.error("Please fill in all fields.")
            elif data['username'] in config['credentials']['usernames']:
                st.error("Username already exists!")
            else:
                
                hashed_password = hash_password(data['password'])
                
                
                config['credentials']['usernames'][data['username']] = {
                    'email': data['email'],
                    'name': f"{data['first_name']} {data['last_name']}",
                    'password': hashed_password
                }
                
                if save_credentials(config):
                    st.success(f"User '{data['username']}' registered successfully! Please log in.")
    else:  
        st.header("User Login")
        
        
        debug_mode = False
        
       
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Login")
        
        if login_submitted:
            if not username or not password:
                st.warning("Please enter your username and password")
            else:
                
                if username not in config['credentials']['usernames']:
                    st.error("Username not found")
                else:
                    
                    user_data = config['credentials']['usernames'][username]
                    hashed_password = user_data['password']
                    name = user_data['name']
                    email = user_data['email']
                    
                    
                    if debug_mode:
                        st.info(f"Stored hash: {hashed_password}")
                    
                    
                    if verify_password(password, hashed_password):
                        st.success(f"Welcome *{name}*")
                       
                        st.session_state.authentication_status = True
                        st.session_state.name = name
                        st.session_state.username = username
                        st.session_state.user = username
                        st.session_state.email = email
                        st.session_state.page = "notebook"
                        st.rerun()
                    else:
                        st.error("Password is incorrect")
    
  
    if not users_exist and 'no_users_shown' not in st.session_state:
        st.info("No users found. Please register a new user.")
        st.session_state.no_users_shown = True

def logout():
    """
    Log the user out.
    """
    keys_to_clear = [
        'authentication_status', 'user', 'name', 'username', 
        'email', 'no_users_shown', 'registration_submitted'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state.page = "login"

def is_authenticated():
    """
    Check if the user is authenticated.
    """
    return st.session_state.get('authentication_status', False)

def initialize_session_state():
    """
    Initialize session state variables if they don't exist.
    """
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'name' not in st.session_state:
        st.session_state.name = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'page' not in st.session_state:
        st.session_state.page = "login"














