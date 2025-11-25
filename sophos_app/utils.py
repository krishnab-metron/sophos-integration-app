def format_username(username: str) -> str:
    """
    Convert usernames like 'krishna.balsara_metronlabs'
    to 'Krishna Balsara'.
    """
    base = username.split('_')[0]  # Remove domain/extra
    parts = base.split('.')        # Split by '.'
    formatted_parts = [p.capitalize() for p in parts if p]  # Capitalize
    return " ".join(formatted_parts)