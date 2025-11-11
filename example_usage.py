"""Example usage of the job API."""
import requests
import time
import json

API_BASE_URL = "http://localhost:8000"


def create_upsert_job():
    """Example: Create an upsert job."""
    response = requests.post(
        f"{API_BASE_URL}/v1/jobs",
        json={
            "type": "upsert",
            "payload": {
                "document_id": "example_doc_1",
                "content": "This is example document content for testing.",
                "metadata": {
                    "source": "api",
                    "tags": ["example", "test"],
                },
            },
            "webhook_url": "https://webhook.site/your-unique-url",  # Optional
        },
    )
    
    if response.status_code == 201:
        job = response.json()
        print(f"Created job: {job['id']}")
        print(f"Status: {job['status']}")
        return job["id"]
    else:
        print(f"Error creating job: {response.text}")
        return None


def create_chat_job():
    """Example: Create a chat job."""
    response = requests.post(
        f"{API_BASE_URL}/v1/jobs",
        json={
            "type": "chat",
            "payload": {
                "query": "Explain the concept of machine learning in simple terms",
                "max_hops": 3,
                "temperature": 0.7,
            },
        },
    )
    
    if response.status_code == 201:
        job = response.json()
        print(f"Created chat job: {job['id']}")
        return job["id"]
    else:
        print(f"Error creating job: {response.text}")
        return None


def check_job_status(job_id: str):
    """Example: Check job status."""
    response = requests.get(f"{API_BASE_URL}/v1/jobs/{job_id}")
    
    if response.status_code == 200:
        job = response.json()
        print(f"\nJob {job_id}:")
        print(f"  Type: {job['type']}")
        print(f"  Status: {job['status']}")
        print(f"  Created: {job['created_at']}")
        if job.get("started_at"):
            print(f"  Started: {job['started_at']}")
        if job.get("completed_at"):
            print(f"  Completed: {job['completed_at']}")
        if job.get("result_url"):
            print(f"  Result URL: {job['result_url']}")
        if job.get("error"):
            print(f"  Error: {job['error']}")
        return job
    else:
        print(f"Error getting job status: {response.text}")
        return None


def get_job_result(job_id: str):
    """Example: Get job result."""
    response = requests.get(f"{API_BASE_URL}/v1/jobs/{job_id}/result")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nJob Result:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"Error getting result: {response.text}")
        return None


if __name__ == "__main__":
    print("=== Example: Upsert Job ===")
    job_id = create_upsert_job()
    
    if job_id:
        print("\nWaiting for job to complete...")
        for i in range(10):  # Check up to 10 times
            time.sleep(1)
            job = check_job_status(job_id)
            if job and job["status"] in ["success", "failure"]:
                if job["status"] == "success" and job.get("result_url"):
                    get_job_result(job_id)
                break
    
    print("\n=== Example: Chat Job ===")
    chat_job_id = create_chat_job()
    
    if chat_job_id:
        print("\nWaiting for job to complete...")
        for i in range(10):  # Check up to 10 times
            time.sleep(1)
            job = check_job_status(chat_job_id)
            if job and job["status"] in ["success", "failure"]:
                if job["status"] == "success" and job.get("result_url"):
                    get_job_result(chat_job_id)
                break
