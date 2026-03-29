"""
Pytest configuration and fixtures
Shared test utilities and fixtures for all tests
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import os
from datetime import datetime, timedelta
import mysql.connector.pooling as mysql_pooling


class _TestNoOpPool:
    """Lightweight stand-in for mysql pool during tests."""

    def __init__(self, *args, **kwargs):
        self._connection = Mock()

    def get_connection(self):
        return self._connection


mysql_pooling.MySQLConnectionPool = _TestNoOpPool



@pytest.fixture
def mock_db_connection():
    """Fixture providing a mocked database connection"""
    mock_connection = Mock()
    mock_connection.is_connected.return_value = True
    mock_connection.start_transaction = Mock()
    mock_connection.commit = Mock()
    mock_connection.rollback = Mock()
    return mock_connection


@pytest.fixture
def mock_db_cursor(mock_db_connection):
    """Fixture providing a mocked database cursor"""
    mock_cursor = Mock()
    mock_db_connection.cursor.return_value = mock_cursor
    return mock_cursor


@pytest.fixture
def mock_db_dict_cursor(mock_db_connection):
    """Fixture providing a mocked dictionary cursor"""
    mock_cursor = Mock()
    mock_db_connection.cursor.return_value = mock_cursor
    return mock_cursor


@pytest.fixture
def patched_get_connection(mock_db_connection):
    """Fixture to patch get_connection_with_retry globally"""
    with patch('db_pool.get_connection_with_retry') as mock_get_conn:
        mock_get_conn.return_value = mock_db_connection
        yield mock_get_conn




@pytest.fixture
def sample_user_trader():
    """Fixture providing sample trader user data"""
    return {
        'user_id': 1,
        'full_name': 'John Trader',
        'email': 'john.trader@example.com',
        'password_hash': 'hashed_password_123',
        'role': 'trader',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_user_carrier():
    """Fixture providing sample carrier user data"""
    return {
        'user_id': 2,
        'full_name': 'Jane Carrier',
        'email': 'jane.carrier@example.com',
        'password_hash': 'hashed_password_456',
        'role': 'carrier',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_carrier_profile(sample_user_carrier):
    """Fixture providing sample carrier profile"""
    return {
        'id': 1,
        'user_id': sample_user_carrier['user_id'],
        'company_name': 'FastShip Logistics',
        'average_rating': 4.5,
        'total_shipments': 150,
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_trader_profile(sample_user_trader):
    """Fixture providing sample trader profile"""
    return {
        'id': 1,
        'user_id': sample_user_trader['user_id'],
        'company_name': 'Global Imports Ltd',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_route():
    """Fixture providing sample route data"""
    return {
        'id': 1,
        'origin_city': 'Lagos',
        'destination_city': 'Accra',
        'distance_km': 600
    }


@pytest.fixture
def sample_container(sample_carrier_profile, sample_route):
    """Fixture providing sample container data"""
    return {
        'id': 1,
        'carrier_id': sample_carrier_profile['id'],
        'route_id': sample_route['id'],
        'container_type': '20ft',
        'max_weight_kg': 10000,
        'max_cbm': 30,
        'price_weight': 5.0,
        'price_cbm': 10.0,
        'departure_date': (datetime.now() + timedelta(days=7)).date(),
        'status': 'open',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_shipment(sample_user_trader, sample_container):
    """Fixture providing sample shipment data"""
    return {
        'id': 1,
        'trader_id': 1,
        'container_id': sample_container['id'],
        'total_weight_kg': 5000,
        'total_cbm': 15,
        'status': 'pending',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_shipment_items():
    """Fixture providing sample shipment items"""
    return [
        {
            'id': 1,
            'shipment_id': 1,
            'product_name': 'Electronics',
            'product_type': 'Fragile',
            'weight_kg': 100,
            'cbm': 50
        },
        {
            'id': 2,
            'shipment_id': 1,
            'product_name': 'Textiles',
            'product_type': 'Bulk',
            'weight_kg': 200,
            'cbm': 80
        }
    ]


@pytest.fixture
def sample_booking(sample_shipment, sample_container):
    """Fixture providing sample booking data"""
    return {
        'id': 1,
        'shipment_id': sample_shipment['id'],
        'container_id': sample_container['id'],
        'booking_status': 'confirmed',
        'created_at': datetime.now()
    }


@pytest.fixture
def sample_payment(sample_booking):
    """Fixture providing sample payment data"""
    return {
        'id': 1,
        'booking_id': sample_booking['id'],
        'amount': 50000,
        'payment_status': 'completed',
        'transaction_ref': 'TXN_123456789',
        'created_at': datetime.now()
    }




@pytest.fixture
def flask_app():
    """Fixture providing Flask app for testing"""
    from main import app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def flask_client(flask_app):
    """Fixture providing Flask test client"""
    return flask_app.test_client()


@pytest.fixture
def flask_request_context(flask_app):
    """Fixture providing Flask request context"""
    with flask_app.test_request_context() as ctx:
        yield ctx


@pytest.fixture
def session_with_trader(flask_request_context):
    """Fixture providing session with logged-in trader"""
    from flask import session
    session['user_email'] = 'trader@example.com'
    session['user_role'] = 'trader'
    session['user_id'] = 1
    return session


@pytest.fixture
def session_with_carrier(flask_request_context):
    """Fixture providing session with logged-in carrier"""
    from flask import session
    session['user_email'] = 'carrier@example.com'
    session['user_role'] = 'carrier'
    session['user_id'] = 2
    return session




def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# FIXTURES FOR ENVIRONMENT SETUP

@pytest.fixture(autouse=True)
def load_test_env():
    """Fixture to load test environment variables"""
    test_env = {
        'app_secret_key': 'test-secret-key',
        'server_ip': 'localhost',
        'server_password': 'test_password',
        'DB_POOL_SIZE': '10'
    }
    
    with patch.dict(os.environ, test_env):
        yield


# FIXTURES FOR COMMON ASSERTIONS

@pytest.fixture
def assert_valid_email_format():
    """Fixture providing email validation function"""
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def validate(email):
        return bool(re.match(email_pattern, email))
    
    return validate


@pytest.fixture
def assert_password_strength():
    """Fixture providing password strength validation"""
    def validate(password):
        # Minimum 8 characters
        if len(password) < 8:
            return False
        # At least one uppercase
        if not any(c.isupper() for c in password):
            return False
        # At least one digit
        if not any(c.isdigit() for c in password):
            return False
        return True
    
    return validate


# HELPER FIXTURES

@pytest.fixture
def reset_token():
    """Fixture providing test reset token"""
    import secrets
    return secrets.token_urlsafe(32)


@pytest.fixture
def valid_container_status():
    """Fixture providing valid container statuses"""
    return ["open", "full", "in_transit", "completed", "cancelled"]


@pytest.fixture
def valid_shipment_status():
    """Fixture providing valid shipment statuses"""
    return ["pending", "confirmed", "in_transit", "delivered", "cancelled"]
