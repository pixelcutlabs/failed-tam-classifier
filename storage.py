"""
Storage abstraction layer for the Website Review Tool
Supports both local file storage and cloud storage for Vercel deployment
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

class StorageBackend:
    """Abstract base class for storage backends"""
    
    def load_state(self) -> Dict[str, Any]:
        """Load shared state from storage"""
        raise NotImplementedError
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save shared state to storage"""
        raise NotImplementedError
    
    def export_csv(self, data: list, filename: str) -> Optional[str]:
        """Export data to CSV and return file path/URL"""
        raise NotImplementedError

class LocalFileStorage(StorageBackend):
    """Local file storage implementation"""
    
    def __init__(self, state_file: str = 'shared_state.json'):
        self.state_file = state_file
    
    def load_state(self) -> Dict[str, Any]:
        """Load state from local JSON file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as file:
                    return json.load(file)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save state to local JSON file"""
        try:
            with open(self.state_file, 'w') as file:
                json.dump(state, file, indent=2)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def export_csv(self, data: list, filename: str) -> Optional[str]:
        """Export data to local CSV file"""
        if not data:
            return None
        
        import csv
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return filename
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return None

class MemoryStorage(StorageBackend):
    """In-memory storage for development/testing"""
    
    def __init__(self):
        self._state = {}
    
    def load_state(self) -> Dict[str, Any]:
        """Load state from memory"""
        return self._state.copy()
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save state to memory"""
        self._state.update(state)
        return True
    
    def export_csv(self, data: list, filename: str) -> Optional[str]:
        """Export data to temporary CSV file"""
        if not data:
            return None
        
        import csv
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            writer = csv.DictWriter(temp_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return None

class CloudStorage(StorageBackend):
    """
    Cloud storage implementation (placeholder for services like AWS S3, Google Cloud Storage, etc.)
    
    For Vercel deployment, you can implement this with:
    - AWS S3 for file storage
    - Redis/Upstash for state management
    - PostgreSQL/PlanetScale for persistent data
    - KV stores like Vercel KV
    """
    
    def __init__(self, storage_url: str):
        self.storage_url = storage_url
        # Initialize your cloud storage client here
        print(f"Cloud storage initialized with URL: {storage_url}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load state from cloud storage"""
        # Implement cloud storage retrieval
        # For now, return empty state for demo purposes
        print("Loading state from cloud storage...")
        return {}
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save state to cloud storage"""
        # Implement cloud storage saving
        print(f"Saving state to cloud storage: {len(str(state))} characters")
        return True
    
    def export_csv(self, data: list, filename: str) -> Optional[str]:
        """Export data to cloud storage and return public URL"""
        if not data:
            return None
        
        # Implement cloud CSV export
        print(f"Exporting {len(data)} records to cloud storage as {filename}")
        return f"https://example-bucket.s3.amazonaws.com/{filename}"

def get_storage_backend() -> StorageBackend:
    """
    Factory function to get the appropriate storage backend based on environment
    """
    # Check for cloud storage configuration
    storage_url = os.environ.get('STORAGE_URL')
    if storage_url:
        return CloudStorage(storage_url)
    
    # Check if we're in a serverless environment (like Vercel)
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        # Use memory storage for serverless (you'd want to implement proper cloud storage)
        print("Running in serverless environment, using memory storage")
        return MemoryStorage()
    
    # Default to local file storage for development
    return LocalFileStorage()