# Move this file to az-func-audio/utils/file_types.py

SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.webm', '.flac', '.ogg', '.opus', '.aac', '.mp4'}
SUPPORTED_TEXT_EXTENSIONS = {'.txt', '.srt', '.vtt', '.json', '.md', '.rtf', '.csv'}
SUPPORTED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.rtf'}
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}

FILE_TYPE_MAP = {}
for ext in SUPPORTED_AUDIO_EXTENSIONS:
    FILE_TYPE_MAP[ext] = 'audio'
for ext in SUPPORTED_TEXT_EXTENSIONS:
    FILE_TYPE_MAP[ext] = 'text'
for ext in SUPPORTED_DOCUMENT_EXTENSIONS:
    FILE_TYPE_MAP[ext] = 'document'
for ext in SUPPORTED_IMAGE_EXTENSIONS:
    FILE_TYPE_MAP[ext] = 'image'

def get_file_type(file_extension: str) -> str:
    return FILE_TYPE_MAP.get(file_extension.lower(), 'unsupported')

def get_supported_extensions() -> set:
    return set(FILE_TYPE_MAP.keys())
