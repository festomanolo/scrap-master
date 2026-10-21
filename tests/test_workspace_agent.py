from scrap_master import ai, workspace
from scrap_master.agent import _relevant, fallback_plan
from scrap_master.utils.harvest import HarvestItem


def test_new_project_creates_standard_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "workspace_root", lambda: tmp_path)
    p = workspace.new_project("Form 2 Computer Exams!")
    assert p.name.endswith("_form-2-computer-exams")
    assert all((p / d).is_dir() for d in workspace.PROJECT_DIRS)
    assert workspace.new_project("Form 2 Computer Exams!") != p


def test_parse_json_tolerates_fences():
    assert ai.parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_fallback_plan_picks_up_urls():
    plan = fallback_plan("grab pdfs from https://x.org/list please")
    assert plan["urls"] == ["https://x.org/list"]


def test_relevant_filters_by_keyword():
    items = [HarvestItem("https://a/computer.pdf", "file", "s"), HarvestItem("https://a/chem.pdf", "file", "s")]
    assert [i.url for i in _relevant(items, "computer exams")] == ["https://a/computer.pdf"]
