"""워크플로 무한루프 가드: recursion 라우팅 / 씬 상한 / HITL 상한."""
import os

os.environ["TESTING"] = "True"

from app.services.workflow import (
    MAX_HITL_FEEDBACK_ROUNDS,
    MAX_JUDGE_EDITOR_LOOPS,
    MAX_SCENES_PER_EPISODE,
    WORKFLOW_RECURSION_LIMIT,
    _cap_scenes,
    route_after_judge,
    route_after_next_scene,
    route_after_plotter,
    route_after_user_review,
    workflow_run_config,
)


def test_recursion_limit_is_conservative():
    assert 8 <= WORKFLOW_RECURSION_LIMIT <= 60
    cfg = workflow_run_config({"thread_id": "t1"})
    assert cfg["recursion_limit"] == WORKFLOW_RECURSION_LIMIT
    assert cfg["configurable"]["thread_id"] == "t1"


def test_cap_scenes():
    scenes = [{"title": f"s{i}", "plot": "p"} for i in range(MAX_SCENES_PER_EPISODE + 5)]
    capped = _cap_scenes(scenes)
    assert len(capped) == MAX_SCENES_PER_EPISODE
    assert capped[-1]["index"] == MAX_SCENES_PER_EPISODE - 1


def test_route_after_plotter_stops_on_empty_or_failed():
    assert route_after_plotter({"status": "failed", "scenes": []}) == "stop"
    assert route_after_plotter({"status": "cancelled", "scenes": [{"plot": "x"}]}) == "stop"
    assert route_after_plotter({"status": "plotting", "scenes": []}) == "stop"
    assert route_after_plotter({
        "status": "plotting",
        "scenes": [{"title": "a", "plot": "p"}],
    }) == "continue"


def test_route_after_next_scene_bounds():
    scenes = [{"plot": "a"}, {"plot": "b"}]
    assert route_after_next_scene({
        "status": "plotting",
        "scenes": scenes,
        "current_scene_index": 0,
    }) == "continue"
    assert route_after_next_scene({
        "status": "plotting",
        "scenes": scenes,
        "current_scene_index": 2,
    }) == "stop"
    assert route_after_next_scene({
        "status": "failed",
        "scenes": scenes,
        "current_scene_index": 0,
    }) == "stop"


def test_judge_editor_loop_cap():
    base = {
        "status": "judging_failed",
        "loop_count": MAX_JUDGE_EDITOR_LOOPS - 1,
        "current_scene_index": 0,
        "scenes": [{"plot": "a"}, {"plot": "b"}],
    }
    assert route_after_judge(base) == "editor"
    base["loop_count"] = MAX_JUDGE_EDITOR_LOOPS
    assert route_after_judge(base) == "user_review"  # not last scene
    base["current_scene_index"] = 1
    assert route_after_judge(base) == "reviewer"


def test_hitl_feedback_round_cap():
    assert route_after_user_review({
        "user_feedback": "고쳐줘",
        "loop_count": MAX_HITL_FEEDBACK_ROUNDS - 1,
    }) == "editor"
    assert route_after_user_review({
        "user_feedback": "또 고쳐줘",
        "loop_count": MAX_HITL_FEEDBACK_ROUNDS,
    }) == "save"
    assert route_after_user_review({"user_feedback": None, "loop_count": 99}) == "save"
