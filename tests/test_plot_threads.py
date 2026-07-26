"""IDEA-03 plot thread schema/status validation (unit, no DB)."""
from app.schemas.plot_thread import PlotThreadCreate, PlotThreadUpdate


def test_plot_thread_create_defaults():
    p = PlotThreadCreate(title="검은 편지")
    assert p.status == "open"
    assert p.description == ""


def test_plot_thread_update_partial():
    u = PlotThreadUpdate(status="resolved")
    d = u.model_dump(exclude_unset=True)
    assert d == {"status": "resolved"}
