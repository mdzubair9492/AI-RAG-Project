import os
import tempfile
import sqlite3
import pytest


import db_utils
import auth



@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch, tmp_path):
    """
    Monkeypatch the DB_PATH to use a temporary file for isolation.
    """
    temp_db = tmp_path / "test_papersage.db"
    monkeypatch.setattr(db_utils, 'DB_PATH', str(temp_db))
  
    db_utils.init_db()
    return temp_db



def test_init_db_creates_tables(use_temp_db):
    
    conn = sqlite3.connect(use_temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert 'notebooks' in tables
    assert 'notes' in tables
    conn.close()


def test_create_and_get_and_delete_notebook(use_temp_db):
    user = 'alice'
    name = 'TestNotebook'

    
    assert db_utils.get_notebooks(user) == []

  
    db_utils.create_notebook(user, name)
    nbs = db_utils.get_notebooks(user)
    assert len(nbs) == 1
    assert nbs[0]['name'] == name
    assert nbs[0]['processed'] == 0

  
    db_utils.delete_notebook(user, name)
    assert db_utils.get_notebooks(user) == []


def test_update_notebook_processing(use_temp_db):
    user = 'bob'
    name = 'ProcNB'
    db_utils.create_notebook(user, name)
    nb = db_utils.get_notebooks(user)[0]
    assert nb['processed'] == 0

   
    db_utils.update_notebook_processing(nb['id'], True, 'path/to/index')
    updated = db_utils.get_notebooks(user)[0]
    assert updated['processed'] == 1
    assert updated['faiss_path'] == 'path/to/index'


def test_add_and_get_notes(use_temp_db):
    user = 'carol'
    nb_name = 'NotesNB'
    db_utils.create_notebook(user, nb_name)
    nb = db_utils.get_notebooks(user)[0]
    content1 = 'First note'
    content2 = 'Second note'

    db_utils.add_note_to_db(nb['id'], content1)
    db_utils.add_note_to_db(nb['id'], content2)
    notes = db_utils.get_notes_from_db(nb['id'])
    assert content1 in notes
    assert content2 in notes



def test_hash_and_verify_password(tmp_path, monkeypatch):
    
    class DummyHasher:
        @staticmethod
        def hash(pw):
            raise RuntimeError("bcrypt not available")
        @staticmethod
        def check_pw(pw, hashed):
            raise RuntimeError("bcrypt check fails")

    monkeypatch.setattr(auth, 'stauth', type('m', (), {'Hasher': DummyHasher}))
    password = 's3cr3t!'
    
    hashed = auth.hash_password(password)
    assert hashed != password
    
    assert not auth.verify_password(password, hashed)


def test_verify_password_bcrypt(monkeypatch):
    
    class DummyHasher2:
        @staticmethod
        def hash(pw):
            return f"hashed-{pw}"
        @staticmethod
        def check_pw(pw, hashed):
            return hashed == f"hashed-{pw}"

    monkeypatch.setattr(auth, 'stauth', type('m', (), {'Hasher': DummyHasher2}))
    pwd = 'my_pw'
    hpw = auth.hash_password(pwd)
    assert auth.verify_password(pwd, hpw)
    assert not auth.verify_password('wrong', hpw)
