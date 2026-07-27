from pathlib import Path
from api.services.supabase_client import supabase

from pathlib import Path

from api.services.supabase_client import supabase


def upload_file(
    bucket: str,
    destination_path: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    """
    Sube un archivo a Supabase Storage y devuelve la ruta donde se ha guardado.
    """
    print(f"Bucket: {bucket}")
    print(f"Ruta: {destination_path}")
    
    supabase.storage.from_(bucket).upload(
        path=destination_path,
        file=file_bytes,
        file_options={
            "content-type": content_type,
            "upsert": "True",
        },
    )

    return destination_path
  