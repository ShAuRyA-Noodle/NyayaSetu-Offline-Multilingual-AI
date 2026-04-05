"""
Connectivity Manager Tests

Comprehensive test suite for the ConnectivityManager module.
Tests connectivity detection, monitoring, callbacks, and quality assessment.

Author: NyayaSetu Team
Version: 1.0.0
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from src.sync.connectivity import (
    ConnectivityManager,
    ConnectionStatus,
    ConnectionQuality,
    ConnectionInfo,
    quick_check
)


class TestConnectivityManager(unittest.TestCase):
    """Test suite for ConnectivityManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ConnectivityManager(
            check_interval=1,  # Fast for testing
            timeout=2
        )
    
    def tearDown(self):
        """Clean up after tests."""
        if self.manager._monitoring:
            self.manager.stop_monitoring()
    
    # ========================================================================
    # INITIALIZATION TESTS
    # ========================================================================
    
    def test_initialization(self):
        """Test manager initializes correctly."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.check_interval, 1)
        self.assertEqual(self.manager.timeout, 2)
        self.assertFalse(self.manager._monitoring)
    
    def test_custom_endpoints(self):
        """Test custom check endpoints."""
        custom_endpoints = ["https://example.com"]
        manager = ConnectivityManager(check_endpoints=custom_endpoints)
        self.assertEqual(manager.check_endpoints, custom_endpoints)
    
    # ========================================================================
    # CONNECTION CHECKING TESTS
    # ========================================================================
    
    @patch('connectivity.requests.get')
    def test_online_detection(self, mock_get):
        """Test detection of online status."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        info = self.manager.check_connection(force=True)
        
        self.assertEqual(info.status, ConnectionStatus.ONLINE)
        self.assertTrue(self.manager.is_online())
        self.assertFalse(self.manager.is_offline())
    
    @patch('connectivity.requests.get')
    def test_offline_detection(self, mock_get):
        """Test detection of offline status."""
        # Mock connection error
        mock_get.side_effect = requests.ConnectionError("Network unreachable")
        
        info = self.manager.check_connection(force=True)
        
        self.assertEqual(info.status, ConnectionStatus.OFFLINE)
        self.assertTrue(self.manager.is_offline())
        self.assertFalse(self.manager.is_online())
    
    @patch('connectivity.requests.get')
    def test_latency_measurement(self, mock_get):
        """Test latency measurement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        info = self.manager.check_connection(force=True)
        
        self.assertIsNotNone(info.latency_ms)
        self.assertGreater(info.latency_ms, 0)
    
    # ========================================================================
    # QUALITY ASSESSMENT TESTS
    # ========================================================================
    
    def test_quality_excellent(self):
        """Test excellent quality assessment."""
        quality = self.manager._assess_quality(True, 50)
        self.assertEqual(quality, ConnectionQuality.EXCELLENT)
    
    def test_quality_good(self):
        """Test good quality assessment."""
        quality = self.manager._assess_quality(True, 200)
        self.assertEqual(quality, ConnectionQuality.GOOD)
    
    def test_quality_fair(self):
        """Test fair quality assessment."""
        quality = self.manager._assess_quality(True, 500)
        self.assertEqual(quality, ConnectionQuality.FAIR)
    
    def test_quality_poor(self):
        """Test poor quality assessment."""
        quality = self.manager._assess_quality(True, 1500)
        self.assertEqual(quality, ConnectionQuality.POOR)
    
    def test_quality_unavailable(self):
        """Test unavailable quality assessment."""
        quality = self.manager._assess_quality(False, None)
        self.assertEqual(quality, ConnectionQuality.UNAVAILABLE)
    
    # ========================================================================
    # STATUS CALLBACK TESTS
    # ========================================================================
    
    @patch('connectivity.requests.get')
    def test_status_callback(self, mock_get):
        """Test status change callback."""
        callback = Mock()
        self.manager.register_status_callback(callback)
        
        # First check - online
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        self.manager.check_connection(force=True)
        
        # Second check - offline
        mock_get.side_effect = requests.ConnectionError()
        self.manager.check_connection(force=True)
        
        # Callback should be called once (status changed)
        callback.assert_called_once()
        args = callback.call_args[0]
        self.assertEqual(args[0], ConnectionStatus.ONLINE)
        self.assertEqual(args[1], ConnectionStatus.OFFLINE)
    
    @patch('connectivity.requests.get')
    def test_quality_callback(self, mock_get):
        """Test quality change callback."""
        callback = Mock()
        self.manager.register_quality_callback(callback)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        self.manager.check_connection(force=True)
        
        # Callback should be called
        callback.assert_called()
    
    def test_unregister_callbacks(self):
        """Test unregistering callbacks."""
        callback = Mock()
        self.manager.register_status_callback(callback)
        self.manager.unregister_all_callbacks()
        
        self.assertEqual(len(self.manager._status_callbacks), 0)
    
    # ========================================================================
    # MONITORING TESTS
    # ========================================================================
    
    def test_start_monitoring(self):
        """Test starting monitoring."""
        self.manager.start_monitoring()
        
        self.assertTrue(self.manager._monitoring)
        self.assertIsNotNone(self.manager._monitor_thread)
        self.assertTrue(self.manager._monitor_thread.is_alive())
    
    def test_stop_monitoring(self):
        """Test stopping monitoring."""
        self.manager.start_monitoring()
        time.sleep(0.5)
        self.manager.stop_monitoring()
        
        self.assertFalse(self.manager._monitoring)
    
    @patch('connectivity.requests.get')
    def test_monitoring_updates_status(self, mock_get):
        """Test monitoring continuously updates status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        self.manager.start_monitoring()
        time.sleep(2)  # Let it run for 2 checks
        
        # Should have checked at least once
        self.assertGreater(mock_get.call_count, 0)
    
    # ========================================================================
    # CONTEXT MANAGER TESTS
    # ========================================================================
    
    def test_context_manager(self):
        """Test using ConnectivityManager as context manager."""
        with ConnectivityManager(check_interval=1) as manager:
            self.assertTrue(manager._monitoring)
        
        # Should stop monitoring on exit
        self.assertFalse(manager._monitoring)
    
    # ========================================================================
    # HELPER FUNCTION TESTS
    # ========================================================================
    
    @patch('connectivity.socket.create_connection')
    def test_quick_check_online(self, mock_socket):
        """Test quick_check when online."""
        mock_socket.return_value = Mock()
        
        result = quick_check()
        
        self.assertTrue(result)
    
    @patch('connectivity.socket.create_connection')
    def test_quick_check_offline(self, mock_socket):
        """Test quick_check when offline."""
        mock_socket.side_effect = OSError("Network unreachable")
        
        result = quick_check()
        
        self.assertFalse(result)
    
    # ========================================================================
    # CONNECTION INFO TESTS
    # ========================================================================
    
    def test_connection_info_to_dict(self):
        """Test ConnectionInfo serialization."""
        info = self.manager.get_connection_info()
        data = info.to_dict()
        
        self.assertIn("status", data)
        self.assertIn("quality", data)
        self.assertIn("latency_ms", data)
        self.assertIsInstance(data, dict)
    
    def test_get_connection_info(self):
        """Test getting connection info."""
        info = self.manager.get_connection_info()
        
        self.assertIsInstance(info, ConnectionInfo)
        self.assertIsInstance(info.status, ConnectionStatus)
        self.assertIsInstance(info.quality, ConnectionQuality)
    
    # ========================================================================
    # EDGE CASE TESTS
    # ========================================================================
    
    @patch('connectivity.requests.get')
    def test_multiple_endpoint_fallback(self, mock_get):
        """Test fallback to alternative endpoints."""
        # First endpoint fails, second succeeds
        mock_get.side_effect = [
            requests.ConnectionError(),
            Mock(status_code=200)
        ]
        
        info = self.manager.check_connection(force=True)
        
        self.assertEqual(info.status, ConnectionStatus.ONLINE)
        self.assertEqual(mock_get.call_count, 2)
    
    @patch('connectivity.requests.get')
    def test_degraded_connection(self, mock_get):
        """Test degraded connection detection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Simulate high latency by using assess_quality directly
        quality = self.manager._assess_quality(True, 1500)
        self.assertEqual(quality, ConnectionQuality.POOR)
    
    @patch('connectivity.requests.get')
    def test_consecutive_failures(self, mock_get):
        """Test tracking consecutive failures."""
        mock_get.side_effect = requests.ConnectionError()
        
        # Check 3 times
        for _ in range(3):
            self.manager.check_connection(force=True)
        
        info = self.manager.get_connection_info()
        self.assertEqual(info.consecutive_failures, 3)
        self.assertEqual(info.consecutive_successes, 0)
    
    @patch('connectivity.requests.get')
    def test_wait_for_connection(self, mock_get):
        """Test waiting for connection."""
        # First 2 attempts fail, third succeeds
        mock_get.side_effect = [
            requests.ConnectionError(),
            requests.ConnectionError(),
            Mock(status_code=200)
        ]
        
        result = self.manager.wait_for_connection(timeout=10)
        
        self.assertTrue(result)
    
    @patch('connectivity.requests.get')
    def test_wait_for_connection_timeout(self, mock_get):
        """Test wait_for_connection timeout."""
        mock_get.side_effect = requests.ConnectionError()
        
        result = self.manager.wait_for_connection(timeout=3)
        
        self.assertFalse(result)
    
    # ========================================================================
    # API ENDPOINT TESTS
    # ========================================================================
    
    @patch('connectivity.requests.get')
    def test_api_endpoint_check(self, mock_get):
        """Test checking custom API endpoint."""
        manager = ConnectivityManager(
            api_endpoint="http://localhost:8000"
        )
        
        # First regular endpoints fail, API succeeds
        mock_get.side_effect = [
            requests.ConnectionError(),
            requests.ConnectionError(),
            requests.ConnectionError(),
            Mock(status_code=200)  # API health check
        ]
        
        info = manager.check_connection(force=True)
        
        # Should eventually succeed via API endpoint
        self.assertEqual(info.status, ConnectionStatus.ONLINE)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)