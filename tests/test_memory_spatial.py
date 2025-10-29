from generative_agents.modules.memory.spatial import Spatial


def test_spatial_init_default_sleeping_address():
    s = Spatial(tree={"living_area": {"room": ["bed"]}}, address={"living_area": ["home", "room"]})
    # Should inject sleeping/睡觉 address based on living_area
    assert "睡觉" in s.address and s.address["睡觉"][-1] in ["床", "bed"]


def test_spatial_add_leaf_and_get_leaves():
    s = Spatial(tree={})
    s.add_leaf(["home", "room", "bed"])
    s.add_leaf(["home", "room", "desk"])
    leaves = s.get_leaves(["home", "room"])
    assert set(leaves) >= {"bed", "desk"}


def test_spatial_find_and_random_address():
    s = Spatial(tree={"a": {"b": ["c", "d"]}}, address={"target": ["a", "b", "c"]})
    assert s.find_address("target", as_list=True) == ["a", "b", "c"]
    ra = s.random_address()
    assert len(ra) == 3 and ra[0] in {"a"}
