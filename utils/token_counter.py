"""Token counting utilities"""
import tiktoken

# Token counter
try:
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
except:
    encoding = None

def count_tokens(text: str) -> int:
    """Count tokens in text"""
    if encoding:
        return len(encoding.encode(text))
    return len(text.split()) * 1.3  # Rough estimate if tiktoken fails