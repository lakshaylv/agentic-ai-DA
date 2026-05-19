import pandas as pd

from backend.services.session_service import SessionStore


class TestSessionStore:
    def test_create_and_get(self, sample_df):
        store = SessionStore()
        sid = store.create(sample_df, filename="test.csv")
        df = store.get(sid)
        assert df is not None
        assert df.shape == sample_df.shape

    def test_list_sessions(self, sample_df):
        store = SessionStore()
        sid = store.create(sample_df)
        sessions = store.list_sessions()
        assert any(s["session_id"] == sid for s in sessions)

    def test_get_metadata(self, sample_df):
        store = SessionStore()
        sid = store.create(sample_df, filename="test.csv")
        meta = store.get_metadata(sid)
        assert meta is not None
        assert meta["filename"] == "test.csv"
        assert meta["row_count"] == 5

    def test_delete(self, sample_df):
        store = SessionStore()
        sid = store.create(sample_df)
        assert store.delete(sid) is True
        assert store.get(sid) is None

    def test_delete_nonexistent(self):
        store = SessionStore()
        assert store.delete("nonexistent") is False

    def test_get_nonexistent(self):
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_thread_safety(self, sample_df):
        store = SessionStore()
        import threading
        sids = []

        def create_session():
            sids.append(store.create(sample_df))

        threads = [threading.Thread(target=create_session) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(sids) == 10
        assert len(store.list_sessions()) == 10
