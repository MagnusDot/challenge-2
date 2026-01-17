def estimate_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4
    except Exception:
        return len(text) // 4