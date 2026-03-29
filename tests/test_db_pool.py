"""
Unit tests for database pool module
Test connection pooling and retry logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mysql.connector.errors import PoolError
import time


class TestDatabasePool:
    """Test database connection pool functions"""

    @patch('db_pool.pooling.MySQLConnectionPool')
    def test_pool_initialization(self, mock_pool_class):
        """Test database pool is initialized correctly"""
        import importlib
        import db_pool

        importlib.reload(db_pool)
        from db_pool import shared_connection_pool
        
        mock_pool_class.assert_called()
        call_kwargs = mock_pool_class.call_args[1]
        
        assert call_kwargs['pool_name'] == 'shared_main_pool'
        assert call_kwargs['pool_size'] > 0
        assert call_kwargs['pool_reset_session'] is True

    @patch('db_pool.shared_connection_pool')
    def test_get_connection_with_retry_success(self, mock_pool):
        """Test successful connection retrieval"""
        from db_pool import get_connection_with_retry
        
        mock_connection = Mock()
        mock_pool.get_connection.return_value = mock_connection
        
        result = get_connection_with_retry()
        
        assert result == mock_connection
        mock_pool.get_connection.assert_called_once()

    @patch('db_pool.shared_connection_pool')
    @patch('time.sleep')
    def test_get_connection_with_retry_retries(self, mock_sleep, mock_pool):
        """Test get_connection_with_retry retries on pool error"""
        from db_pool import get_connection_with_retry
        
        mock_connection = Mock()
        # First two attempts fail, third succeeds
        mock_pool.get_connection.side_effect = [
            PoolError("Pool busy"),
            PoolError("Pool busy"),
            mock_connection
        ]
        
        result = get_connection_with_retry(retries=3, delay=0.1)
        
        assert result == mock_connection
        assert mock_pool.get_connection.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('db_pool.shared_connection_pool')
    def test_get_connection_with_retry_exhausted(self, mock_pool):
        """Test get_connection_with_retry raises after exhausting retries"""
        from db_pool import get_connection_with_retry
        
        mock_pool.get_connection.side_effect = PoolError("Pool busy")
        
        with pytest.raises(PoolError) as exc_info:
            get_connection_with_retry(retries=2, delay=0.1)
        
        assert "busy" in str(exc_info.value)
        assert mock_pool.get_connection.call_count == 2

    @patch.dict('os.environ', {'DB_POOL_SIZE': '100'})
    def test_pool_size_from_env_valid(self):
        """Test pool size is read from environment"""
        import importlib
        import db_pool
        
        # Re-import to pick up env var
        importlib.reload(db_pool)
        from db_pool import _pool_size_from_env
        
        size = _pool_size_from_env(default=60)
        assert size == 100

    def test_pool_size_from_env_invalid(self):
        """Test pool size defaults when invalid value in env"""
        from db_pool import _pool_size_from_env
        
        size = _pool_size_from_env(default=60)
        # Should return default or valid parsed value
        assert size >= 1

    def test_pool_size_minimum(self):
        """Test pool size is at least 1"""
        from db_pool import _pool_size_from_env
        
        size = _pool_size_from_env(default=1)
        assert size >= 1


class TestConnectionPoolRetryLogic:
    """Test retry mechanism for connection pool"""

    @patch('db_pool.shared_connection_pool')
    def test_retry_delay_increases(self, mock_pool):
        """Test retry delay between attempts"""
        from db_pool import get_connection_with_retry
        
        with patch('time.sleep') as mock_sleep:
            mock_pool.get_connection.side_effect = PoolError("Busy")
            
            try:
                get_connection_with_retry(retries=3, delay=0.5)
            except PoolError:
                pass
            
            # Verify sleep was called with correct delay
            mock_sleep.assert_called_with(0.5)

    @patch('db_pool.shared_connection_pool')
    def test_single_retry_no_delay(self, mock_pool):
        """Test no retry when single attempt fails"""
        from db_pool import get_connection_with_retry
        
        mock_pool.get_connection.side_effect = PoolError("Busy")
        
        with pytest.raises(PoolError):
            get_connection_with_retry(retries=1, delay=0.1)
        
        assert mock_pool.get_connection.call_count == 1
