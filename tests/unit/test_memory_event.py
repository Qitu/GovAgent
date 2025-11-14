from generative_agents.modules.memory.event import Event


def test_event_str_and_update():
    # __str__ should include describe or fallback to subject predicate object and address
    e = Event("Alice", "is", "reading", address=["home", "sofa"])
    s1 = str(e)
    assert "Alice" in s1 and "reading" in s1 and "home:sofa" in s1

    e.update(describe="Alice focuses on reading")
    s2 = str(e)
    assert "focuses on reading" in s2 and "home:sofa" in s2


def test_event_equality_and_id():
    e1 = Event("Bob", "is", "idle")
    e2 = Event("Bob", "is", "idle")
    assert e1 == e2
    assert e1.to_id() == ("Bob", "is", "idle", "")


def test_event_fit_and_dict():
    e = Event("Bob", "does", "work", describe="Bob does work")
    assert e.fit(subject="Bob", predicate="does", object="work")
    assert not e.fit(subject="Alice")
    d = e.to_dict()
    assert d["subject"] == "Bob" and d["predicate"] == "does"


def test_event_get_describe_subject_prefix_logic():
    e = Event("Alice", "does", "coding")
    # with subject
    desc_with = e.get_describe(with_subject=True)
    assert desc_with.startswith("Alice ")
    # without subject
    desc_no = e.get_describe(with_subject=False)
    assert not desc_no.startswith("Alice ")


def test_event_from_list():
    e3 = Event.from_list(["A", "B", "C"])
    assert e3.subject == "A" and e3.object == "C"
    e4 = Event.from_list(["A", "B", "C", ["x", "y"]])
    assert e4.address == ["x", "y"]
