"""
Integration tests for job lifecycle.
"""
import pytest
import requests
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class WebhookHandler(BaseHTTPRequestHandler):
    """Simple HTTP server to receive webhook callbacks."""
    received_callbacks = []
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        WebhookHandler.received_callbacks.append(data)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'received'}).encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass


@pytest.fixture
def webhook_server():
    """Start a webhook server for testing."""
    server = HTTPServer(('localhost', 8765), WebhookHandler)
    WebhookHandler.received_callbacks.clear()
    
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    
    yield server
    
    server.shutdown()
    server.server_close()


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return 'http://localhost:5000'


class TestJobLifecycle:
    """Test job lifecycle operations."""
    
    def test_create_summarize_job(self, api_base_url):
        """Test creating a summarize job."""
        response = requests.post(
            f'{api_base_url}/v1/jobs',
            json={
                'type': 'summarize',
                'text': 'This is a long text that needs to be summarized. ' * 10
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert 'id' in data
        assert data['status'] == 'processing'
        assert 'created_at' in data
        
        return data['id']
    
    def test_create_classify_job(self, api_base_url):
        """Test creating a classify job."""
        response = requests.post(
            f'{api_base_url}/v1/jobs',
            json={
                'type': 'classify',
                'text': 'This is about programming and software development.'
            }
        )
        
        assert response.status_code == 202
        data = response.json()
        assert 'id' in data
        assert data['status'] == 'processing'
        assert 'created_at' in data
        
        return data['id']
    
    def test_get_job_status(self, api_base_url):
        """Test getting job status."""
        # Create a job
        job_id = self.test_create_summarize_job(api_base_url)
        
        # Wait a bit for processing
        time.sleep(2)
        
        # Get job status
        response = requests.get(f'{api_base_url}/v1/jobs/{job_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == job_id
        assert data['status'] in ['processing', 'completed', 'failed']
        assert 'created_at' in data
    
    def test_job_completion_with_result(self, api_base_url):
        """Test that job completes and returns result."""
        # Create a job
        job_id = self.test_create_summarize_job(api_base_url)
        
        # Wait for completion (with timeout)
        max_wait = 30
        wait_interval = 1
        elapsed = 0
        
        while elapsed < max_wait:
            response = requests.get(f'{api_base_url}/v1/jobs/{job_id}')
            assert response.status_code == 200
            data = response.json()
            
            if data['status'] == 'completed':
                assert 'result' in data
                assert 'summary' in data['result']
                assert 'completed_at' in data
                return
            
            if data['status'] == 'failed':
                pytest.fail(f"Job failed: {data.get('error', 'Unknown error')}")
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        pytest.fail("Job did not complete within timeout period")
    
    def test_classify_job_result(self, api_base_url):
        """Test classify job returns correct result format."""
        # Create a classify job
        job_id = self.test_create_classify_job(api_base_url)
        
        # Wait for completion
        max_wait = 30
        wait_interval = 1
        elapsed = 0
        
        while elapsed < max_wait:
            response = requests.get(f'{api_base_url}/v1/jobs/{job_id}')
            assert response.status_code == 200
            data = response.json()
            
            if data['status'] == 'completed':
                assert 'result' in data
                assert 'category' in data['result']
                assert 'confidence' in data['result']
                return
            
            if data['status'] == 'failed':
                pytest.fail(f"Job failed: {data.get('error', 'Unknown error')}")
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        pytest.fail("Job did not complete within timeout period")
    
    def test_webhook_callback(self, api_base_url, webhook_server):
        """Test webhook callback on job completion."""
        webhook_url = 'http://localhost:8765/webhook'
        
        # Create a job with webhook
        response = requests.post(
            f'{api_base_url}/v1/jobs',
            json={
                'type': 'summarize',
                'text': 'Test text for webhook',
                'webhook_url': webhook_url
            }
        )
        
        assert response.status_code == 202
        job_id = response.json()['id']
        
        # Wait for completion and webhook
        max_wait = 30
        wait_interval = 1
        elapsed = 0
        
        while elapsed < max_wait:
            if WebhookHandler.received_callbacks:
                callback = WebhookHandler.received_callbacks[0]
                assert callback['job_id'] == job_id
                assert callback['status'] == 'completed'
                assert 'result' in callback
                return
            
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        pytest.fail("Webhook callback not received within timeout period")
    
    def test_invalid_job_type(self, api_base_url):
        """Test creating job with invalid type."""
        response = requests.post(
            f'{api_base_url}/v1/jobs',
            json={
                'type': 'invalid',
                'text': 'Some text'
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_missing_text(self, api_base_url):
        """Test creating job without text."""
        response = requests.post(
            f'{api_base_url}/v1/jobs',
            json={
                'type': 'summarize'
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_nonexistent_job(self, api_base_url):
        """Test getting nonexistent job."""
        response = requests.get(f'{api_base_url}/v1/jobs/nonexistent-id')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_health_endpoint(self, api_base_url):
        """Test health check endpoint."""
        response = requests.get(f'{api_base_url}/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
