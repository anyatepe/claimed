"""
Tests for the summarization and classification API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import app, SummarizeRequest, SummarizeResponse, ClassifyRequest, ClassifyResponse

client = TestClient(app)


class TestSummarizeEndpoint:
    """Tests for POST /v1/summarize endpoint."""

    def test_summarize_valid_request(self):
        """Test summarize endpoint with valid request."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "This is a test input text.",
                "style": "bullet"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert isinstance(data["summary"], str)
        assert data["summary"] == "This is a test input text."

    def test_summarize_with_all_optional_fields(self):
        """Test summarize endpoint with all optional fields."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "Test input",
                "retrieval": {"k": 10},
                "max_tokens": 200,
                "style": "abstract"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

    def test_summarize_missing_input(self):
        """Test summarize endpoint with missing required field."""
        response = client.post(
            "/v1/summarize",
            json={
                "style": "bullet"
            }
        )
        assert response.status_code == 422

    def test_summarize_empty_input(self):
        """Test summarize endpoint with empty input."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "",
                "style": "bullet"
            }
        )
        assert response.status_code == 422

    def test_summarize_invalid_style(self):
        """Test summarize endpoint with invalid style."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "Test input",
                "style": "invalid_style"
            }
        )
        assert response.status_code == 422

    def test_summarize_invalid_max_tokens(self):
        """Test summarize endpoint with invalid max_tokens."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "Test input",
                "max_tokens": -1
            }
        )
        assert response.status_code == 422

    def test_summarize_invalid_retrieval_k(self):
        """Test summarize endpoint with invalid retrieval k value."""
        response = client.post(
            "/v1/summarize",
            json={
                "input": "Test input",
                "retrieval": {"k": 0}
            }
        )
        assert response.status_code == 422

    def test_summarize_pydantic_model_validation(self):
        """Test Pydantic model validation for SummarizeRequest."""
        # Valid request
        valid_request = SummarizeRequest(
            input="Test input",
            style="bullet"
        )
        assert valid_request.input == "Test input"
        assert valid_request.style == "bullet"
        assert valid_request.retrieval is None
        assert valid_request.max_tokens is None

        # Invalid style
        with pytest.raises(ValidationError):
            SummarizeRequest(input="Test", style="invalid")

        # Empty input
        with pytest.raises(ValidationError):
            SummarizeRequest(input="", style="bullet")

        # Invalid max_tokens
        with pytest.raises(ValidationError):
            SummarizeRequest(input="Test", max_tokens=-1)


