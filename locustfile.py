"""
Locust load test for document upload and query API.

Target: Sustain 200 RPS with p95 < 1.8s (streaming disabled)
"""

import os
import random
import time
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import json


# Random questions to ask about the PDF
QUESTIONS = [
    "What is the main topic of this document?",
    "Can you summarize the key points?",
    "What are the main conclusions?",
    "What methodology is described?",
    "What are the key findings?",
    "What data sources are mentioned?",
    "What recommendations are provided?",
    "What is the purpose of this document?",
    "What are the main sections?",
    "What are the limitations discussed?",
    "What future work is mentioned?",
    "What are the main arguments?",
    "What evidence is presented?",
    "What are the implications?",
    "What is the context of this document?",
]


class DocumentUser(FastHttpUser):
    """
    Locust user class for testing document upload and query endpoints.
    Uses FastHttpUser for better performance at high RPS.
    """
    
    wait_time = between(0.1, 0.5)  # Wait between 0.1-0.5 seconds between tasks
    
    def on_start(self):
        """Called when a user starts. Upload a document once per user."""
        self.document_id = None
        self.pdf_path = os.path.join(os.path.dirname(__file__), "test_document.pdf")
        
        # Upload document once per user
        if os.path.exists(self.pdf_path):
            self.upload_document()
    
    def upload_document(self):
        """Upload a PDF document via /v1/documents endpoint."""
        with open(self.pdf_path, 'rb') as pdf_file:
            files = {'file': ('test_document.pdf', pdf_file, 'application/pdf')}
            
            with self.client.post(
                "/v1/documents",
                files=files,
                catch_response=True,
                name="upload_document"
            ) as response:
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        data = response.json()
                        # Extract document ID from response
                        # Common patterns: {"id": "...", "document_id": "...", "data": {"id": "..."}}
                        if isinstance(data, dict):
                            self.document_id = (
                                data.get("id") or 
                                data.get("document_id") or 
                                data.get("data", {}).get("id") or
                                data.get("data", {}).get("document_id")
                            )
                        response.success()
                    except (json.JSONDecodeError, AttributeError):
                        # If response is not JSON or doesn't have expected structure,
                        # assume success if status is 200/201
                        response.success()
                elif response.status_code == 0:
                    response.failure("Connection error")
                else:
                    response.failure(f"Upload failed with status {response.status_code}")
    
    @task(3)  # Weight: 3 queries per upload
    def query_document(self):
        """Query the uploaded document via /v1/chat/query endpoint."""
        if not self.document_id:
            # If no document_id, try to upload first
            self.upload_document()
            if not self.document_id:
                return
        
        # Select a random question
        question = random.choice(QUESTIONS)
        
        # Prepare query payload (common API patterns)
        payload = {
            "question": question,
            "document_id": self.document_id,
            "stream": False  # Explicitly disable streaming
        }
        
        # Alternative payload structures (uncomment if needed)
        # payload = {
        #     "query": question,
        #     "document_id": self.document_id,
        #     "streaming": False
        # }
        # payload = {
        #     "message": question,
        #     "doc_id": self.document_id,
        #     "stream": False
        # }
        
        headers = {"Content-Type": "application/json"}
        
        with self.client.post(
            "/v1/chat/query",
            json=payload,
            headers=headers,
            catch_response=True,
            name="query_document"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validate response structure
                    if isinstance(data, dict):
                        response.success()
                    else:
                        response.success()  # Accept any 200 response
                except json.JSONDecodeError:
                    # Non-JSON response might still be valid
                    response.success()
            elif response.status_code == 0:
                response.failure("Connection error")
            else:
                response.failure(f"Query failed with status {response.status_code}: {response.text[:200]}")
    
    @task(1)  # Weight: 1 upload per 3 queries
    def upload_and_query(self):
        """Upload a new document and immediately query it."""
        self.upload_document()
        if self.document_id:
            time.sleep(0.1)  # Small delay to allow document processing
            self.query_document()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("=" * 80)
    print("Starting load test")
    print(f"Target: 200 RPS, p95 < 1.8s")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("=" * 80)
    print("Test completed")
    print("=" * 80)
