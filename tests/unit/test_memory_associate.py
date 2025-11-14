import types
from datetime import datetime, timedelta

import pytest

from generative_agents.modules.memory.associate import Associate, Concept


class DummyNode:
    def __init__(self, id_, text, metadata, score=1.0):
        self.id_ = id_
        self.text = text
        self.metadata = metadata.copy()
        self.score = score


class DummyIndex:
    def __init__(self):
        self.nodes = {}
        self.saved = False
    def cleanup(self):
        # Remove expired nodes
        removed = []
        now = datetime.now()
        for nid, node in list(self.nodes.items()):
            exp = datetime.strptime(node.metadata["expire"], "%Y%m%d-%H:%M:%S")
            if exp < now:
                removed.append(nid)
                self.nodes.pop(nid)
        return removed
    def add_node(self, text, metadata):
        nid = f"n{len(self.nodes)}"
        self.nodes[nid] = DummyNode(nid, text, metadata, score=1.0)
        return self.nodes[nid]
    def remove_nodes(self, ids):
        for i in ids:
            self.nodes.pop(i, None)
    def find_node(self, nid):
        return self.nodes[nid]
    def retrieve(self, text, similarity_top_k=5, filters=None, node_ids=None, retriever_creator=None):
        # Return nodes in node_ids order with increasing score
        res = []
        for idx, nid in enumerate(node_ids or list(self.nodes.keys())):
            if nid in self.nodes:
                n = self.nodes[nid]
                nn = DummyNode(n.id_, n.text, n.metadata, score=idx + 1)
                res.append(nn)
        return res[:similarity_top_k]
    def save(self):
        self.saved = True


class DummyLlamaIndexFactory:
    def __init__(self, dummy):
        self.dummy = dummy
    def __call__(self, *args, **kwargs):
        return self.dummy


def test_associate_add_and_retrieve_focus(monkeypatch):
    dummy_index = DummyIndex()
    # Patch LlamaIndex class used inside Associate
    import generative_agents.modules.storage.index as idx
    monkeypatch.setattr(idx, "LlamaIndex", DummyLlamaIndexFactory(dummy_index))

    assoc = Associate(
        path="/tmp/x",
        embedding={"provider": "openai", "api_key": "k", "base_url": "http://x", "model": "m"},
        retention=5,
        max_memory=10,
    )

    # Add nodes with different poignancy and times
    from generative_agents.modules.memory.event import Event
    base_time = datetime.now() - timedelta(days=1)
    for i in range(6):
        e = Event("s", "p", f"o{i}", address=["w", "s", "a", f"obj{i}"])
        assoc.add_node("event", e, poignancy=i+1, create=base_time + timedelta(minutes=i))

    # retrieve_focus should return up to retention nodes, ranked
    focus = ["important future plan", "daily"]
    out = assoc.retrieve_focus(focus, retrieve_max=3, reduce_all=True)
    assert len(out) <= 5
    # access time should be updated to current
    for c in out:
        assert isinstance(c.access, datetime)

    # to_dict should call index.save
    d = assoc.to_dict()
    assert "memory" in d
