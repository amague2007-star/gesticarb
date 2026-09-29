import streamlit as st

def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 Connexion - GestiCarb ONG")
    st.write("Veuillez vous identifier pour accéder au logiciel.")

    with st.form("login"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")

        if submit:
            if (username == st.secrets["auth"]["username"]
                    and password == st.secrets["auth"]["password"]):
                st.session_state["authenticated"] = True
                st.session_state["user"] = username
                st.rerun()
            else:
                st.error("Identifiants incorrects")
    return False

def logout():
    st.session_state["authenticated"] = False
    st.rerun()