class TestClassifyEndpoint:
    """Tests for POST /v1/classify endpoint."""

    def test_classify_valid_request(self):
        """Test classify endpoint with valid request."""
        response = client.post(
            "/v1/classify",
            json={
                "input": "This is a positive review.",
                "labels": ["positive", "negative", "neutral"],
                "multi_label": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "confidence" in data
        assert isinstance(data["labels"], list)
        assert isinstance(data["confidence"], dict)
        assert len(data["labels"]) > 0
        assert len(data["confidence"]) == 3

    def test_classify_multi_label(self):
        """Test classify endpoint with multi_label enabled."""
        response = client.post(
            "/v1/classify",
            json={
                "input": "This is a test.",
                "labels": ["label1", "label2", "label3"],
                "multi_label": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "confidence" in data

    def test_classify_missing_input(self):
        """Test classify endpoint with missing required field."""
        response = client.post(
            "/v1/classify",
            json={
                "labels": ["positive", "negative"],
                "multi_label": False
            }
        )
        assert response.status_code == 422

    def test_classify_empty_labels(self):
        """Test classify endpoint with empty labels list."""
        response = client.post(
            "/v1/classify",
            json={
                "input": "Test input",
                "labels": [],
                "multi_label": False
            }
        )
        assert response.status_code == 422

    def test_classify_duplicate_labels(self):
        """Test classify endpoint with duplicate labels."""
        response = client.post(
            "/v1/classify",
            json={
                "input": "Test input",
                "labels": ["positive", "positive", "negative"],
                "multi_label": False
            }
        )
        assert response.status_code == 422

    def test_classify_pydantic_model_validation(self):
        """Test Pydantic model validation for ClassifyRequest."""
        # Valid request
        valid_request = ClassifyRequest(
            input="Test input",
            labels=["label1", "label2"],
            multi_label=False
        )
        assert valid_request.input == "Test input"
        assert valid_request.labels == ["label1", "label2"]
        assert valid_request.multi_label is False

        # Empty labels
        with pytest.raises(ValidationError):
            ClassifyRequest(input="Test", labels=[])

        # Duplicate labels
        with pytest.raises(ValidationError):
            ClassifyRequest(input="Test", labels=["label1", "label1"])

        # Empty input
        with pytest.raises(ValidationError):
            ClassifyRequest(input="", labels=["label1"])


class TestOpenAPISchema:
    """Tests for OpenAPI schema generation."""

    def test_openapi_schema_exists(self):
        """Test that OpenAPI schema is generated."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_summarize_endpoint_in_openapi(self):
        """Test that summarize endpoint is documented in OpenAPI."""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/v1/summarize" in schema["paths"]
        assert "post" in schema["paths"]["/v1/summarize"]
        
        post_schema = schema["paths"]["/v1/summarize"]["post"]
        assert "requestBody" in post_schema
        assert "responses" in post_schema
        
        # Check for schema reference in request body
        request_body = post_schema["requestBody"]
        assert "content" in request_body
        assert "application/json" in request_body["content"]
        content = request_body["content"]["application/json"]
        assert "schema" in content
        
        # Check that the schema component exists and has an example
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "SummarizeRequest" in schema["components"]["schemas"]
        assert "example" in schema["components"]["schemas"]["SummarizeRequest"]

    def test_classify_endpoint_in_openapi(self):
        """Test that classify endpoint is documented in OpenAPI."""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/v1/classify" in schema["paths"]
        assert "post" in schema["paths"]["/v1/classify"]
        
        post_schema = schema["paths"]["/v1/classify"]["post"]
        assert "requestBody" in post_schema
        assert "responses" in post_schema
        
        # Check for schema reference in request body
        request_body = post_schema["requestBody"]
        assert "content" in request_body
        assert "application/json" in request_body["content"]
        content = request_body["content"]["application/json"]
        assert "schema" in content
        
        # Check that the schema component exists and has an example
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "ClassifyRequest" in schema["components"]["schemas"]
        assert "example" in schema["components"]["schemas"]["ClassifyRequest"]

    def test_openapi_examples_present(self):
        """Test that examples are present in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check summarize endpoint example in schema components
        assert "components" in schema
        assert "schemas" in schema["components"]
        assert "SummarizeRequest" in schema["components"]["schemas"]
        summarize_schema = schema["components"]["schemas"]["SummarizeRequest"]
        assert "example" in summarize_schema
        example = summarize_schema["example"]
        assert "input" in example
        assert "style" in example
        
        # Check classify endpoint example in schema components
        assert "ClassifyRequest" in schema["components"]["schemas"]
        classify_schema = schema["components"]["schemas"]["ClassifyRequest"]
        assert "example" in classify_schema
        example = classify_schema["example"]
        assert "input" in example
        assert "labels" in example
        assert "multi_label" in example

    def test_openapi_response_schemas(self):
        """Test that response schemas are properly defined."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check summarize response schema
        summarize_responses = schema["paths"]["/v1/summarize"]["post"]["responses"]
        assert "200" in summarize_responses
        response_200 = summarize_responses["200"]
        assert "content" in response_200
        assert "application/json" in response_200["content"]
        response_schema_ref = response_200["content"]["application/json"]["schema"]
        # Schema may be a reference or inline
        if "$ref" in response_schema_ref:
            # Resolve reference
            ref_path = response_schema_ref["$ref"].split("/")[-1]
            response_schema = schema["components"]["schemas"][ref_path]
        else:
            response_schema = response_schema_ref
        assert "properties" in response_schema
        assert "summary" in response_schema["properties"]
        
        # Check classify response schema
        classify_responses = schema["paths"]["/v1/classify"]["post"]["responses"]
        assert "200" in classify_responses
        response_200 = classify_responses["200"]
        assert "content" in response_200
        assert "application/json" in response_200["content"]
        response_schema_ref = response_200["content"]["application/json"]["schema"]
        # Schema may be a reference or inline
        if "$ref" in response_schema_ref:
            # Resolve reference
            ref_path = response_schema_ref["$ref"].split("/")[-1]
            response_schema = schema["components"]["schemas"][ref_path]
        else:
            response_schema = response_schema_ref
        assert "properties" in response_schema
        assert "labels" in response_schema["properties"]
        assert "confidence" in response_schema["properties"]


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "healthy"}
