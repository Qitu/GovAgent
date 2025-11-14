import types

import pytest

from generative_agents.modules.storage.index import LlamaIndex


class FlakyIndex:
    def __init__(self):
        self.docstore = types.SimpleNamespace(docs={})
        self.storage_context = types.SimpleNamespace(persist=lambda path: None)
        self._insert_calls = 0
        self._as_qe_calls = 0
    def insert_nodes(self, nodes):
        self._insert_calls += 1
        if self._insert_calls == 1:
            raise RuntimeError("temporary failure")
        for n in nodes:
            self.docstore.docs[n.id_] = n
    def as_retriever(self, **kwargs):
        return self
    def as_query_engine(self, **kwargs):
        self._as_qe_calls += 1
        if self._as_qe_calls == 1:
            raise RuntimeError("temporary failure qe")
        return self
    def query(self, text):
        return types.SimpleNamespace(response=text)


def make_li_flaky(monkeypatch):
    li = LlamaIndex.__new__(LlamaIndex)
    li._config = {"max_nodes": 0}
    li._index = FlakyIndex()
    li._path = None
    # avoid actual sleep in retry loops
    import time as _time
    monkeypatch.setattr(_time, "sleep", lambda s: None)
    return li


def test_add_node_retry_and_query_retry(monkeypatch):
    li = make_li_flaky(monkeypatch)
    n = li.add_node("t", metadata={"create": "20240101-00:00:00", "expire": "20250101-00:00:00"})
    assert n.id_ in li._index.docstore.docs

    out = li.query("x")
    assert out.response == "x"


def test_retrieve_exception_returns_empty():
    li = LlamaIndex.__new__(LlamaIndex)
    li._config = {"max_nodes": 0}
    li._index = types.SimpleNamespace()  # minimal
    def bad_retriever(*a, **k):
        raise RuntimeError("boom")
    out = li.retrieve("q", retriever_creator=bad_retriever)
    assert out == []
