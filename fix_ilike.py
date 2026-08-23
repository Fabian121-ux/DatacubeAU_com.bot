import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add import for escape_like if not there
    if 'escape_like' not in content:
        content = content.replace('from app.utils.text import normalize_text', 'from app.utils.text import escape_like, normalize_text')
        # If it doesn't have normalize_text import, add it after from sqlalchemy
        if 'escape_like' not in content:
            content = content.replace('from app.utils.time import utcnow', 'from app.utils.text import escape_like\nfrom app.utils.time import utcnow')

    # Replace like = f"%{q}%" -> like = f"%{escape_like(q)}%"
    content = re.sub(r'like = f"%\{([a-zA-Z0-9_]+)\}%"', r'like = f"%{escape_like(\1)}%"', content)
    # norm_like = f"%{normalize_text(q)}%" -> norm_like = f"%{normalize_text(escape_like(q))}%"
    content = re.sub(r'norm_like = f"%\{normalize_text\(([a-zA-Z0-9_]+)\)\}%"', r'norm_like = f"%{normalize_text(escape_like(\1))}%"', content)
    
    # display_like = f"%{display_name_like}%" -> display_like = f"%{escape_like(display_name_like)}%"
    content = re.sub(r'display_like = f"%\{([a-zA-Z0-9_]+)\}%"', r'display_like = f"%{escape_like(\1)}%"', content)

    # .ilike(like) -> .ilike(like, escape="\\")
    content = re.sub(r'\.ilike\((like|display_like|norm_like)\)', r'.ilike(\1, escape="\\\\")', content)
    
    # f"%{query}%" -> f"%{escape_like(query)}%"
    content = re.sub(r'\.ilike\(f"%\{([a-zA-Z0-9_]+)\}%"\)', r'.ilike(f"%{escape_like(\1)}%", escape="\\\\")', content)

    # f"%{clean.lstrip('@')}%" -> f"%{escape_like(clean.lstrip('@'))}%"
    content = content.replace(
        '.ilike(f"%{clean.lstrip(\'@\')}%")',
        '.ilike(f"%{escape_like(clean.lstrip(\'@\'))}%", escape="\\\\")'
    )
    
    with open(filepath, 'w') as f:
        f.write(content)

process_file("bot_core/app/api/admin.py")
process_file("bot_core/app/services/memory_service.py")
process_file("bot_core/app/services/owner_command_service.py")
