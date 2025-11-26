def format_username(username: str) -> str:
    base = username.split('_')[0]  # Remove domain/extra
    parts = base.split('.')        # Split by '.'
    formatted_parts = [p.capitalize() for p in parts if p]  # Capitalize
    return " ".join(formatted_parts)

def build_weekly_attendance_table(data: list[tuple[str, int]]) -> str:
    table = """
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; border: 1px solid #ddd;">Name</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Office Days</th>
            </tr>
        </thead>
        <tbody>
    """

    for username, days in data:
        name = format_username(username)
        table += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{name}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{days}</td>
            </tr>
        """

    table += "</tbody></table>"
    return table