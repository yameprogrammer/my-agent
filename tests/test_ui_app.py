import pytest
import sys
import os
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock

# Add ui to sys.path so that 'import api_client' works during tests
sys.path.insert(0, os.path.abspath('ui'))
import ui.app

@patch("ui.app.api_client.get_me")
def test_dashboard_login_render(mock_get_me):
    """
    Test that the login page renders when token is not present in session state.
    """
    at = AppTest.from_file("ui/app.py")
    at.run()
    
    # Check that "로그인" title is in the app
    assert "로그인" in at.title[0].value
    
    # Check for text inputs
    assert len(at.text_input) >= 2
    assert at.text_input[0].label == "Username"
    
    # Check buttons
    assert len(at.button) >= 2
    assert at.button[0].label == "로그인"
    assert at.button[1].label == "회원가입"

@patch("ui.app.api_client.get_me")
@patch("ui.app.api_client.get_projects")
def test_dashboard_authenticated(mock_get_projects, mock_get_me):
    """
    Test that the dashboard renders when token is present.
    """
    # Mocking get_me to return a valid user
    mock_me_response = MagicMock()
    mock_me_response.status_code = 200
    mock_me_response.json.return_value = {"username": "testuser"}
    mock_get_me.return_value = mock_me_response
    
    # Mocking get_projects
    mock_projects_response = MagicMock()
    mock_projects_response.status_code = 200
    mock_projects_response.json.return_value = [
        {"id": 1, "title": "Test Proj", "description": "desc", "llm_provider": "openai", "llm_model": "gpt"}
    ]
    mock_get_projects.return_value = mock_projects_response

    at = AppTest.from_file("ui/app.py")
    # Simulate an authenticated session
    at.session_state["token"] = "valid_token"
    at.run()
    
    # The title should be the dashboard title
    assert "내 소설 프로젝트" in at.title[0].value
    
    # Check if project lists are rendered
    assert "Test Proj" in at.markdown[0].value
