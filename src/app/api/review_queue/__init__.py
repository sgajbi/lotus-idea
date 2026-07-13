"""HTTP request mapping for role-specific review queues."""

from app.api.review_queue.requests import ReviewQueueRequest, review_queue_request_from_http

__all__ = ["ReviewQueueRequest", "review_queue_request_from_http"]
