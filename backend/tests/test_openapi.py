from app.main import OPENAPI_TAGS, app


def used_tags() -> set[str]:
    schema = app.openapi()
    return {
        tag
        for path in schema["paths"].values()
        for op in path.values()
        for tag in op.get("tags", [])
    }


def test_every_route_tag_is_declared_so_swagger_keeps_the_feature_order() -> None:
    declared = [tag["name"] for tag in OPENAPI_TAGS]
    assert used_tags() <= set(declared)


def test_no_declared_tag_is_left_empty() -> None:
    declared = {tag["name"] for tag in OPENAPI_TAGS}
    assert declared <= used_tags()


def test_feature_groups_come_in_feature_order() -> None:
    names = [tag["name"] for tag in app.openapi()["tags"]]
    firsts = [next(i for i, n in enumerate(names) if n.startswith(f"F{k} ")) for k in range(1, 6)]
    assert firsts == sorted(firsts)
