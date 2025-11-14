import types
import time

from generative_agents.modules.storage.index import LlamaIndex


class FakeTextNode:
    def __init__(self, text, id_, metadata):
        self.text = text
        self.id_ = id_
        self.metadata = metadata
        self.excluded_llm_metadata_keys = []
        self.excluded_embed_metadata_keys = []


class FakeDocStore:
    def __init__(self):
        self.docs = {}


class FakeStorageContext:
    def __init__(self, persist_calls):
        self.persist_calls = persist_calls
    def persist(self, path):
        self.persist_calls.append(path)


class FakeIndex:
    def __init__(self):
        self.docstore = FakeDocStore()
        self.storage_context = FakeStorageContext(persist_calls=[])
        self._retriever_args = None
        self._query_args = None
    def insert_nodes(self, nodes):
        for n in nodes:
            self.docstore.docs[n.id_] = n
    def delete_nodes(self, node_ids, delete_from_docstore=True):
        for nid in list(node_ids):
            self.docstore.docs.pop(nid, None)
    def as_retriever(self, **kwargs):
        self._retriever_args = kwargs
        return self
    def retrieve(self, text):
        # Return nodes with a `score` attribute; mimic llama-index NodeWithScore
        class NodeWithScore:
            def __init__(self, node_id, score, metadata):
                self.id_ = node_id
                self.score = score
                self.metadata = metadata
        return [NodeWithScore(nid, i+1, node.metadata) for i, (nid, node) in enumerate(self.docstore.docs.items())]
    def as_query_engine(self, **kwargs):
        self._query_args = kwargs
        return self
    def query(self, text):
        class R:
            def __init__(self, t):
                self.response = t
            def __str__(self):
                return t
        return R(text)


def make_li_instance(tmp_path=None):
    li = LlamaIndex.__new__(LlamaIndex)
    li._config = {"max_nodes": 0}
    li._index = FakeIndex()
    li._path = str(tmp_path) if tmp_path else None
    return li


def test_add_find_remove_cleanup_and_save(tmp_path):
    li = make_li_instance(tmp_path)

    # add_node increments ids and stores nodes
    n1 = li.add_node("t1", metadata={"create": "20240101-00:00:00", "expire": "20250101-00:00:00"})
    n2 = li.add_node("t2", metadata={"create": "20230101-00:00:00", "expire": "20240101-00:00:00"})
    assert li.has_node(n1.id_) and li.find_node(n2.id_).text == "t2"

    # cleanup removes expired or future/invalid ranges
    removed = li.cleanup()
    assert isinstance(removed, list)

    # remove_nodes
    li.remove_nodes([n1.id_])
    assert not li.has_node(n1.id_)

    # save persists
    li.save(tmp_path)
    assert li._index.storage_context.persist_calls and str(tmp_path) in li._index.storage_context.persist_calls[-1]


def test_retrieve_and_query_paths(monkeypatch):
    li = make_li_instance()

    # Preload some nodes
    li.add_node("hello", metadata={"create": "20240101-00:00:00", "expire": "20250101-00:00:00"})
    li.add_node("world", metadata={"create": "20240101-00:00:00", "expire": "20250101-00:00:00"})

    # retrieve with default retriever
    nodes = li.retrieve("q")
    assert len(nodes) >= 1

    # retrieve with custom retriever creator
    class DummyRetriever:
        def __init__(self, idx, similarity_top_k=5, filters=None, node_ids=None):
            self.idx = idx
            self.kw = {"similarity_top_k": similarity_top_k, "filters": filters, "node_ids": node_ids}
        def retrieve(self, text):
            return []
    nodes2 = li.retrieve("q", retriever_creator=DummyRetriever)
    assert nodes2 == []

    # query engine default & custom
    out = li.query("hello")
    assert str(out).find("hello") >= 0

    class DummyQE:
        def __init__(self, retriever):
            self.retriever = retriever
        def query(self, text):
            return types.SimpleNamespace(response="ok")
    out2 = li.query("x", query_creator=lambda **kw: DummyQE(**kw))
    assert out2.response == "ok"
