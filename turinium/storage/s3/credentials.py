from dataclasses import dataclass
from typing import Optional
from turinium.storage.base_credentials import BaseStorageCredentials


@dataclass
class S3Credentials(BaseStorageCredentials):
    """
    AWS S3 credentials and config.

    Attributes:
        bucket_name (str): Name of the target S3 bucket.
        region (Optional[str]): AWS region.
        access_key_id (Optional[str]): AWS access key (can also use IAM role).
        secret_access_key (Optional[str]): AWS secret key.
        session_token (Optional[str]): Optional temporary session token (STS).
    """
    bucket_name: str
    region: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
