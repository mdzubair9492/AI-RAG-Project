# main_page.py

import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os, hashlib
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document

import db_utils

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def get_pdf_text_with_metadata(pdf_docs):
    docs = []
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            docs.append(Document(
                page_content=text,
                metadata={"source": pdf.name, "page": i+1}
            ))
    return docs


def get_text_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return splitter.split_documents(documents)


def get_vector_store(chunks, index_name):
    if not chunks:
        st.warning("No text chunks to process.")
        return False
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        store = FAISS.from_documents(chunks, embedding=embeddings)
        store.save_local(index_name)

        # Persist processing status to DB
        nb_id = st.session_state.current_notebook_id
        db_utils.update_notebook_processing(nb_id, True, index_name)

        st.session_state.faiss_index_path = index_name
        st.session_state.processing_done = True
        return True

    except Exception as e:
        st.error(f"Error creating vector store: {e}")
        st.session_state.processing_done = False
        return False


def get_conversational_chain():
    template = """
Answer the question as detailed as possible from the provided context.
Include relevant details and cite the source document and page number(s).
Context:
{context}

Question:
{question}

Answer:
"""
    model = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.3)
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)


def user_input(user_question, index_path):
    if not index_path or not os.path.exists(index_path):
        st.error("🔴 No FAISS index found. Process PDFs first.")
        return
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    docs = db.similarity_search(user_question, k=5)
    if not docs:
        st.warning("No relevant info found.")
        st.session_state.chat_history += [("User", user_question), ("PaperSage", "No info found.")]
        return

    chain = get_conversational_chain()
    result = chain({"input_documents": docs, "question": user_question})
    answer = result.get("output_text", "")

    # Build citations
    cites = {
        f"[Source: {d.metadata['source']}, Page: {d.metadata['page']}]"
        for d in docs
    }
    cite_str = " ".join(sorted(cites))

    st.session_state.chat_history += [
        ("User", user_question),
        ("PaperSage", answer),
        ("Sources", cite_str)
    ]


def main_notebook_page():
    nb = st.session_state.current_notebook
    if not nb:
        st.error("No notebook selected.")
        if st.button("Back"):
            st.session_state.page = "notebook"
            st.rerun()
        return

    st.title(f"PaperSage: {nb}")
    user = st.session_state.user

    # Fetch notebook record from DB
    recs = db_utils.get_notebooks(user)
    rec = next((r for r in recs if r["id"] == st.session_state.current_notebook_id), None)
    idx_path = rec["faiss_path"] if rec and rec["faiss_path"] else f"faiss_index_{hashlib.md5(nb.encode()).hexdigest()}"

    # Initialize session state for this notebook on first load
    if st.session_state.get("current_notebook_init") != nb:
        st.session_state.chat_history = []
        st.session_state.processing_done = bool(rec["processed"]) if rec else False
        st.session_state.faiss_index_path = idx_path
        st.session_state.current_notebook_init = nb

    # Sidebar: file upload & process
    st.sidebar.header(f"Notebook: {nb}")
    files = st.sidebar.file_uploader("Upload PDF(s)", accept_multiple_files=True, key=f"upload_{nb}")
    if st.sidebar.button("Process PDFs", key=f"process_{nb}"):
        if files:
            with st.spinner("Processing PDFs..."):
                raw = get_pdf_text_with_metadata(files)
                chunks = get_text_chunks(raw)
                get_vector_store(chunks, idx_path)
        else:
            st.sidebar.warning("Please upload PDFs first.")
    st.sidebar.markdown("---")
    if st.sidebar.button("Back to Notebooks", key=f"back_{nb}"):
        st.session_state.page = "notebook"
        st.session_state.current_notebook = None
        st.rerun()

    # Chat area
    st.header("Chat with your Docs")
    if st.session_state.processing_done:
        st.success("✅ Ready to ask questions.")
    else:
        st.info("ℹ️ Please upload & process PDFs first.")

    for role, msg in st.session_state.chat_history:
        align = "right" if role == "User" else "left"
        label = "You" if role == "User" else "PaperSage" if role == "PaperSage" else ""
        style = (
            f"background-color:#000;color:#fff;padding:8px;"
            f"border-radius:8px;text-align:{align}"
        )
        st.markdown(f"<div style='{style}'><b>{label}:</b> {msg}</div>", unsafe_allow_html=True)

    # Single Ask button with unique key
    if st.session_state.processing_done:
        q = st.text_input("Ask a question:", key=f"query_{nb}")
        if st.button("Ask", key=f"ask_{nb}"):
            if q:
                user_input(q, st.session_state.faiss_index_path)
            else:
                st.warning("Please type a question.")
    else:
        st.text_input("Ask a question:", disabled=True)

    st.markdown("---")

    # --------------------------------
    # AI‑Generated Notes
    # --------------------------------
    if st.button("Generate AI Notes", key=f"ai_notes_{nb}"):
        uploaded = st.session_state.get(f"upload_{nb}", [])
        if uploaded:
            with st.spinner("Generating AI notes..."):
                try:
                    raw = get_pdf_text_with_metadata(uploaded)
                    ch = get_text_chunks(raw)
                    summ_model = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.3)
                    chain = load_summarize_chain(summ_model, chain_type="map_reduce")
                    summary = chain.run(ch)
                    db_utils.add_note_to_db(st.session_state.current_notebook_id, summary)
                    st.success("AI note saved!")
                    st.markdown(summary)
                except ResourceExhausted:
                    st.error("🔴 API quota exceeded. Please wait or upgrade your plan.")
                except Exception as e:
                    st.error(f"Error generating AI notes: {e}")
        else:
            st.warning("Please upload & process PDFs first.")

    st.markdown("---")

    # Custom Notes
    with st.form(f"notes_form_{nb}"):
        note = st.text_area("Write your own note")
        if st.form_submit_button("Save Note"):
            if note:
                db_utils.add_note_to_db(st.session_state.current_notebook_id, note)
                st.success("Note saved!")
            else:
                st.error("Cannot save empty note.")

    st.markdown("---")
    st.subheader("All Notes")
    notes = db_utils.get_notes_from_db(st.session_state.current_notebook_id)
    if notes:
        for n in notes:
            st.markdown(f"- {n}")
    else:
        st.info("No notes yet.")





