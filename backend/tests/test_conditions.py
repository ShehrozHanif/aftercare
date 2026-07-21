"""Tests for GET /conditions — the pluggable-protocol inspection endpoint."""


async def test_conditions_lists_all_three_implemented(client):
    res = await client.get("/conditions")
    assert res.status_code == 200
    body = res.json()

    by_name = {c["name"]: c for c in body}
    assert {"heart_failure", "post_surgical", "copd"} <= set(by_name)

    for c in body:
        assert c["implemented"] is True
        # every real protocol has both urgent and warning signs + questions
        assert len(c["signs"]["urgent"]) > 0
        assert len(c["signs"]["warning"]) > 0
        assert len(c["intro_questions"]) > 0


async def test_condition_signs_are_descriptions_not_keywords(client):
    body = (await client.get("/conditions")).json()
    hf = next(c for c in body if c["name"] == "heart_failure")
    # descriptions are human sentences, e.g. "Chest pain or pressure"
    assert any("chest pain" in s.lower() for s in hf["signs"]["urgent"])
