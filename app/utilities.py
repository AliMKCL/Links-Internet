import re
import html
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

def enhance_post_content_for_html(content):
    """Format post content for better HTML display, especially Reddit tables"""
    if not content:
        return ""
        
    # Escape HTML tags for safety
    content = html.escape(content)
    
    # Process markdown headers (##, ###, etc.)
    content = re.sub(r'^(#{1,6})\s+(.+?)$', 
                     lambda m: f'<h{len(m.group(1))} style="color:#185a9d;margin-top:15px;margin-bottom:10px;">{m.group(2)}</h{len(m.group(1))}>', 
                     content, flags=re.MULTILINE)
    
    # Process bold text (**text**)
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    
    # Process italics (*text*)
    content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)
    
    # Process code blocks (```code```)
    content = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', content, flags=re.DOTALL)
    
    # Process inline code (`code`)
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
    
    # Process markdown lists
    content = re.sub(r'^(\s*)\*\s+(.+?)$', r'\1<li>\2</li>', content, flags=re.MULTILINE)
    content = re.sub(r'(<li>.*?</li>\n)+', r'<ul>\n\g<0></ul>', content, flags=re.DOTALL)
    
    # Convert markdown tables to HTML tables
    # First identify each table by looking for lines starting with |
    def extract_tables(text):
        result = []
        lines = text.split('\n')
        in_table = False
        current_table = []
        
        for line in lines:
            # If line starts with | and contains at least one more |, it's likely part of a table
            if line.strip().startswith('|') and line.strip().count('|') > 1:
                if not in_table:
                    in_table = True
                current_table.append(line)
            elif in_table:
                # If we were in a table but this line is not a table line
                in_table = False
                if current_table:
                    result.append(('\n'.join(current_table), current_table))
                    current_table = []
            
        # Don't forget the last table if there is one
        if current_table:
            result.append(('\n'.join(current_table), current_table))
            
        return result
    
    tables = extract_tables(content)
    
    # Process each table
    for table_text, table_lines in tables:
        # Skip tables with fewer than 2 rows (need at least header and separator)
        if len(table_lines) < 2:
            continue
            
        # Check if second row contains the separator (----)
        separator_row = table_lines[1]
        if not re.match(r'^\s*\|([\s\-:|]+\|)+\s*$', separator_row):
            continue
            
        header_row = table_lines[0]
        data_rows = table_lines[2:]
        
        # Extract header cells
        header_cells = []
        for cell in header_row.split('|')[1:-1]:
            header_cells.append(cell.strip())
        
        # Extract alignment information from separator row
        alignments = []
        for sep in separator_row.split('|')[1:-1]:
            sep = sep.strip()
            if sep.startswith(':') and sep.endswith(':'):
                alignments.append('center')
            elif sep.endswith(':'):
                alignments.append('right')
            else:
                alignments.append('left')
        
        # Ensure we have alignment for each column
        while len(alignments) < len(header_cells):
            alignments.append('left')
        
        html_table = '<div class="table-responsive"><table class="table">'
        
        # Add header row
        html_table += '<thead><tr>'
        for i, cell in enumerate(header_cells):
            align = alignments[i] if i < len(alignments) else 'left'
            html_table += f'<th style="text-align:{align}">{cell}</th>'
        html_table += '</tr></thead><tbody>'
        
        # Add data rows
        for row in data_rows:
            cells = row.split('|')[1:-1]
            if len(cells) > 0:  # Make sure there are cells
                html_table += '<tr>'
                for i, cell in enumerate(cells):
                    # Ensure we don't go out of bounds
                    align = 'left'
                    if i < len(alignments):
                        align = alignments[i]
                    
                    # Handle potential mismatch in cell count
                    if i < len(cells):
                        html_table += f'<td style="text-align:{align}">{cell.strip()}</td>'
                    else:
                        html_table += f'<td style="text-align:{align}"></td>'
                html_table += '</tr>'
        
        html_table += '</tbody></table></div>'
        
        # Replace the original table text with the HTML table
        content = content.replace(table_text, html_table)
    
    # Process links [text](url)
    content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', content)
    
    # Process blockquotes
    content = re.sub(r'^>\s+(.*?)$', r'<blockquote>\1</blockquote>', content, flags=re.MULTILINE)
    
    # Convert line breaks to <br> tags, but not within HTML elements we've created
    paragraphs = content.split('\n\n')
    for i in range(len(paragraphs)):
        # Skip paragraphs that are already HTML (tables, headers, etc.)
        if not (paragraphs[i].startswith('<table') or 
                paragraphs[i].startswith('<h') or 
                paragraphs[i].startswith('<pre') or
                paragraphs[i].startswith('<ul') or
                paragraphs[i].startswith('<blockquote')):
            paragraphs[i] = paragraphs[i].replace('\n', '<br>')
    
    content = ''.join([f'<div style="margin-bottom:10px;">{p}</div>' 
                      if not (p.startswith('<table') or 
                              p.startswith('<h') or 
                              p.startswith('<pre') or
                              p.startswith('<ul') or
                              p.startswith('<blockquote'))
                      else p for p in paragraphs])
    
    return content

# Good response but no botw (abbreviations) as subreddits.
def query_classification(query: str) ->int:  
    """
    Classifies the query as a question or statement using a pre-trained model.
    """
    
    tokenizer = AutoTokenizer.from_pretrained("shahrukhx01/question-vs-statement-classifier")
    model = AutoModelForSequenceClassification.from_pretrained("shahrukhx01/question-vs-statement-classifier")

    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

    result = classifier(query)

    # For the first instance/output get the first label and the confidence in it.
    label = result[0]['label']
    score = result[0]['score']

    if label == "LABEL_1" and score > 0.7:
        print("Query classified as a question.")
        return 1  # Question
    else:
        print("Query classified as a statement.")
        return 0  # Statement

# Good maybe not exactly ideal response but catches botw (abbreviations) as subreddits
def query_classificationNEW(query: str) -> int:    
    """
    Classifies the query as a question or statehment using a transformer model.
    Returns 1 for question, 0 for statement.
    """
    try:
        # Load a pre-trained model for sequence classification
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased")
        
        # Create a text classification pipeline
        pipe = pipeline("text-classification", model=model, tokenizer=tokenizer)
        
        # Classify the query
        result = pipe(query)[0]
        
        # In this case, we're just checking if it's a question or not
        # Assuming label "LABEL_1" is for questions and "LABEL_0" is for statements
        if result["label"] == "LABEL_1":
            print(f"Query classified as a question with confidence {result['score']:.4f}")
            return 1
        else:
            print(f"Query classified as a statement with confidence {result['score']:.4f}")
            return 0
    except Exception as e:
        print(f"Error in ML-based query classification: {e}")
        # Fallback to rule-based approach
        question_words = ["what", "who", "when", "where", "why", "how", "which", "can", "could", "would", "should", "is", "are", "do", "does"]
        
        # Clean the query
        query_lower = query.lower().strip()
        
        # Check if it ends with a question mark
        if query_lower.endswith("?"):
            print("Query classified as a question (ends with ?).")
            return 1
        
        # Check if it starts with a question word
        for word in question_words:
            if query_lower.startswith(word + " "):
                print(f"Query classified as a question (starts with '{word}').")
                return 1
        
        print("Query classified as a statement.")
        return 0

 