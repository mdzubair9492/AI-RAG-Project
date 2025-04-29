import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
import hashlib


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


gemini_default = "gemini-1.5-pro-001"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", gemini_default)


def get_pdf_text_with_metadata(pdf_docs):
    docs = []
    for pdf in pdf_docs:
        try:
            reader = PdfReader(pdf)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    docs.append(Document(
                        page_content=text,
                        metadata={"source": pdf.name, "page": i+1}
                    ))
        except Exception as e:
            st.error(f"Error reading '{pdf.name}': {e}")
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
        
        st.session_state.faiss_index_path = index_name
        st.session_state.processing_done = True
        nb = st.session_state.current_notebook
        st.session_state.notebooks[nb]['processed'] = True
        st.session_state.notebooks[nb]['faiss_path'] = index_name
        return True
    except Exception as e:
        if "API key not valid" in str(e) or not os.getenv("GOOGLE_API_KEY"):
            st.error("🔴 Google API Key is invalid or missing.")
        else:
            st.error(f"Error creating vector store: {e}")
        st.session_state.processing_done = False
        return False

def get_conversational_chain():
    template = """
Answer the question as detailed as possible from the provided context.
Include relevant details and cite the source document and page number(s).
Cite like [Source: file.pdf, Page: X].
If not found, reply "The answer is not available in the provided documents.".

Context:
{context}

Question:
{question}

Answer:
"""
    try:
        model = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.3)
        prompt = PromptTemplate(template=template, input_variables=["context","question"])
        return load_qa_chain(model, chain_type="stuff", prompt=prompt)
    except Exception as e:
        st.error(f"Error initializing chat model: {e}")
        return None


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
    if not chain:
        return
    context = "\n".join(d.page_content for d in docs)
    result = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    answer = result.get("output_text", "")
   
    cites = {f"[Source: {d.metadata['source']}, Page: {d.metadata['page']}]" for d in docs}
    cite_str = " ".join(sorted(cites))
    st.session_state.chat_history += [
        ("User", user_question),
        ("PaperSage", answer),
        ("Sources", cite_str)
    ]


def main_notebook_page():
    nb = st.session_state.get("current_notebook")
    if not nb:
        st.error("No notebook selected.")
        if st.button("Back"):
            st.session_state.page = "notebook"; st.rerun()
        return

    st.title(f"PaperSage: {nb}")
 
    safe = hashlib.md5(nb.encode()).hexdigest()
    raw_path = st.session_state.notebooks[nb].get("faiss_path")
    idx_path = raw_path if raw_path else f"faiss_index_{safe}"
  
    if st.session_state.get("current_notebook_init") != nb:
        st.session_state.chat_history = []
        st.session_state.processing_done = st.session_state.notebooks[nb].get("processed", False)
        st.session_state.faiss_index_path = idx_path
        st.session_state.current_notebook_init = nb

    
    st.sidebar.header(f"Notebook: {nb}")
    files = st.sidebar.file_uploader("Upload PDF(s)", accept_multiple_files=True, key=f"pdf_upload_{nb}")
    if st.sidebar.button("Process PDFs", key=f"process_{nb}"):
        if files:
            with st.sidebar:
                with st.spinner("Processing PDFs..."):
                    raw = get_pdf_text_with_metadata(files)
                    ch = get_text_chunks(raw)
                    get_vector_store(ch, idx_path)
        else:
            st.sidebar.warning("Upload PDFs first.")
    st.sidebar.markdown("---")
    if st.sidebar.button("Back to Notebooks"):
        st.session_state.page="notebook"; st.session_state.current_notebook=None; st.rerun()

    
    st.header("Chat with your Docs")
    if st.session_state.processing_done:
        st.success("✅ Ready to ask questions.")
    else:
        st.info("ℹ️ Please upload & process PDFs first.")
    for role, msg in st.session_state.chat_history:
        if role == "User":
            st.markdown(
                f"<div style='text-align:right; background-color:#000; color:#fff; padding:8px; border-radius:8px;'>**You:** {msg}</div>",
                unsafe_allow_html=True
            )
        elif role == "PaperSage":
            st.markdown(
                f"<div style='text-align:left; background-color:#000; color:#fff; padding:8px; border-radius:8px;'>**PaperSage:** {msg}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background-color:#000; color:#fff; font-size:0.8em; padding:5px; border-radius:5px;'>Sources: {msg}</div>",
                unsafe_allow_html=True
            )
    st.markdown("---")
    if st.session_state.processing_done:
        q = st.text_input("Ask a question:", key=f"query_input_{nb}")
        if st.button("Ask", key=f"ask_btn_{nb}"):
            if q:
                user_input(q, st.session_state.faiss_index_path)
            else:
                st.warning("Please type a question.")
    else:
        st.text_input("Ask a question:", disabled=True)

    
    st.markdown("---")
    st.subheader("Custom Notes")
    with st.form("custom_notes_form"):
        note = st.text_area("Write your own note")
        if st.form_submit_button("Save Note"):
            if note:
                st.session_state.notebooks[nb]['notes'].append(note)
                st.success("Note saved!")
            else:
                st.error("Cannot save empty note.")

    
    st.markdown("---")
    st.subheader("AI‑Generated Notes")
    if st.button("Generate AI Notes", key=f"ai_notes_{nb}"):
        uploaded = st.session_state.get(f"pdf_upload_{nb}", [])
        if uploaded:
            with st.spinner("Generating notes..."):
                try:
                    raw = get_pdf_text_with_metadata(uploaded)
                    ch = get_text_chunks(raw)
                    summ = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.3)
                    chain = load_summarize_chain(summ, chain_type="map_reduce")
                    summary = chain.run(ch)
                    st.session_state.notebooks[nb]['notes'].append(summary)
                    st.success("AI note saved!")
                    st.write(summary)
                except ResourceExhausted as e:
                    st.error("🔴 API quota exceeded. Please wait or upgrade your Google AI plan.")
                except Exception as e:
                    st.error(f"Error generating AI notes: {e}")
        else:
            st.warning("Please upload & process PDFs first.")

   
    st.markdown("---")
    st.subheader("All Notes")
    notes = st.session_state.notebooks[nb].get('notes', [])
    if notes:
        for n in notes:
            st.markdown(f"- {n}")
    else:
        st.info("No notes yet.")


