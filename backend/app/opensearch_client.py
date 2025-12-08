"""OpenSearch client for vector storage and search."""
from opensearchpy import OpenSearch, RequestsHttpConnection
from typing import List, Dict, Optional, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Client for OpenSearch operations."""
    
    def __init__(self):
        """Initialize OpenSearch client."""
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish connection to OpenSearch."""
        try:
            http_auth = None
            if settings.opensearch_user and settings.opensearch_password:
                http_auth = (settings.opensearch_user, settings.opensearch_password)
            
            self.client = OpenSearch(
                hosts=[{
                    'host': settings.opensearch_host,
                    'port': settings.opensearch_port
                }],
                http_auth=http_auth,
                use_ssl=settings.opensearch_use_ssl,
                verify_certs=settings.opensearch_verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
            # Test connection
            if self.client.ping():
                logger.info("Successfully connected to OpenSearch")
            else:
                raise Exception("Failed to ping OpenSearch")
                
        except Exception as e:
            logger.error(f"Error connecting to OpenSearch: {str(e)}")
            raise
    
    def create_index(self, index_name: Optional[str] = None, dimension: Optional[int] = None):
        """
        Create OpenSearch index with k-NN vector field.
        
        Args:
            index_name: Name of the index (uses config default if None)
            dimension: Embedding dimension (uses config default if None)
        """
        index = index_name or settings.index_name
        dim = dimension or settings.embedding_dimension
        
        if self.index_exists(index):
            logger.info(f"Index {index} already exists")
            return
        
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
                    },
                    "image_path": {
                        "type": "keyword"
                    },
                    "short_description": {
                        "type": "text"
                    },
                    "full_description": {
                        "type": "text"
                    }
                }
            }
        }
        
        try:
            self.client.indices.create(index=index, body=index_body)
            logger.info(f"Created index: {index}")
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise
    
    def index_exists(self, index_name: Optional[str] = None) -> bool:
        """
        Check if index exists.
        
        Args:
            index_name: Name of the index (uses config default if None)
            
        Returns:
            True if index exists, False otherwise
        """
        index = index_name or settings.index_name
        try:
            return self.client.indices.exists(index=index)
        except Exception as e:
            logger.error(f"Error checking index existence: {str(e)}")
            return False
    
    def index_document(
        self,
        embedding: List[float],
        image_path: str,
        short_description: str,
        full_description: str,
        doc_id: Optional[str] = None,
        index_name: Optional[str] = None
    ) -> str:
        """
        Index a document with embedding.
        
        Args:
            embedding: Embedding vector
            image_path: Path to the image file
            short_description: Short description
            full_description: Full description
            doc_id: Optional document ID
            index_name: Name of the index (uses config default if None)
            
        Returns:
            Document ID
        """
        index = index_name or settings.index_name
        
        document = {
            "embedding": embedding,
            "image_path": image_path,
            "short_description": short_description,
            "full_description": full_description
        }
        
        try:
            response = self.client.index(
                index=index,
                body=document,
                id=doc_id,
                refresh=True
            )
            doc_id = response['_id']
            logger.debug(f"Indexed document: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            raise
    
    def search_similar(
        self,
        embedding: List[float],
        k: Optional[int] = None,
        index_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using k-NN.
        
        Args:
            embedding: Query embedding vector
            k: Number of results to return (uses config default if None)
            index_name: Name of the index (uses config default if None)
            
        Returns:
            List of retrieved documents with scores
        """
        index = index_name or settings.index_name
        k_value = k or settings.k_retrieval_count
        
        query = {
            "size": k_value,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": k_value
                    }
                }
            },
            "_source": {
                "includes": ["image_path", "short_description", "full_description"]
            }
        }
        
        try:
            response = self.client.search(index=index, body=query)
            results = []
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append({
                    "image_path": source.get("image_path", ""),
                    "short_description": source.get("short_description", ""),
                    "full_description": source.get("full_description", ""),
                    "score": hit['_score']
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching OpenSearch: {str(e)}")
            raise
    
    def get_document_count(self, index_name: Optional[str] = None) -> int:
        """
        Get total number of documents in the index.
        
        Args:
            index_name: Name of the index (uses config default if None)
            
        Returns:
            Document count
        """
        index = index_name or settings.index_name
        try:
            response = self.client.count(index=index)
            return response['count']
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0
    
    def delete_index(self, index_name: Optional[str] = None):
        """
        Delete an index.
        
        Args:
            index_name: Name of the index (uses config default if None)
        """
        index = index_name or settings.index_name
        try:
            if self.index_exists(index):
                self.client.indices.delete(index=index)
                logger.info(f"Deleted index: {index}")
        except Exception as e:
            logger.error(f"Error deleting index: {str(e)}")
            raise


# Global OpenSearch client instance
_opensearch_client: OpenSearchClient = None


def get_opensearch_client() -> OpenSearchClient:
    """
    Get or create the global OpenSearch client instance.
    
    Returns:
        OpenSearchClient instance
    """
    global _opensearch_client
    if _opensearch_client is None:
        _opensearch_client = OpenSearchClient()
    return _opensearch_client

