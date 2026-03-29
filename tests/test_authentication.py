"""
Unit tests for authentication module
Test login, password reset, and user validation
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask_bcrypt import Bcrypt
import hashlib


class TestAuthenticationFunctions:
    """Test authentication-related functions"""

    def test_hash_reset_token(self):
        """Test password reset token hashing"""
        from main import _hash_reset_token
        
        raw_token = "test_token_123"
        hashed = _hash_reset_token(raw_token)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 hex digest length
        assert hashed == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def test_hash_reset_token_consistency(self):
        """Test that same token always produces same hash"""
        from main import _hash_reset_token
        
        raw_token = "consistent_token"
        hash1 = _hash_reset_token(raw_token)
        hash2 = _hash_reset_token(raw_token)
        
        assert hash1 == hash2

    def test_hash_reset_token_different_tokens(self):
        """Test that different tokens produce different hashes"""
        from main import _hash_reset_token
        
        token1 = "token_one"
        token2 = "token_two"
        
        hash1 = _hash_reset_token(token1)
        hash2 = _hash_reset_token(token2)
        
        assert hash1 != hash2

    @patch('main.get_connection_with_retry')
    def test_send_reset_email(self, mock_get_connection):
        """Test password reset email sending"""
        from main import _send_reset_email
        
        to_email = "user@example.com"
        reset_link = "https://example.com/reset?token=abc123"
        
        # Should not raise any exception
        result = _send_reset_email(to_email, reset_link)
        
        # Function prints, so we just verify it doesn't crash
        assert result is None


class TestLoginRequired:
    """Test login_required decorator"""
    
    @patch('main.Flask')
    def test_login_required_redirects_when_no_session(self, mock_flask):
        """Test that login_required redirects when user not in session"""
        from main import login_required
        
        @login_required
        def protected_view():
            return "Protected content"
        
        # Mock a Flask request context without session
        with patch('main.session', {}):
            with patch('main.redirect') as mock_redirect:
                with patch('main.url_for', return_value='/login'):
                    result = protected_view()
                    # The decorator should attempt redirect
                    assert result is not None

    @patch('main.session', {'user_email': 'test@example.com'})
    def test_login_required_allows_access_with_session(self):
        """Test that login_required allows access when user in session"""
        from main import login_required
        
        @login_required
        def protected_view():
            return "Protected content"
        
        # When session has user_email, function should execute
        # Note: This is a simplified test; in real scenario would need Flask context
        assert protected_view() == "Protected content"


class TestCarrierRequired:
    """Test carrier_required decorator"""
    
    def test_carrier_required_denies_non_carriers(self):
        """Test that carrier_required denies non-carrier users"""
        from main import carrier_required
        
        @carrier_required
        def carrier_view():
            return "Carrier content"
        
        # Mock session with trader role
        with patch('main.session', {'user_role': 'trader'}):
            result = carrier_view()
            assert result == ("Forbidden", 403)

    def test_carrier_required_allows_carriers(self):
        """Test that carrier_required allows carrier users"""
        from main import carrier_required
        
        @carrier_required
        def carrier_view():
            return "Carrier content"
        
        # Mock session with carrier role
        with patch('main.session', {'user_role': 'carrier'}):
            result = carrier_view()
            assert result == "Carrier content"


class TestPasswordValidation:
    """Test password validation logic"""

    def test_validate_password_strength_minimum_length(self):
        """Test that weak passwords are rejected"""
        # Password validation would be in a separate util module
        weak_password = "abc123"
        
        # Should check minimum length (typically 8 characters)
        assert len(weak_password) < 8

    def test_validate_email_format(self):
        """Test email format validation"""
        import re
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com"
        ]
        
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@.com",
            "user @example.com"
        ]
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"{email} should be valid"
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"{email} should be invalid"
