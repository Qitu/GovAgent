from generative_agents.modules.memory.spatial import Spatial


def test_spatial_init_default_sleeping_address():
    s = Spatial(tree={"living_area": {"room": ["bed"]}}, address={"living_area": ["home", "room"]})
    # Should inject sleeping/Sleep address based on living_area
    assert "Sleep" in s.address and s.address["Sleep"][-1] in ["床", "bed"]


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
