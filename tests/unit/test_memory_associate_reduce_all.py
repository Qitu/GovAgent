from datetime import datetime, timedelta

from generative_agents.modules.memory.associate import Associate


class DummyNode:
    def __init__(self, id_, text, metadata, score=1.0):
        self.id_ = id_
        self.text = text
        self.metadata = metadata.copy()
        self.score = score


class DummyIndex:
    def __init__(self):
        self.nodes = {}
    def cleanup(self):
        return []
    def add_node(self, text, metadata):
        nid = f"n{len(self.nodes)}"
        node = DummyNode(nid, text, metadata, score=1.0)
        self.nodes[nid] = node
        return node
    def remove_nodes(self, ids):
        for i in ids:
            self.nodes.pop(i, None)
    def find_node(self, nid):
        return self.nodes[nid]
    def retrieve(self, text, similarity_top_k=5, filters=None, node_ids=None, retriever_creator=None):
        res = []
        for idx, nid in enumerate(node_ids or list(self.nodes.keys())):
            if nid in self.nodes:
                n = self.nodes[nid]
                nn = DummyNode(n.id_, n.text, n.metadata, score=idx + 1)
                res.append(nn)
        return res[:similarity_top_k]
    def save(self):
        pass


def test_retrieve_focus_group_by_query(monkeypatch):
    dummy_index = DummyIndex()
    import generative_agents.modules.storage.index as idx
    monkeypatch.setattr(idx, "LlamaIndex", lambda *a, **k: dummy_index)

    assoc = Associate(
        path="/tmp/x",
        embedding={"provider": "openai", "api_key": "k", "base_url": "http://x", "model": "m"},
        retention=5,
        max_memory=10,
    )

    from generative_agents.modules.memory.event import Event
    base_time = datetime.now() - timedelta(days=1)
    for i in range(4):
        e = Event("s", "p", f"o{i}", address=["w","s","a",f"obj{i}"])
        assoc.add_node("event", e, poignancy=i+1, create=base_time + timedelta(minutes=i))

    focus = ["topic1", "topic2"]
    out_map = assoc.retrieve_focus(focus, retrieve_max=3, reduce_all=False)
    assert set(out_map.keys()) == set(focus)
    for v in out_map.values():
        assert len(v) <= 5
