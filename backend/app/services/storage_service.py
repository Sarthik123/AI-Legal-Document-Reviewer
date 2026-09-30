import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4


STORAGE_DIR = Path("storage/documents")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_document(filename: str, file_data: bytes) -> tuple[str, str]:
    document_id = str(uuid4())
    safe_filename = Path(filename).name
    stored_filename = f"{document_id}_{safe_filename}"

    if r2_enabled():
        key = f"documents/{stored_filename}"
        _r2_client().put_object(
            Bucket=os.environ["R2_BUCKET_NAME"],
            Key=key,
            Body=file_data,
            ContentType="application/pdf",
        )
        return document_id, f"r2://{os.environ['R2_BUCKET_NAME']}/{key}"

    file_path = STORAGE_DIR / stored_filename
    file_path.write_bytes(file_data)
    return document_id, str(file_path)


def _r2_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.getenv("R2_REGION", "auto"),
    )


def r2_enabled() -> bool:
    return all(os.getenv(name, "").strip() for name in (
        "R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME",
    ))


def read_document(storage_path: str) -> BytesIO | Path:
    if storage_path.startswith("r2://"):
        _, bucket, key = storage_path.split("/", 2)
        response = _r2_client().get_object(Bucket=bucket, Key=key)
        return BytesIO(response["Body"].read())
    return Path(storage_path)


def delete_document(storage_path: str) -> None:
    if storage_path.startswith("r2://"):
        _, bucket, key = storage_path.split("/", 2)
        _r2_client().delete_object(Bucket=bucket, Key=key)
        return
    path = Path(storage_path)
    if path.exists():
        path.unlink()
