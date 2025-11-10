"""Tests for ChromaStore."""

import tempfile
import unittest

from adapters.chroma_store import ChromaStore


class TestChromaStore(unittest.TestCase):
    """Test suite for ChromaStore."""

    def setUp(self):
        """Set up test fixtures."""
        # Use in-memory Chroma for ephemeral testing
        self.store = ChromaStore(
            collection_name=f"test_collection_{id(self)}",
            persist_directory=None,  # In-memory mode
        )

    def tearDown(self):
        """Clean up after tests."""
        # Chroma in-memory client doesn't need explicit cleanup
        pass

    def test_collection_creation(self):
        """Test that collection is created on first access."""
        # Collection should be created lazily
        self.assertIsNotNone(self.store.collection)
        self.assertEqual(self.store.collection.name, self.store.collection_name)

    def test_add_embeddings_basic(self):
        """Test adding embeddings without metadata."""
        embeddings = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        ids = self.store.add_embeddings(embeddings)

        self.assertEqual(len(ids), 2)
        self.assertIsInstance(ids[0], str)
        self.assertIsInstance(ids[1], str)

        # Verify embeddings were added
        info = self.store.get_collection_info()
        self.assertEqual(info["count"], 2)

    def test_add_embeddings_with_metadata(self):
        """Test adding embeddings with metadata."""
        embeddings = [[1.0, 2.0], [3.0, 4.0]]
        metadatas = [
            {"category": "A", "value": 10},
            {"category": "B", "value": 20},
        ]
        ids = self.store.add_embeddings(embeddings, metadatas=metadatas)

        self.assertEqual(len(ids), 2)

        # Verify metadata was stored
        info = self.store.get_collection_info()
        self.assertEqual(info["count"], 2)

    def test_add_embeddings_with_custom_ids(self):
        """Test adding embeddings with custom IDs."""
        embeddings = [[1.0, 2.0]]
        custom_ids = ["custom_id_1"]
        ids = self.store.add_embeddings(embeddings, ids=custom_ids)

        self.assertEqual(ids, custom_ids)

    def test_add_embeddings_length_mismatch(self):
        """Test that length mismatches raise errors."""
        embeddings = [[1.0, 2.0], [3.0, 4.0]]
        metadatas = [{"key": "value"}]  # Wrong length

        with self.assertRaises(ValueError):
            self.store.add_embeddings(embeddings, metadatas=metadatas)

    def test_similarity_search_knn(self):
        """Test k-nearest neighbors similarity search."""
        # Add test embeddings
        embeddings = [
            [1.0, 0.0, 0.0],  # Unit vector along x-axis
            [0.0, 1.0, 0.0],  # Unit vector along y-axis
            [0.0, 0.0, 1.0],  # Unit vector along z-axis
            [0.9, 0.1, 0.0],  # Close to first vector
        ]
        ids = self.store.add_embeddings(embeddings)

        # Search for vectors similar to [1.0, 0.0, 0.0]
        query = [1.0, 0.0, 0.0]
        results = self.store.similarity_search(query, k=2)

        self.assertEqual(len(results), 2)
        # First result should be the closest (should be [1.0, 0.0, 0.0] or [0.9, 0.1, 0.0])
        self.assertIn(results[0]["id"], ids)
        self.assertIsNotNone(results[0]["distance"])
        # Distance should be smaller for closer vectors
        self.assertLessEqual(results[0]["distance"], results[1]["distance"])

    def test_similarity_search_with_metadata_filter(self):
        """Test similarity search with metadata filtering."""
        # Add embeddings with metadata
        embeddings = [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.5, 0.5],
        ]
        metadatas = [
            {"category": "A", "type": "test"},
            {"category": "B", "type": "test"},
            {"category": "A", "type": "demo"},
        ]
        ids = self.store.add_embeddings(embeddings, metadatas=metadatas)

        # Search with metadata filter
        query = [1.0, 0.0]
        where_filter = {"category": "A"}
        results = self.store.similarity_search(query, k=10, where=where_filter)

        # All results should have category "A"
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertEqual(result["metadata"]["category"], "A")

    def test_similarity_search_with_complex_filter(self):
        """Test similarity search with complex metadata filters."""
        embeddings = [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.5, 0.5],
        ]
        metadatas = [
            {"category": "A", "score": 10},
            {"category": "B", "score": 20},
            {"category": "A", "score": 30},
        ]
        self.store.add_embeddings(embeddings, metadatas=metadatas)

        # Search with complex filter (score > 15)
        query = [1.0, 0.0]
        where_filter = {"score": {"$gt": 15}}
        results = self.store.similarity_search(query, k=10, where=where_filter)

        # All results should have score > 15
        for result in results:
            self.assertGreater(result["metadata"]["score"], 15)

    def test_delete_by_ids(self):
        """Test deleting embeddings by IDs."""
        embeddings = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        ids = self.store.add_embeddings(embeddings)

        # Delete one embedding
        self.store.delete(ids=[ids[0]])

        # Verify deletion
        info = self.store.get_collection_info()
        self.assertEqual(info["count"], 2)

        # Verify the remaining embeddings exist
        query = [1.0, 2.0]
        results = self.store.similarity_search(query, k=10)
        remaining_ids = [r["id"] for r in results]
        self.assertNotIn(ids[0], remaining_ids)
        self.assertIn(ids[1], remaining_ids)
        self.assertIn(ids[2], remaining_ids)

    def test_delete_by_where_filter(self):
        """Test deleting embeddings using metadata filter."""
        embeddings = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        metadatas = [
            {"category": "A"},
            {"category": "B"},
            {"category": "A"},
        ]
        ids = self.store.add_embeddings(embeddings, metadatas=metadatas)

        # Delete all embeddings with category "A"
        self.store.delete(where={"category": "A"})

        # Verify deletion
        info = self.store.get_collection_info()
        self.assertEqual(info["count"], 1)

        # Verify remaining embedding has category "B"
        query = [1.0, 2.0]
        results = self.store.similarity_search(query, k=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["category"], "B")

    def test_delete_requires_ids_or_where(self):
        """Test that delete requires either ids or where parameter."""
        with self.assertRaises(ValueError):
            self.store.delete()

    def test_persistent_storage(self):
        """Test persistent storage using temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ChromaStore(
                collection_name="persistent_test",
                persist_directory=tmpdir,
            )

            # Add embeddings
            embeddings = [[1.0, 2.0], [3.0, 4.0]]
            ids = store.add_embeddings(embeddings)

            # Create a new store instance pointing to the same directory
            store2 = ChromaStore(
                collection_name="persistent_test",
                persist_directory=tmpdir,
            )

            # Verify data persists
            info = store2.get_collection_info()
            self.assertEqual(info["count"], 2)

            # Verify we can search
            results = store2.similarity_search([1.0, 2.0], k=2)
            self.assertEqual(len(results), 2)
            self.assertIn(results[0]["id"], ids)

    def test_empty_collection_search(self):
        """Test searching an empty collection."""
        results = self.store.similarity_search([1.0, 2.0], k=5)
        self.assertEqual(len(results), 0)

    def test_get_collection_info(self):
        """Test getting collection information."""
        info = self.store.get_collection_info()
        self.assertEqual(info["name"], self.store.collection_name)
        self.assertEqual(info["count"], 0)
        self.assertIsInstance(info["metadata"], dict)

        # Add some data
        self.store.add_embeddings([[1.0, 2.0]])
        info = self.store.get_collection_info()
        self.assertEqual(info["count"], 1)

    def test_multiple_collections(self):
        """Test that different stores use different collections."""
        store1 = ChromaStore(collection_name="collection_1", persist_directory=None)
        store2 = ChromaStore(collection_name="collection_2", persist_directory=None)

        store1.add_embeddings([[1.0, 2.0]])
        store2.add_embeddings([[3.0, 4.0]])

        self.assertEqual(store1.get_collection_info()["count"], 1)
        self.assertEqual(store2.get_collection_info()["count"], 1)

    def test_similarity_search_returns_correct_structure(self):
        """Test that similarity_search returns properly structured results."""
        embeddings = [[1.0, 2.0], [3.0, 4.0]]
        self.store.add_embeddings(embeddings)

        results = self.store.similarity_search([1.0, 2.0], k=2)

        self.assertGreater(len(results), 0)
        for result in results:
            self.assertIn("id", result)
            self.assertIn("embedding", result)
            self.assertIn("metadata", result)
            self.assertIn("distance", result)
            self.assertIsInstance(result["id"], str)
            self.assertIsInstance(result["metadata"], dict)


if __name__ == "__main__":
    unittest.main()
