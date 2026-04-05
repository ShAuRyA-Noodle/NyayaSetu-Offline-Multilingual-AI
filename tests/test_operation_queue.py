"""
Operation Queue Tests

Comprehensive test suite for the OperationQueue module.
Tests queuing, processing, persistence, retry logic, and priority handling.

Author: NyayaSetu Team
Version: 1.0.0
"""

import unittest
import tempfile
import os
import time
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.sync.operation_queue import (
    OperationQueue,
    QueuedOperation,
    OperationType,
    OperationStatus,
    OperationPriority
)


class TestOperationQueue(unittest.TestCase):
    """Test suite for OperationQueue."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        
        self.queue = OperationQueue(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.queue._processing:
            self.queue.stop_auto_processing()
        
        # Delete temp database
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    # ========================================================================
    # INITIALIZATION TESTS
    # ========================================================================
    
    def test_initialization(self):
        """Test queue initializes correctly."""
        self.assertIsNotNone(self.queue)
        self.assertEqual(self.queue.db_path, self.temp_db.name)
        self.assertFalse(self.queue._processing)
    
    def test_database_creation(self):
        """Test database is created."""
        self.assertTrue(os.path.exists(self.temp_db.name))
    
    # ========================================================================
    # ENQUEUE/DEQUEUE TESTS
    # ========================================================================
    
    def test_enqueue_operation(self):
        """Test enqueueing operation."""
        op = QueuedOperation(
            type=OperationType.API_REQUEST,
            endpoint="/api/test",
            data={"key": "value"}
        )
        
        op_id = self.queue.enqueue(op)
        
        self.assertIsNotNone(op_id)
        self.assertEqual(self.queue.get_pending_count(), 1)
    
    def test_dequeue_operation(self):
        """Test dequeueing operation."""
        op = QueuedOperation(
            endpoint="/api/test",
            data={"key": "value"}
        )
        self.queue.enqueue(op)
        
        dequeued = self.queue.dequeue()
        
        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued.endpoint, "/api/test")
        self.assertEqual(dequeued.status, OperationStatus.PROCESSING)
    
    def test_dequeue_empty_queue(self):
        """Test dequeueing from empty queue."""
        dequeued = self.queue.dequeue()
        self.assertIsNone(dequeued)
    
    def test_dequeue_priority_order(self):
        """Test operations are dequeued by priority."""
        # Add low priority
        op1 = QueuedOperation(
            endpoint="/api/low",
            priority=OperationPriority.LOW
        )
        self.queue.enqueue(op1)
        
        # Add high priority
        op2 = QueuedOperation(
            endpoint="/api/high",
            priority=OperationPriority.HIGH
        )
        self.queue.enqueue(op2)
        
        # High priority should be dequeued first
        dequeued = self.queue.dequeue()
        self.assertEqual(dequeued.endpoint, "/api/high")
    
    # ========================================================================
    # STATUS UPDATE TESTS
    # ========================================================================
    
    def test_mark_completed(self):
        """Test marking operation as completed."""
        op = QueuedOperation(endpoint="/api/test")
        op_id = self.queue.enqueue(op)
        
        self.queue.mark_completed(op_id)
        
        updated = self.queue.get_operation(op_id)
        self.assertEqual(updated.status, OperationStatus.COMPLETED)
    
    def test_mark_failed(self):
        """Test marking operation as failed."""
        op = QueuedOperation(endpoint="/api/test", max_retries=3)
        op_id = self.queue.enqueue(op)
        
        self.queue.mark_failed(op_id, "Test error")
        
        updated = self.queue.get_operation(op_id)
        self.assertEqual(updated.retry_count, 1)
        self.assertEqual(updated.status, OperationStatus.RETRY)
        self.assertEqual(updated.last_error, "Test error")
    
    def test_max_retries_exceeded(self):
        """Test operation marked failed after max retries."""
        op = QueuedOperation(endpoint="/api/test", max_retries=2)
        op_id = self.queue.enqueue(op)
        
        # Fail twice
        self.queue.mark_failed(op_id, "Error 1")
        self.queue.mark_failed(op_id, "Error 2")
        
        updated = self.queue.get_operation(op_id)
        self.assertEqual(updated.status, OperationStatus.FAILED)
        self.assertEqual(updated.retry_count, 2)
    
    def test_cancel_operation(self):
        """Test cancelling operation."""
        op = QueuedOperation(endpoint="/api/test")
        op_id = self.queue.enqueue(op)
        
        self.queue.cancel_operation(op_id)
        
        updated = self.queue.get_operation(op_id)
        self.assertEqual(updated.status, OperationStatus.CANCELLED)
    
    # ========================================================================
    # PROCESSING TESTS
    # ========================================================================
    
    def test_process_all_success(self):
        """Test processing all operations successfully."""
        # Add operations
        for i in range(3):
            op = QueuedOperation(endpoint=f"/api/test{i}")
            self.queue.enqueue(op)
        
        # Mock executor that always succeeds
        def executor(operation):
            return True
        
        stats = self.queue.process_all(executor)
        
        self.assertEqual(stats["processed"], 3)
        self.assertEqual(stats["succeeded"], 3)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(self.queue.get_pending_count(), 0)
    
    def test_process_all_with_failures(self):
        """Test processing with some failures."""
        # Add operations
        for i in range(3):
            op = QueuedOperation(endpoint=f"/api/test{i}")
            self.queue.enqueue(op)
        
        # Mock executor that fails every other operation
        call_count = [0]
        def executor(operation):
            call_count[0] += 1
            return call_count[0] % 2 == 1
        
        stats = self.queue.process_all(executor)
        
        self.assertEqual(stats["processed"], 3)
        self.assertEqual(stats["succeeded"], 2)
        self.assertEqual(stats["failed"], 1)
    
    def test_process_all_max_operations(self):
        """Test processing limited number of operations."""
        # Add 5 operations
        for i in range(5):
            op = QueuedOperation(endpoint=f"/api/test{i}")
            self.queue.enqueue(op)
        
        def executor(operation):
            return True
        
        # Process only 3
        stats = self.queue.process_all(executor, max_operations=3)
        
        self.assertEqual(stats["processed"], 3)
        self.assertEqual(self.queue.get_pending_count(), 2)
    
    # ========================================================================
    # STATISTICS TESTS
    # ========================================================================
    
    def test_get_stats(self):
        """Test getting queue statistics."""
        # Add operations with different statuses
        op1 = QueuedOperation(endpoint="/api/1")
        op1_id = self.queue.enqueue(op1)
        
        op2 = QueuedOperation(endpoint="/api/2")
        op2_id = self.queue.enqueue(op2)
        self.queue.mark_completed(op2_id)
        
        op3 = QueuedOperation(endpoint="/api/3")
        op3_id = self.queue.enqueue(op3)
        self.queue.mark_failed(op3_id, "Error")
        
        stats = self.queue.get_stats()
        
        self.assertEqual(stats["total"], 3)
        self.assertIn("pending", stats)
        self.assertIn("completed", stats)
    
    def test_get_pending_count(self):
        """Test getting pending operation count."""
        self.assertEqual(self.queue.get_pending_count(), 0)
        
        # Add operations
        for i in range(3):
            op = QueuedOperation(endpoint=f"/api/{i}")
            self.queue.enqueue(op)
        
        self.assertEqual(self.queue.get_pending_count(), 3)
    
    # ========================================================================
    # CLEANUP TESTS
    # ========================================================================
    
    def test_clear_completed(self):
        """Test clearing completed operations."""
        # Add completed operation
        op = QueuedOperation(endpoint="/api/test")
        op_id = self.queue.enqueue(op)
        self.queue.mark_completed(op_id)
        
        # Clear completed
        cleared = self.queue.clear_completed(older_than_days=0)
        
        self.assertEqual(cleared, 1)
        self.assertEqual(self.queue.get_stats()["total"], 0)
    
    def test_clear_all(self):
        """Test clearing all operations."""
        # Add operations
        for i in range(3):
            op = QueuedOperation(endpoint=f"/api/{i}")
            self.queue.enqueue(op)
        
        cleared = self.queue.clear_all()
        
        self.assertEqual(cleared, 3)
        self.assertEqual(self.queue.get_stats()["total"], 0)
    
    # ========================================================================
    # PERSISTENCE TESTS
    # ========================================================================
    
    def test_persistence_across_instances(self):
        """Test operations persist across queue instances."""
        # Add operation
        op = QueuedOperation(endpoint="/api/test", data={"key": "value"})
        op_id = self.queue.enqueue(op)
        
        # Create new queue instance with same database
        queue2 = OperationQueue(db_path=self.temp_db.name)
        
        # Operation should exist
        retrieved = queue2.get_operation(op_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.endpoint, "/api/test")
        self.assertEqual(retrieved.data["key"], "value")
    
    # ========================================================================
    # PRIORITY TESTS
    # ========================================================================
    
    def test_priority_processing(self):
        """Test high priority operations processed first."""
        # Add operations in mixed priority order
        priorities = [
            OperationPriority.LOW,
            OperationPriority.CRITICAL,
            OperationPriority.NORMAL,
            OperationPriority.HIGH
        ]
        
        for i, priority in enumerate(priorities):
            op = QueuedOperation(
                endpoint=f"/api/{i}",
                priority=priority
            )
            self.queue.enqueue(op)
        
        # Dequeue - should get CRITICAL first
        op1 = self.queue.dequeue()
        self.assertEqual(op1.priority, OperationPriority.CRITICAL)
        
        # Then HIGH
        op2 = self.queue.dequeue()
        self.assertEqual(op2.priority, OperationPriority.HIGH)
        
        # Then NORMAL
        op3 = self.queue.dequeue()
        self.assertEqual(op3.priority, OperationPriority.NORMAL)
        
        # Then LOW
        op4 = self.queue.dequeue()
        self.assertEqual(op4.priority, OperationPriority.LOW)
    
    def test_dequeue_priority_only(self):
        """Test dequeueing only high priority operations."""
        # Add low priority
        op1 = QueuedOperation(
            endpoint="/api/low",
            priority=OperationPriority.LOW
        )
        self.queue.enqueue(op1)
        
        # Add high priority
        op2 = QueuedOperation(
            endpoint="/api/high",
            priority=OperationPriority.HIGH
        )
        self.queue.enqueue(op2)
        
        # Dequeue only high priority
        dequeued = self.queue.dequeue(priority_only=True)
        self.assertEqual(dequeued.endpoint, "/api/high")
        
        # Low priority should remain
        self.assertEqual(self.queue.get_pending_count(), 1)
    
    # ========================================================================
    # SCHEDULED OPERATIONS TESTS
    # ========================================================================
    
    def test_scheduled_operations(self):
        """Test operations scheduled for future execution."""
        # Add operation scheduled for 1 hour in future
        future_time = datetime.utcnow() + timedelta(hours=1)
        op = QueuedOperation(
            endpoint="/api/scheduled",
            scheduled_at=future_time
        )
        self.queue.enqueue(op)
        
        # Should not be dequeued yet
        dequeued = self.queue.dequeue()
        self.assertIsNone(dequeued)
        
        # But should be in stats
        self.assertEqual(self.queue.get_pending_count(), 1)
    
    # ========================================================================
    # OPERATION DATA CLASS TESTS
    # ========================================================================
    
    def test_operation_to_dict(self):
        """Test operation serialization."""
        op = QueuedOperation(
            endpoint="/api/test",
            data={"key": "value"},
            metadata={"user": "test"}
        )
        
        data = op.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["endpoint"], "/api/test")
        self.assertIn("data", data)
        self.assertIn("metadata", data)
    
    def test_operation_from_dict(self):
        """Test operation deserialization."""
        op = QueuedOperation(
            endpoint="/api/test",
            data={"key": "value"}
        )
        
        data = op.to_dict()
        reconstructed = QueuedOperation.from_dict(data)
        
        self.assertEqual(reconstructed.endpoint, op.endpoint)
        self.assertEqual(reconstructed.data, op.data)
    
    # ========================================================================
    # CONTEXT MANAGER TESTS
    # ========================================================================
    
    def test_context_manager(self):
        """Test using OperationQueue as context manager."""
        with OperationQueue(db_path=self.temp_db.name) as queue:
            op = QueuedOperation(endpoint="/api/test")
            queue.enqueue(op)
            
            self.assertEqual(queue.get_pending_count(), 1)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
