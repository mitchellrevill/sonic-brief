import re
from typing import Tuple, Optional

def strip_vtt_tags(line: str) -> str:
    """Remove VTT formatting tags from a line."""
    return re.sub(r'<[^>]+>', '', line)

def extract_vtt_speaker(line: str, current_speaker: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Extract speaker name from a VTT line, if present."""
    if '<v ' in line and '>' in line:
        start_tag = line.find('<v ')
        end_tag = line.find('>', start_tag)
        if end_tag != -1:
            speaker = line[start_tag + 3:end_tag].strip()
            clean_line = line[end_tag + 1:].strip()
            return speaker, clean_line
    return None, line
