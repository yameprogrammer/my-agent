import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
import ui.api_client as api_client

@pytest.fixture
def mock_st_session_state():
    with patch("ui.api_client.st.session_state", {"token": "test_token"}):
        yield

def test_get_headers_with_token(mock_st_session_state):
    headers = api_client.get_headers()
    assert headers == {"Authorization": "Bearer test_token"}

@patch("ui.api_client.st.session_state", {})
def test_get_headers_without_token():
    headers = api_client.get_headers()
    assert headers == {}

@patch("ui.api_client.requests.post")
def test_login(mock_post):
    mock_response = MagicMock()
    mock_post.return_value = mock_response
    
    res = api_client.login("testuser", "testpass")
    
    mock_post.assert_called_once_with(
        f"{api_client.BASE_URL}/auth/login", 
        data={"username": "testuser", "password": "testpass"}
    )
    assert res == mock_response

@patch("ui.api_client.requests.post")
def test_create_project(mock_post, mock_st_session_state):
    mock_response = MagicMock()
    mock_post.return_value = mock_response
    
    res = api_client.create_project("My Title", "Desc", "openai", "gpt-4o", "key")
    
    mock_post.assert_called_once_with(
        f"{api_client.BASE_URL}/projects",
        json={
            "title": "My Title",
            "description": "Desc",
            "llm_provider": "openai",
            "llm_model": "gpt-4o",
            "api_key_override": "key"
        },
        headers={"Authorization": "Bearer test_token"}
    )
    assert res == mock_response

@patch("ui.api_client.requests.get")
def test_get_projects(mock_get, mock_st_session_state):
    mock_response = MagicMock()
    mock_get.return_value = mock_response
    
    res = api_client.get_projects()
    mock_get.assert_called_once_with(
        f"{api_client.BASE_URL}/projects",
        headers={"Authorization": "Bearer test_token"}
    )
    assert res == mock_response

@patch("ui.api_client.requests.post")
def test_create_episode(mock_post, mock_st_session_state):
    mock_response = MagicMock()
    mock_post.return_value = mock_response
    
    res = api_client.create_episode(1, 1, "Ep 1")
    
    mock_post.assert_called_once_with(
        f"{api_client.BASE_URL}/projects/1/episodes",
        json={
            "episode_number": 1,
            "title": "Ep 1"
        },
        headers={"Authorization": "Bearer test_token"}
    )
    assert res == mock_response
