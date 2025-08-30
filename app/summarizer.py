from transformers import pipeline

# Load once and reuse
#summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

"""
def summarize_comments(comments: list[str]) -> str:
    text = " ".join(comments)
    if len(text) > 1024:
        text = text[:1024]  # BART input length limit
    summary = summarizer(text, max_length=100, min_length=25, do_sample=False)
    return summary[0]['summary_text']
"""

def summarize_comments(comments: list[str]) -> str:
    return "Temporary text"