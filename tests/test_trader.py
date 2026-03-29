"""
Unit tests for trader module
Test trader-specific functions like routes, carriers, bookings
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import mysql.connector


class TestGetRoutes:
    """Test getRoutes function"""

    @patch('trader.get_connection_with_retry')
    def test_get_routes_success(self, mock_get_connection):
        """Test successful retrieval of routes"""
        from trader import getRoutes
        
        # Mock connection and cursor
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        # Mock query results
        expected_routes = [
            ('Lagos', 'Accra'),
            ('Lagos', 'Nairobi'),
            ('Accra', 'Nairobi')
        ]
        mock_cursor.fetchall.return_value = expected_routes
        
        result = getRoutes()
        
        assert result == expected_routes
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_get_routes_database_error(self, mock_get_connection):
        """Test getRoutes handles database errors"""
        from trader import getRoutes
        
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Simulate database error
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        
        result = getRoutes()
        
        assert result[0] is False
        assert "Error" in result[1]
        mock_connection.rollback.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_get_routes_connection_error(self, mock_get_connection):
        """Test getRoutes handles connection errors"""
        from trader import getRoutes
        
        # Simulate connection failure
        mock_get_connection.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            getRoutes()


class TestGetCarriers:
    """Test getCarriers function"""

    @patch('trader.get_connection_with_retry')
    def test_get_carriers_success(self, mock_get_connection):
        """Test successful retrieval of carriers"""
        from trader import getCarriers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        # Mock carrier data
        expected_carriers = [
            {
                'container_id': 1,
                'container_type': '20ft',
                'max_weight_kg': 10000,
                'max_cbm': 30,
                'price_weight': 5.0,
                'price_cbm': 10.0,
                'departure_date': '2024-04-01',
                'status': 'open',
                'origin_city': 'Lagos',
                'destination_city': 'Accra',
                'distance_km': 600,
                'company_name': 'FastShip',
                'average_rating': 4.5,
                'used_weight': 5000,
                'used_cbm': 15,
                'fullness_percentage': 50
            }
        ]
        mock_cursor.fetchall.return_value = expected_carriers
        
        result = getCarriers()
        
        assert result == expected_carriers
        mock_cursor.execute.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_get_carriers_with_filters(self, mock_get_connection):
        """Test getCarriers with origin and destination filters"""
        from trader import getCarriers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchall.return_value = []
        
        result = getCarriers(origin='Lagos', destination='Accra', limit=5)
        
        # Verify query was executed with parameters
        call_args = mock_cursor.execute.call_args
        assert 'Lagos' in str(call_args)
        assert 'Accra' in str(call_args)

    @patch('trader.get_connection_with_retry')
    def test_get_carriers_with_limit(self, mock_get_connection):
        """Test getCarriers respects limit parameter"""
        from trader import getCarriers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchall.return_value = []
        
        getCarriers(limit=20)
        
        call_args = mock_cursor.execute.call_args
        # LIMIT should be in the query
        assert 'LIMIT' in str(call_args[0][0])


class TestGetContainerById:
    """Test getContainerById function"""

    @patch('trader.get_connection_with_retry')
    def test_get_container_by_id_success(self, mock_get_connection):
        """Test successful retrieval of container by ID"""
        from trader import getContainerById
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        expected_container = {
            'container_id': 1,
            'container_type': '20ft',
            'max_weight_kg': 10000,
            'max_cbm': 30,
            'origin_city': 'Lagos',
            'destination_city': 'Accra',
            'distance_km': 600,
            'company_name': 'FastShip',
            'carrier_name': 'John Doe',
            'carrier_email': 'john@example.com',
            'carrier_phone': '+234123456789',
            'status': 'open'
        }
        mock_cursor.fetchone.return_value = expected_container
        
        result = getContainerById(1)
        
        assert result == expected_container
        mock_cursor.execute.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_get_container_by_id_not_found(self, mock_get_connection):
        """Test getContainerById returns None when not found"""
        from trader import getContainerById
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchone.return_value = None
        
        result = getContainerById(999)
        
        assert result is None


class TestBookContainer:
    """Test book_container function"""

    @patch('trader.get_connection_with_retry')
    def test_book_container_success(self, mock_get_connection):
        """Test successful container booking"""
        from trader import book_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.commit = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            (1,),
            ("open", 10000, 100, 5.0, 10.0),
        ]
        mock_cursor.lastrowid = 100  # shipment_id
        
        result = book_container(
            user_email='trader@example.com',
            container_id=1,
            product_names=['Item1'],
            product_types=['Type1'],
            weights=[100.0],
            cbms=[50.0]
        )
        
        assert result[0] is True
        mock_connection.commit.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_book_container_invalid_items(self, mock_get_connection):
        """Test book_container rejects empty items"""
        from trader import book_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        result = book_container(
            user_email='trader@example.com',
            container_id=1,
            product_names=[],
            product_types=[],
            weights=[],
            cbms=[]
        )
        
        assert result[0] is False
        assert "at least one" in result[1].lower()
        mock_connection.rollback.assert_called_once()

    @patch('trader.get_connection_with_retry')
    def test_book_container_mismatched_items(self, mock_get_connection):
        """Test book_container rejects mismatched item arrays"""
        from trader import book_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        result = book_container(
            user_email='trader@example.com',
            container_id=1,
            product_names=['Item1', 'Item2'],
            product_types=['Type1'],  # Mismatched length
            weights=[100.0, 200.0],
            cbms=[50.0, 60.0]
        )
        
        assert result[0] is False
        assert "Invalid" in result[1]

    @patch('trader.get_connection_with_retry')
    def test_book_container_invalid_weights(self, mock_get_connection):
        """Test book_container validates weight values"""
        from trader import book_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        result = book_container(
            user_email='trader@example.com',
            container_id=1,
            product_names=['Item1'],
            product_types=['Type1'],
            weights=['not_a_number'],
            cbms=[50.0]
        )
        
        assert result[0] is False
        assert "valid numbers" in result[1].lower()

    @patch('trader.get_connection_with_retry')
    def test_book_container_negative_weight(self, mock_get_connection):
        """Test book_container rejects negative weights"""
        from trader import book_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        result = book_container(
            user_email='trader@example.com',
            container_id=1,
            product_names=['Item1'],
            product_types=['Type1'],
            weights=[-100.0],
            cbms=[50.0]
        )
        
        assert result[0] is False
