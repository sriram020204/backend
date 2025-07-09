import os
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError
from dotenv import load_dotenv

load_dotenv()

class BlobUploader:
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_BLOB_CONTAINER", "tender-documents")
        
        if not self.connection_string:
            raise ValueError("Azure Storage connection string not found in environment variables")
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            # Ensure container exists
            self._ensure_container_exists()
        except Exception as e:
            print(f"Failed to initialize Azure Blob Storage: {e}")
            raise

    def _ensure_container_exists(self):
        """Ensure the container exists, create if it doesn't"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
        except Exception:
            # Container doesn't exist, create it
            try:
                self.blob_service_client.create_container(self.container_name)
                print(f"Created container: {self.container_name}")
            except Exception as e:
                print(f"Failed to create container: {e}")

    def upload_file(self, file_content: bytes, blob_name: str, content_type: str = None) -> str:
        """
        Upload file content to Azure Blob Storage
        
        Args:
            file_content: The file content as bytes
            blob_name: Name for the blob in storage
            content_type: MIME type of the file
            
        Returns:
            str: URL of the uploaded blob
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Upload the file
            blob_client.upload_blob(
                file_content, 
                overwrite=True,
                content_settings={'content_type': content_type} if content_type else None
            )
            
            # Return the blob URL
            return blob_client.url
            
        except AzureError as e:
            print(f"Azure error uploading {blob_name}: {e}")
            raise
        except Exception as e:
            print(f"Error uploading {blob_name}: {e}")
            raise

    def upload_file_from_path(self, file_path: str, blob_name: str = None) -> str:
        """
        Upload a file from local path to Azure Blob Storage
        
        Args:
            file_path: Local path to the file
            blob_name: Name for the blob (uses filename if not provided)
            
        Returns:
            str: URL of the uploaded blob
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not blob_name:
            blob_name = os.path.basename(file_path)
        
        # Determine content type based on file extension
        content_type = self._get_content_type(file_path)
        
        try:
            with open(file_path, 'rb') as file_data:
                return self.upload_file(file_data.read(), blob_name, content_type)
        except Exception as e:
            print(f"Error uploading file from path {file_path}: {e}")
            raise

    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except Exception as e:
            print(f"Error deleting blob {blob_name}: {e}")
            return False

    def list_blobs(self, prefix: str = None) -> list:
        """
        List all blobs in the container
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            list: List of blob names
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"Error listing blobs: {e}")
            return []

    def get_blob_url(self, blob_name: str) -> str:
        """
        Get the URL of a blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            str: URL of the blob
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, 
            blob=blob_name
        )
        return blob_client.url

    def _get_content_type(self, file_path: str) -> str:
        """
        Determine content type based on file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MIME type
        """
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.zip': 'application/zip',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        return content_types.get(extension, 'application/octet-stream')

# Convenience function for easy import
def get_blob_uploader():
    """Get a configured BlobUploader instance"""
    return BlobUploader()