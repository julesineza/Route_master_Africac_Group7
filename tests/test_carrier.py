"""
Unit tests for carrier module
Test carrier-specific functions like container creation and management
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import mysql.connector
from datetime import datetime, timedelta


class TestCreateContainer:
    """Test create_container function"""

    @patch('carrier.get_connection_with_retry')
    def test_create_container_success(self, mock_get_connection):
        """Test successful container creation"""
        from carrier import create_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.commit = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock carrier found
        mock_cursor.fetchone.side_effect = [(1,), None, None]  # carrier_id, then route checks
        mock_cursor.lastrowid = 10  # container_id
        
        result = create_container(
            user_email='carrier@example.com',
            origin='Lagos',
            destination='Accra',
            distance=600,
            cont_type='20ft',
            departure_date='2024-04-01',
            max_weight=10000,
            max_cbm=30,
            price_weight=5.0,
            price_cbm=10.0
        )
        
        assert result[0] is True
        assert result[1] == 10
        mock_connection.commit.assert_called_once()

    @patch('carrier.get_connection_with_retry')
    def test_create_container_no_carrier_profile(self, mock_get_connection):
        """Test create_container fails when carrier profile not found"""
        from carrier import create_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock no carrier found
        mock_cursor.fetchone.return_value = None
        
        result = create_container(
            user_email='unknown@example.com',
            origin='Lagos',
            destination='Accra',
            distance=600,
            cont_type='20ft',
            departure_date='2024-04-01',
            max_weight=10000,
            max_cbm=30,
            price_weight=5.0,
            price_cbm=10.0
        )
        
        assert result[0] is False
        assert "Carrier profile not found" in result[1]
        mock_connection.rollback.assert_called_once()

    @patch('carrier.get_connection_with_retry')
    def test_create_container_database_error(self, mock_get_connection):
        """Test create_container handles database errors"""
        from carrier import create_container
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        
        result = create_container(
            user_email='carrier@example.com',
            origin='Lagos',
            destination='Accra',
            distance=600,
            cont_type='20ft',
            departure_date='2024-04-01',
            max_weight=10000,
            max_cbm=30,
            price_weight=5.0,
            price_cbm=10.0
        )
        
        assert result[0] is False
        assert "failed" in result[1].lower()


class TestShowCarrierContainers:
    """Test show_carrier_containers function"""

    @patch('carrier.get_connection_with_retry')
    def test_show_carrier_containers_success(self, mock_get_connection):
        """Test successful retrieval of carrier containers"""
        from carrier import show_carrier_containers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        expected_containers = [
            {
                'container_id': 1,
                'origin_city': 'Lagos',
                'destination_city': 'Accra',
                'distance_km': 600,
                'container_type': '20ft',
                'max_weight_kg': 10000,
                'max_cbm': 30,
                'price_weight': 5.0,
                'price_cbm': 10.0,
                'departure_date': '2024-04-01'
            }
        ]
        mock_cursor.fetchall.return_value = expected_containers
        
        result = show_carrier_containers('carrier@example.com')
        
        assert result == expected_containers
        mock_cursor.execute.assert_called_once()

    @patch('carrier.get_connection_with_retry')
    def test_show_carrier_containers_empty(self, mock_get_connection):
        """Test show_carrier_containers returns empty list"""
        from carrier import show_carrier_containers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchall.return_value = []
        
        result = show_carrier_containers('unknown@example.com')
        
        assert result == []

    @patch('carrier.get_connection_with_retry')
    def test_show_carrier_containers_database_error(self, mock_get_connection):
        """Test show_carrier_containers handles database errors"""
        from carrier import show_carrier_containers
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        
        result = show_carrier_containers('carrier@example.com')
        
        assert isinstance(result, str)
        assert "Error" in result


class TestGetShipmentItems:
    """Test get_shipment_items function"""

    @patch('carrier.get_connection_with_retry')
    def test_get_shipment_items_success(self, mock_get_connection):
        """Test successful retrieval of shipment items"""
        from carrier import get_shipment_items
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        expected_items = [
            {
                'id': 1,
                'product_name': 'Electronics',
                'product_type': 'Fragile',
                'weight_kg': 50,
                'cbm': 25
            },
            {
                'id': 2,
                'product_name': 'Textiles',
                'product_type': 'Non-fragile',
                'weight_kg': 100,
                'cbm': 40
            }
        ]
        mock_cursor.fetchall.return_value = expected_items
        
        result = get_shipment_items(1)
        
        assert result == expected_items
        mock_cursor.execute.assert_called_once()

    @patch('carrier.get_connection_with_retry')
    def test_get_shipment_items_empty(self, mock_get_connection):
        """Test get_shipment_items returns empty list for non-existent shipment"""
        from carrier import get_shipment_items
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchall.return_value = []
        
        result = get_shipment_items(999)
        
        assert result == []

    @patch('carrier.get_connection_with_retry')
    def test_get_shipment_items_database_error(self, mock_get_connection):
        """Test get_shipment_items handles database errors"""
        from carrier import get_shipment_items
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        
        result = get_shipment_items(1)
        
        assert isinstance(result, str)
        assert "Error" in result


class TestContainerStatusConstant:
    """Test container status constants"""

    def test_allowed_container_statuses(self):
        """Test ALLOWED_CONTAINER_STATUSES constant"""
        from carrier import ALLOWED_CONTAINER_STATUSES
        
        expected_statuses = ("open", "full", "in_transit", "completed", "cancelled")
        assert ALLOWED_CONTAINER_STATUSES == expected_statuses

    def test_allowed_shipment_statuses(self):
        """Test ALLOWED_SHIPMENT_STATUSES constant"""
        from carrier import ALLOWED_SHIPMENT_STATUSES
        
        expected_statuses = ("pending", "confirmed", "in_transit", "delivered", "cancelled")
        assert ALLOWED_SHIPMENT_STATUSES == expected_statuses

    def test_status_validation(self):
        """Test status validation against allowed values"""
        from carrier import ALLOWED_CONTAINER_STATUSES, ALLOWED_SHIPMENT_STATUSES
        
        valid_container_status = "open"
        invalid_container_status = "invalid_status"
        
        assert valid_container_status in ALLOWED_CONTAINER_STATUSES
        assert invalid_container_status not in ALLOWED_CONTAINER_STATUSES
        
        valid_shipment_status = "delivered"
        invalid_shipment_status = "invalid_status"
        
        assert valid_shipment_status in ALLOWED_SHIPMENT_STATUSES
        assert invalid_shipment_status not in ALLOWED_SHIPMENT_STATUSES


class TestGetCarrierContainerDetails:
    """Test get_carrier_container_details_payload function"""

    @patch('carrier.get_connection_with_retry')
    def test_get_carrier_container_details_success(self, mock_get_connection):
        """Test successful retrieval of carrier container details"""
        from carrier import get_carrier_container_details_payload
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        expected_details = {
            'container_id': 1,
            'origin_city': 'Lagos',
            'destination_city': 'Accra',
            'distance_km': 600,
            'container_type': '20ft',
            'max_weight_kg': 10000,
            'max_cbm': 30,
            'price_weight': 5.0,
            'price_cbm': 10.0,
            'departure_date': '2024-04-01',
            'status': 'open',
            'company_name': 'FastShip',
            'carrier_name': 'John Doe',
            'carrier_email': 'john@example.com',
            'carrier_phone': '+234123456789'
        }
        mock_cursor.fetchone.return_value = expected_details
        mock_cursor.fetchall.side_effect = [[], []]
        
        result = get_carrier_container_details_payload('carrier@example.com', 1)

        assert result[1] is None
        assert result[0]["container"] == expected_details

    @patch('carrier.get_connection_with_retry')
    def test_get_carrier_container_details_not_found(self, mock_get_connection):
        """Test get_carrier_container_details returns None when not found"""
        from carrier import get_carrier_container_details_payload
        
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        mock_cursor.fetchone.return_value = None
        
        result = get_carrier_container_details_payload('carrier@example.com', 999)

        assert result == (None, None)
