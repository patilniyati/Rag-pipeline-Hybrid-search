import re
import unicodedata

def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)   # fix odd unicode characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)   # zero-width characters
    text = re.sub(r"[●○■▪•]", "-", text)                      # bullet glyphs -> plain dash
    text = text.replace("\u00a0", " ")           # non-breaking space -> normal space
    text = text.replace("\r\n", "\n")            # Windows line endings
    text = re.sub(r"[ \t]+", " ", text)          # collapse repeated spaces
    text = re.sub(r"\n{3,}", "\n\n", text)       # max one blank line
    return text.strip()

