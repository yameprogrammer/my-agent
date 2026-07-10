import requests
import streamlit as st

BASE_URL = "http://localhost:8080"

def get_headers():
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def login(username, password):
    response = requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})
    return response

def register(username, password):
    response = requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": password})
    return response

def get_me():
    response = requests.get(f"{BASE_URL}/users/me", headers=get_headers())
    return response

def get_projects():
    response = requests.get(f"{BASE_URL}/projects", headers=get_headers())
    return response

def create_project(title, synopsis, llm_provider="openai", llm_model="gpt-4o-mini", api_key_override=None):
    data = {
        "title": title,
        "synopsis": synopsis,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "api_key_override": api_key_override
    }
    response = requests.post(f"{BASE_URL}/projects", json=data, headers=get_headers())
    return response

def delete_project(project_id):
    response = requests.delete(f"{BASE_URL}/projects/{project_id}", headers=get_headers())
    return response

def get_world_settings(project_id):
    return requests.get(f"{BASE_URL}/projects/{project_id}/world-settings", headers=get_headers())

def create_world_setting(project_id, keyword, category, description):
    data = {"keyword": keyword, "category": category, "description": description}
    return requests.post(f"{BASE_URL}/projects/{project_id}/world-settings", json=data, headers=get_headers())

def delete_world_setting(project_id, setting_id):
    return requests.delete(f"{BASE_URL}/projects/{project_id}/world-settings/{setting_id}", headers=get_headers())

def get_characters(project_id):
    return requests.get(f"{BASE_URL}/projects/{project_id}/characters", headers=get_headers())

def create_character(project_id, name, description, importance):
    data = {"name": name, "description": description, "importance": importance}
    return requests.post(f"{BASE_URL}/projects/{project_id}/characters", json=data, headers=get_headers())

def update_character(project_id, character_id, name, description, importance):
    data = {"name": name, "description": description, "importance": importance}
    return requests.put(f"{BASE_URL}/projects/{project_id}/characters/{character_id}", json=data, headers=get_headers())

def delete_character(project_id, character_id):
    return requests.delete(f"{BASE_URL}/projects/{project_id}/characters/{character_id}", headers=get_headers())

def get_episodes(project_id):
    return requests.get(f"{BASE_URL}/projects/{project_id}/episodes", headers=get_headers())

def create_episode(project_id, episode_number, title, outline=None):
    data = {"episode_number": episode_number, "title": title}
    if outline:
        data["outline"] = outline
    return requests.post(f"{BASE_URL}/projects/{project_id}/episodes", json=data, headers=get_headers())

def delete_episode(project_id, episode_id):
    return requests.delete(f"{BASE_URL}/projects/{project_id}/episodes/{episode_id}", headers=get_headers())

def get_contents(project_id, episode_id):
    return requests.get(f"{BASE_URL}/projects/{project_id}/episodes/{episode_id}/contents", headers=get_headers())

