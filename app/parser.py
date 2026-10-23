import re
import hashlib
import uuid
import pdfplumber

def compute_hash(heading: str, body: str) -> str:
    content = f"{heading.strip()}|{body.strip()}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def parse_pdf_to_nodes(pdf_path: str, version_id: int):
    heading_regex = re.compile(r'^(\d+(?:\.\d+)*)\s+(.*)')
    nodes = []
    stack = []
    
    with pdfplumber.open(pdf_path) as pdf:
        text_blocks = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_blocks.extend(text.split('\n'))

    current_node = None

    for line in text_blocks:
        line = line.strip()
        if not line:
            continue
            
        match = heading_regex.match(line)
        if match:
            if current_node:
                current_node['content_hash'] = compute_hash(current_node['heading'], current_node['body_text'])
                nodes.append(current_node)
                
            section_num, heading_title = match.groups()
            level = len(section_num.split('.'))
            node_id = f"node_{version_id}_{uuid.uuid4().hex[:8]}"
            
            while stack and stack[-1][0] >= level:
                stack.pop()
                
            parent_id = stack[-1][1]['id'] if stack else None
            
            current_node = {
                'id': node_id,
                'version_id': version_id,
                'parent_id': parent_id,
                'heading': f"{section_num} {heading_title}",
                'level': level,
                'body_text': '',
                'node_path': section_num,
                'content_hash': ''
            }
            stack.append((level, current_node))
        else:
            if current_node:
                current_node['body_text'] += line + ' '

    if current_node:
        current_node['content_hash'] = compute_hash(current_node['heading'], current_node['body_text'])
        nodes.append(current_node)

    return nodes
    