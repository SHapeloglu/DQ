# Bu dosya: /api/profile-export/{id} endpoint'inin CSV ve JSON çıktılarını test eder. Veritabanı yerine sahte (MagicMock) bağlantı kullanılır.
# patch('database.get_conn'): gerçek bağlantı fonksiyonu geçici olarak sahte ile değiştirilir; test bitince eski haline döner.
# TestClient: sunucu açmadan FastAPI uygulamasına HTTP isteği gönderen test aracıdır.
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
    
    with patch('database.get_conn') as mock_get_conn, patch('database.release_conn'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            'source_id': 1, 'column_name': 'user_id', 'col_type': 'INT', 'row_count': 1000,
            'null_pct': 0.0, 'distinct_count': 950, 'min_val': '1', 'max_val': '1000', 'avg_val': '500.5',
            'is_pii': False, 'pii_type': None, 'business_name': 'User ID',
            'description': 'Primary key', 'owner': 'admin', 'tags': 'core'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # format=csv: yanıt text/csv içerikli olmalı.
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
    
    with patch('database.get_conn') as mock_get_conn, patch('database.release_conn'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            'source_id': 1, 'column_name': 'email', 'col_type': 'VARCHAR', 'row_count': 1000,
            'null_pct': 0.1, 'distinct_count': 950, 'min_val': None, 'max_val': None, 'avg_val': None,
            'is_pii': True, 'pii_type': 'email', 'business_name': 'Email Address',
            'description': 'Contact info', 'owner': 'data_team', 'tags': 'pii'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # format=json: yanıt application/json içerikli olmalı.
        response = client.get('/api/profile-export/1?format=json')
        assert response.status_code == 200
        assert 'application/json' in response.headers['content-type']


def test_profile_export_404_when_no_profile():
    """Profil kaydı yoksa 404 dönmeli (500'e çevrilmemeli)."""
    from routers.api import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch('database.get_conn') as mock_get_conn, patch('database.release_conn'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        response = client.get('/api/profile-export/999?format=csv')
        assert response.status_code == 404


def test_profile_export_csv_icerik_ve_baglanti_iadesi():
    """Sözlük satırları CSV'ye doğru yazılmalı ve bağlantı her durumda havuza iade edilmeli."""
    from routers.api import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch('database.get_conn') as mock_get_conn, patch('database.release_conn') as mock_release:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            'source_id': 1, 'column_name': 'email', 'col_type': 'VARCHAR', 'row_count': 10,
            'null_pct': 0.5, 'distinct_count': 9, 'min_val': 'a', 'max_val': 'z', 'avg_val': None,
            'is_pii': True, 'pii_type': 'email', 'business_name': 'E-posta',
            'description': 'd', 'owner': 'o', 'tags': 't'}]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        response = client.get('/api/profile-export/1?format=csv')
        assert response.status_code == 200
        body = response.text
        assert 'Column,Type,RowCount' in body.splitlines()[0]
        assert 'email,VARCHAR,10,0.5,9,a,z,0,Yes,email' in body
        mock_release.assert_called_once_with(mock_conn)


def test_profile_export_404_bağlantı_iade_edilir():
    """Kayıt yoksa 404 dönmeli ve bağlantı yine de iade edilmeli."""
    from routers.api import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch('database.get_conn') as mock_get_conn, patch('database.release_conn') as mock_release:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        response = client.get('/api/profile-export/999?format=json')
        assert response.status_code == 404
        mock_release.assert_called_once_with(mock_conn)
