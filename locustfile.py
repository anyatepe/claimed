"""
Locust load test script for summarization API endpoint.
Simulates 500 concurrent users making requests to /v1/summarize
"""

from locust import HttpUser, task, between
import random
import string


class SummarizationUser(HttpUser):
    """Simulates a user making summarization requests."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts."""
        pass
    
    def generate_random_text(self, min_words=50, max_words=500):
        """Generate random text for summarization."""
        # Sample sentences for more realistic text
        sample_sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is transforming how we process and understand data.",
            "Natural language processing enables computers to understand human language.",
            "Artificial intelligence has become increasingly important in modern technology.",
            "Data science combines statistics, programming, and domain expertise.",
            "Cloud computing provides scalable infrastructure for applications.",
            "Distributed systems allow for better performance and reliability.",
            "API design is crucial for building maintainable software systems.",
            "Performance optimization requires careful analysis and measurement.",
            "Load testing helps identify bottlenecks and capacity limits.",
            "Microservices architecture enables better scalability and maintainability.",
            "Containerization simplifies deployment and environment management.",
            "Continuous integration and deployment improve development workflows.",
            "Monitoring and observability are essential for production systems.",
            "Security best practices protect applications from vulnerabilities.",
        ]
        
        # Generate random number of words
        num_words = random.randint(min_words, max_words)
        words = []
        
        # Build text from sample sentences
        while len(words) < num_words:
            sentence = random.choice(sample_sentences)
            words.extend(sentence.split())
        
        # Trim to exact word count
        words = words[:num_words]
        text = " ".join(words)
        
        return text
    
    @task(1)
    def summarize_text(self):
        """Make a POST request to the summarization endpoint."""
        # Generate random text input
        text = self.generate_random_text()
        
        # Prepare request payload
        payload = {
            "text": text
        }
        
        # Make POST request with custom name for better metrics tracking
        with self.client.post(
            "/v1/summarize",
            json=payload,
            catch_response=True,
            name="summarize"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            elif response.status_code >= 500:
                response.failure(f"Server error: {response.status_code}")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
