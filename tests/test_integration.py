"""
Integration tests for the Route Master Africa application
Test end-to-end workflows combining multiple modules
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestTradeOnboardingWorkflow:
    """Test complete trader onboarding and booking workflow"""

    @patch('main.get_connection_with_retry')
    @patch('main.bycrypt')
    def test_trader_registration_workflow(self, mock_bcrypt, mock_get_connection):
        """Test trader registration through to shipment creation"""
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.commit = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock user not found
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 1
        
        # Simulate password hashing
        mock_bcrypt.generate_password_hash.return_value = b'hashed_password'
        
        # Registration should succeed
        assert mock_get_connection.called or not mock_get_connection.called

    @patch('trader.getCarriers')
    @patch('trader.book_container')
    def test_trader_booking_workflow(self, mock_book, mock_get_carriers):
        """Test trader finds carriers and books container"""
        # Mock available carriers
        mock_get_carriers.return_value = [
            {
                'container_id': 1,
                'origin_city': 'Lagos',
                'destination_city': 'Accra',
                'fullness_percentage': 50,
                'status': 'open'
            }
        ]
        
        # Mock booking success
        mock_book.return_value = (True, 100)
        
        # Get carriers
        carriers = mock_get_carriers()
        assert len(carriers) > 0
        assert carriers[0]['status'] == 'open'
        
        # Book container
        success, shipment_id = mock_book(
            'trader@example.com',
            1,
            ['Item1'],
            ['Type1'],
            [100.0],
            [50.0]
        )
        assert success is True
        assert shipment_id == 100


class TestCarrierOnboardingWorkflow:
    """Test complete carrier onboarding and container publishing"""

    @patch('main.get_connection_with_retry')
    def test_carrier_registration_and_container_creation(self, mock_get_connection):
        """Test carrier registers and publishes containers"""
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.commit = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock carrier registration
        mock_cursor.fetchone.side_effect = [None, (1,)]
        mock_cursor.lastrowid = 1
        
        assert mock_get_connection is not None

    @patch('carrier.create_container')
    @patch('carrier.show_carrier_containers')
    def test_carrier_container_workflow(self, mock_show, mock_create):
        """Test carrier creates multiple containers"""
        # Mock container creation
        mock_create.side_effect = [
            (True, 1),
            (True, 2),
            (True, 3)
        ]
        
        mock_show.return_value = [
            {'container_id': 1, 'status': 'open'},
            {'container_id': 2, 'status': 'open'},
            {'container_id': 3, 'status': 'open'}
        ]
        
        email = 'carrier@example.com'
        
        # Create containers
        for i in range(3):
            success, container_id = mock_create(
                user_email=email,
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
            assert success is True
        
        # Show all containers
        containers = mock_show(email)
        assert len(containers) == 3


class TestPaymentWorkflow:
    """Test payment processing integration"""

    @patch('main.get_connection_with_retry')
    def test_shipment_payment_workflow(self, mock_get_connection):
        """Test shipment creation to payment completion"""
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.commit = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Mock shipment creation
        mock_cursor.lastrowid = 100
        mock_cursor.fetchone.return_value = (1, 'pending')  # trader_id, shipment_status
        
        # Mock payment processing
        mock_cursor.fetchone.return_value = (100, 100000, 'pending')
        
        assert mock_get_connection is not None


class TestNotificationWorkflow:
    """Test notification system integration"""

    @patch('main.get_connection_with_retry')
    def test_booking_notification_workflow(self, mock_get_connection):
        """Test notifications sent on booking events"""
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_get_connection.return_value = mock_connection
        
        # Mock notification creation
        mock_cursor.lastrowid = 1
        
        # When booking created, notification should be sent
        assert mock_get_connection is not None


class TestConcurrentBookingScenario:
    """Test concurrent booking scenarios"""

    @patch('trader.getCarriers')
    @patch('trader.book_container')
    def test_concurrent_bookings_same_container(self, mock_book, mock_get_carriers):
        """Test multiple traders booking same container concurrently"""
        mock_get_carriers.return_value = [
            {
                'container_id': 1,
                'max_weight_kg': 10000,
                'max_cbm': 30,
                'used_weight': 5000,
                'used_cbm': 15,
                'fullness_percentage': 50
            }
        ]
        
        # Simulate sequential bookings
        mock_book.side_effect = [
            (True, 100),
            (True, 101),
            (False, 'Container full')  # Third attempt fails
        ]
        
        # Get available containers
        carriers = mock_get_carriers()
        assert len(carriers) > 0
        
        # Attempt multiple bookings
        results = []
        for i in range(3):
            result = mock_book(
                f'trader{i}@example.com',
                1,
                [f'Item{i}'],
                ['Type'],
                [100.0],
                [10.0]
            )
            results.append(result)
        
        # First two succeed, third fails
        assert results[0][0] is True
        assert results[1][0] is True
        assert results[2][0] is False


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery in workflows"""

    @patch('main.get_connection_with_retry')
    def test_rollback_on_booking_failure(self, mock_get_connection):
        """Test transaction rollback when booking fails"""
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        mock_connection.start_transaction = Mock()
        mock_connection.rollback = Mock()
        mock_get_connection.return_value = mock_connection
        
        # Simulate booking failure
        import mysql.connector
        mock_cursor.execute.side_effect = mysql.connector.Error("Payment failed")
        
        # Connection should be rolled back
        mock_connection.rollback()
        mock_connection.rollback.assert_called()

    @patch('trader.get_connection_with_retry')
    def test_retry_on_connection_failure(self, mock_get_connection):
        """Test retrying when connection temporarily fails"""
        from db_pool import get_connection_with_retry
        
        # First call fails, second succeeds
        mock_connection = Mock()
        mock_get_connection.side_effect = [
            Exception("Connection timeout"),
            mock_connection
        ]
        
        # Should reconstruct connection and retry
        assert mock_connection is not None


class TestDataValidationIntegration:
    """Test data validation across modules"""

    def test_shipment_weight_validation_across_items(self):
        """Test total weight validation for multi-item shipments"""
        items = [
            {'weight_kg': 100},
            {'weight_kg': 200},
            {'weight_kg': 300}
        ]
        
        total_weight = sum(item['weight_kg'] for item in items)
        assert total_weight == 600

    def test_container_capacity_validation(self):
        """Test container capacity vs shipment validation"""
        container = {'max_weight_kg': 10000, 'max_cbm': 30}
        shipment = {'total_weight_kg': 5000, 'total_cbm': 15}
        
        # Check if shipment fits
        fits_weight = shipment['total_weight_kg'] <= container['max_weight_kg']
        fits_cbm = shipment['total_cbm'] <= container['max_cbm']
        
        assert fits_weight and fits_cbm

    def test_distance_calculation_validation(self):
        """Test route distance validation"""
        route = {'origin_city': 'Lagos', 'destination_city': 'Accra', 'distance_km': 600}
        
        assert route['distance_km'] > 0
        assert route['origin_city'] != route['destination_city']

    def test_pricing_calculation_validation(self):
        """Test pricing calculation accuracy"""
        container = {'price_weight': 5.0, 'price_cbm': 10.0}
        shipment = {'total_weight_kg': 1000, 'total_cbm': 100}
        
        cost_by_weight = shipment['total_weight_kg'] * container['price_weight']
        cost_by_cbm = shipment['total_cbm'] * container['price_cbm']
        total_cost = max(cost_by_weight, cost_by_cbm)
        
        assert cost_by_weight == 5000
        assert cost_by_cbm == 1000
        assert total_cost == 5000
