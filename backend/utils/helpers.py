import re

def clean_text(text):
    # Replace non-breaking space with a regular space
    text = text.replace('\xa0', ' ')
    
    # Remove extra newlines (more than 2 newlines -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespaces on each line
    text = '\n'.join(line.strip() for line in text.splitlines())
    
    # Remove extra blank lines (lines that are just empty)
    text = re.sub(r'\n\s*\n', '\n\n', text)

    return text.strip()