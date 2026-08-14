import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

def test_profile_export_csv():
    """CSV export endpoint'i test et."""
    from routers.api import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    with patch('database.get_conn') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'user_id', 'INT', 1000, 0.0, 950, '1', '1000', '500.5',
             False, None, 'User ID', 'Primary key', 'admin', 'core')
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        response = client.get('/api/profile-export/1?format=csv')
        assert response.status_code == 200
        assert 'text/csv' in response.headers['content-type']

def test_profile_export_json():
    """JSON export endpoint'i test et."""
    from routers.api import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    with patch('database.get_conn') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, 'email', 'VARCHAR', 1000, 0.1, 950, None, None, None,
             True, 'email', 'Email Address', 'Contact info', 'data_team', 'pii')
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        response = client.get('/api/profile-export/1?format=json')
        assert response.status_code == 200
        assert 'application/json' in response.headers['content-type']
