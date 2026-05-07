import hashlib

STOPWORDS = {"a","an","the","is","it","i","you","me","my","and","or","to","of","in","that"}

def simhash(text: str) -> str:
    tokens = sorted(set(text.lower().split()) - STOPWORDS)
    return hashlib.md5(" ".join(tokens).encode()).hexdigest()[:16]