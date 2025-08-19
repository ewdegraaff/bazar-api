"""
Messaging service for SQS operations with support for multiple message types.
"""
import json
import logging
import os
from typing import Dict, Any, Literal
from enum import Enum
import uuid
from datetime import datetime

import boto3

logger = logging.getLogger(__name__)

# AWS SQS configuration
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", None)  # For localstack
TASK_QUEUE_NAME = os.environ.get("TASK_QUEUE_NAME", "task-queue")


class MessageType(str, Enum):
    """Supported message types for the messaging service."""
    SIMPLE_REQUEST = "simple_request"
    BATCH_REQUEST = "batch_request"
    PRIORITY_REQUEST = "priority_request"
    # Future message types can be added here:
    # IMAGE_REQUEST = "image_request"  
    # AUDIO_REQUEST = "audio_request"
    # ADMIN_MESSAGE = "admin_message"


class MessagingService:
    """
    Service for SQS operations with support for multiple message types.
    
    This service provides a centralized way to send different types of messages
    to appropriate queues with proper formatting and validation.
    """
    
    def __init__(self):
        # Initialize SQS client
        self.sqs = boto3.client(
            "sqs", 
            region_name=AWS_REGION,
            endpoint_url=AWS_ENDPOINT_URL
        )
        
        # Cache for queue URLs
        self._queue_urls = {}
        
        logger.info(f"Initialized MessagingService with region {AWS_REGION}" + 
                   (f" and endpoint {AWS_ENDPOINT_URL}" if AWS_ENDPOINT_URL else ""))
    
    async def initialize(self):
        """Initialize queue URLs for all supported queues."""
        # Get task queue URL
        self._queue_urls[TASK_QUEUE_NAME] = await self.get_queue_url(TASK_QUEUE_NAME)
        
        # Future: Initialize additional queues here
        # self._queue_urls["priority-queue"] = await self.get_queue_url("priority-queue")
        # self._queue_urls["admin-queue"] = await self.get_queue_url("admin-queue")
    
    async def get_queue_url(self, queue_name: str) -> str:
        """
        Get the URL for an SQS queue with caching.
        
        Args:
            queue_name: Name of the queue
            
        Returns:
            Queue URL
        """
        if queue_name in self._queue_urls:
            return self._queue_urls[queue_name]
        
        response = self.sqs.get_queue_url(QueueName=queue_name)
        queue_url = response["QueueUrl"]
        self._queue_urls[queue_name] = queue_url
        
        logger.info(f"Got URL for queue {queue_name}: {queue_url}")
        return queue_url
    
    def _create_base_message(self, message_type: MessageType, conversation_id: str, payload: Dict[str, Any], thread_id: str = None) -> Dict[str, Any]:
        """
        Create a base message structure with common fields using new worker format.
        
        Args:
            message_type: Type of message being sent
            conversation_id: ID of the conversation (user's conversation with AI)
            payload: Message-specific payload
            thread_id: Optional thread ID within the conversation
            
        Returns:
            Base message structure compatible with worker's new format
        """
        message = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        
        # Add thread_id only if provided
        if thread_id:
            message["thread_id"] = thread_id
            
        return message
    
    async def send_simple_request(self, user_id: str, payload: Dict[str, Any], thread_id: str = None) -> str:
        """
        Send a simple AI request message to the task queue using new worker format.
        
        Args:
            user_id: ID of the user making the request (used as conversation_id)
            payload: Request payload (should contain 'input' field)
            thread_id: Optional thread ID within the conversation
            
        Returns:
            Message ID for tracking
        """
        # Use user_id as conversation_id for now (simple 1:1 mapping)
        conversation_id = user_id
        
        message = self._create_base_message(MessageType.SIMPLE_REQUEST, conversation_id, payload, thread_id)
        queue_url = await self.get_queue_url(TASK_QUEUE_NAME)
        
        # Send message to task queue
        self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        logger.info(f"Sent simple request message {message['id']} to task queue for conversation {conversation_id}")
        return message["id"]
    
    # Future message type methods can be added here:
    
    async def send_batch_request(self, user_id: str, requests: list[Dict[str, Any]], thread_id: str = None) -> str:
        """
        Send a batch request message (placeholder for future implementation).
        
        Args:
            user_id: ID of the user making the request (used as conversation_id)
            requests: List of individual requests to process as a batch
            thread_id: Optional thread ID within the conversation
            
        Returns:
            Message ID for tracking
        """
        # Use user_id as conversation_id for now (simple 1:1 mapping)
        conversation_id = user_id
        
        payload = {
            "requests": requests,
            "batch_size": len(requests)
        }
        message = self._create_base_message(MessageType.BATCH_REQUEST, conversation_id, payload, thread_id)
        
        # For now, send to same queue (future: could route to different queue)
        queue_url = await self.get_queue_url(TASK_QUEUE_NAME)
        
        self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        logger.info(f"Sent batch request message {message['id']} with {len(requests)} requests for conversation {conversation_id}")
        return message["id"]
    
    async def send_priority_request(self, user_id: str, payload: Dict[str, Any], priority_level: int = 1, thread_id: str = None) -> str:
        """
        Send a priority request message (placeholder for future implementation).
        
        Args:
            user_id: ID of the user making the request (used as conversation_id)
            payload: Request payload
            priority_level: Priority level (1 = highest, 5 = lowest)
            thread_id: Optional thread ID within the conversation
            
        Returns:
            Message ID for tracking
        """
        # Use user_id as conversation_id for now (simple 1:1 mapping)
        conversation_id = user_id
        
        enhanced_payload = {
            **payload,
            "priority_level": priority_level
        }
        message = self._create_base_message(MessageType.PRIORITY_REQUEST, conversation_id, enhanced_payload, thread_id)
        
        # Future: Route to priority queue based on priority level
        # if priority_level <= 2:
        #     queue_url = await self.get_queue_url("priority-queue")
        # else:
        #     queue_url = await self.get_queue_url(TASK_QUEUE_NAME)
        
        queue_url = await self.get_queue_url(TASK_QUEUE_NAME)
        
        self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            # Future: Add message attributes for priority routing
            # MessageAttributes={
            #     'Priority': {
            #         'StringValue': str(priority_level),
            #         'DataType': 'Number'
            #     }
            # }
        )
        
        logger.info(f"Sent priority request message {message['id']} (priority {priority_level}) for conversation {conversation_id}")
        return message["id"]
    
    # Legacy method for backward compatibility
    async def send_simple_message(self, message: Dict[str, Any]) -> None:
        """
        Legacy method for backward compatibility.
        
        Args:
            message: Complete message to send
        """
        queue_url = await self.get_queue_url(TASK_QUEUE_NAME)
        
        self.sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        logger.info(f"Sent legacy message to task queue: {message.get('id', 'unknown')}")


# Singleton instance
messaging_service = MessagingService()
