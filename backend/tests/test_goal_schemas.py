import pytest
from pydantic import ValidationError

from app.schemas.goal import GoalCreate, GoalUpdate


def test_focus_goal_ok():
    g = GoalCreate(type="daily_focus_min", target_value=180)
    assert g.app_name is None


def test_app_goal_needs_app_name():
    with pytest.raises(ValidationError):
        GoalCreate(type="max_app_min", target_value=60)
    assert GoalCreate(type="max_app_min", target_value=60, app_name="Chrome").app_name == "Chrome"


def test_app_name_not_allowed_for_other_goals():
    with pytest.raises(ValidationError):
        GoalCreate(type="daily_focus_min", target_value=60, app_name="Chrome")


def test_target_bounds():
    with pytest.raises(ValidationError):
        GoalCreate(type="max_task_switches", target_value=0)
    with pytest.raises(ValidationError):
        GoalCreate(type="daily_focus_min", target_value=2000)  # > 1440 minutes
    assert GoalCreate(type="max_task_switches", target_value=2000).target_value == 2000


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        GoalCreate(type="something_else", target_value=10)


def test_update_is_partial():
    assert GoalUpdate(is_active=False).model_dump(exclude_unset=True) == {"is_active": False}
