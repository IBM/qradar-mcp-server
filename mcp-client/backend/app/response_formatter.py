"""
Response Formatter Module

Model-independent formatting layer that ensures consistent output
regardless of which LLM is used. Handles:
- Auto-detection of data types
- Markdown table formatting
- Large result summarization
- Consistent output structure
"""

import json
from typing import Any, Union, List, Dict
from datetime import datetime


class ResponseFormatter:
    """Model-independent response formatting layer."""
    
    # Thresholds
    MAX_TABLE_ROWS = 20
    MAX_LIST_ITEMS = 15
    MAX_STRING_LENGTH = 5000
    SUMMARY_THRESHOLD = 10
    
    def __init__(self):
        pass
    
    def format(self, data: Any, hint: str = None) -> str:
        """
        Auto-detect and format any data.
        Works regardless of which model produced it.
        
        Args:
            data: Any data to format
            hint: Optional hint about data type (e.g., "users", "offenses", "version")
        
        Returns:
            Formatted markdown string
        """
        if data is None:
            return "_No data available_"
        
        # Already a string - check if it needs formatting
        if isinstance(data, str):
            return self._format_string(data)
        
        # Single value (number, bool)
        if isinstance(data, (int, float, bool)):
            return self._format_single_value(data, hint)
        
        # Dictionary (key-value pairs)
        if isinstance(data, dict):
            return self._format_dict(data, hint)
        
        # List of items
        if isinstance(data, list):
            return self._format_list(data, hint)
        
        # Fallback
        return str(data)
    
    def _format_string(self, data: str) -> str:
        """Format string data."""
        # Check if it's JSON
        if data.strip().startswith('{') or data.strip().startswith('['):
            try:
                parsed = json.loads(data)
                return self.format(parsed)
            except json.JSONDecodeError:
                pass
        
        # Truncate if too long
        if len(data) > self.MAX_STRING_LENGTH:
            return data[:self.MAX_STRING_LENGTH] + f"\n\n_... truncated ({len(data)} total characters)_"
        
        return data
    
    def _format_single_value(self, data: Union[int, float, bool], hint: str = None) -> str:
        """Format a single value."""
        if isinstance(data, bool):
            return "✅ Yes" if data else "❌ No"
        
        if isinstance(data, float):
            return f"**{data:,.2f}**"
        
        # Integer - check if it's a count
        if hint and any(word in hint.lower() for word in ['count', 'total', 'number']):
            return f"**{data:,}** {hint}"
        
        return f"**{data:,}**"
    
    def _format_dict(self, data: dict, hint: str = None) -> str:
        """Format dictionary as table or key-value pairs."""
        if not data:
            return "_Empty result_"
        
        # Check if it's a nested structure with lists
        has_nested_lists = any(isinstance(v, list) for v in data.values())
        
        if has_nested_lists:
            return self._format_nested_dict(data, hint)
        
        # Simple key-value table
        lines = ["| Property | Value |", "|----------|-------|"]
        
        for key, value in data.items():
            formatted_key = self._format_key(key)
            formatted_value = self._format_value(value)
            lines.append(f"| {formatted_key} | {formatted_value} |")
        
        return "\n".join(lines)
    
    def _format_nested_dict(self, data: dict, hint: str = None) -> str:
        """Format dictionary with nested structures."""
        parts = []
        
        for key, value in data.items():
            formatted_key = self._format_key(key)
            
            if isinstance(value, list):
                parts.append(f"### {formatted_key}")
                parts.append(self._format_list(value))
            elif isinstance(value, dict):
                parts.append(f"### {formatted_key}")
                parts.append(self._format_dict(value))
            else:
                parts.append(f"**{formatted_key}:** {self._format_value(value)}")
        
        return "\n\n".join(parts)
    
    def _format_list(self, data: list, hint: str = None) -> str:
        """Format list of items."""
        if not data:
            return "_No items found_"
        
        total_count = len(data)
        
        # Check if all items are simple values
        if all(isinstance(item, (str, int, float, bool)) for item in data):
            return self._format_simple_list(data, total_count)
        
        # Check if all items are dicts with same keys (table-able)
        if all(isinstance(item, dict) for item in data):
            return self._format_list_as_table(data, total_count, hint)
        
        # Mixed list
        return self._format_mixed_list(data, total_count)
    
    def _format_simple_list(self, data: list, total_count: int) -> str:
        """Format list of simple values."""
        display_data = data[:self.MAX_LIST_ITEMS]
        
        lines = []
        for item in display_data:
            lines.append(f"- {item}")
        
        result = "\n".join(lines)
        
        if total_count > self.MAX_LIST_ITEMS:
            result += f"\n\n_... and {total_count - self.MAX_LIST_ITEMS} more items (showing {self.MAX_LIST_ITEMS} of {total_count})_"
        
        return result
    
    def _format_list_as_table(self, data: list, total_count: int, hint: str = None) -> str:
        """Format list of dicts as markdown table."""
        if not data:
            return "_No items_"
        
        # Get columns from first item, prioritize important fields
        first_item = data[0]
        all_keys = list(first_item.keys())
        
        # Prioritize common important fields
        priority_fields = ['id', 'name', 'username', 'status', 'description', 'type', 
                          'severity', 'offense_type', 'start_time', 'created', 'updated']
        
        # Sort keys: priority first, then alphabetical
        columns = []
        for pf in priority_fields:
            if pf in all_keys:
                columns.append(pf)
        for key in all_keys:
            if key not in columns and len(columns) < 6:  # Max 6 columns
                columns.append(key)
        
        # Limit rows
        display_data = data[:self.MAX_TABLE_ROWS]
        
        # Build table header
        header = "| " + " | ".join(self._format_key(col) for col in columns) + " |"
        separator = "|" + "|".join("---" for _ in columns) + "|"
        
        # Build rows
        rows = []
        for item in display_data:
            row_values = []
            for col in columns:
                value = item.get(col, "")
                formatted = self._format_cell_value(value)
                row_values.append(formatted)
            rows.append("| " + " | ".join(row_values) + " |")
        
        result = "\n".join([header, separator] + rows)
        
        # Add summary if truncated
        if total_count > self.MAX_TABLE_ROWS:
            result = f"**Found {total_count:,} items** (showing first {self.MAX_TABLE_ROWS})\n\n" + result
            result += f"\n\n_... {total_count - self.MAX_TABLE_ROWS} more items not shown_"
        elif total_count > 1:
            result = f"**{total_count} items:**\n\n" + result
        
        return result
    
    def _format_mixed_list(self, data: list, total_count: int) -> str:
        """Format list with mixed types."""
        display_data = data[:self.MAX_LIST_ITEMS]
        
        parts = []
        for i, item in enumerate(display_data, 1):
            if isinstance(item, dict):
                parts.append(f"**Item {i}:**\n{self._format_dict(item)}")
            else:
                parts.append(f"- {item}")
        
        result = "\n\n".join(parts)
        
        if total_count > self.MAX_LIST_ITEMS:
            result += f"\n\n_... and {total_count - self.MAX_LIST_ITEMS} more items_"
        
        return result
    
    def _format_key(self, key: str) -> str:
        """Format a key/column name for display."""
        # Convert snake_case to Title Case
        return key.replace('_', ' ').title()
    
    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "-"
        if isinstance(value, bool):
            return "✅" if value else "❌"
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                return f"{value:,.2f}"
            return f"{value:,}"
        if isinstance(value, list):
            if len(value) == 0:
                return "-"
            if len(value) <= 3:
                return ", ".join(str(v) for v in value)
            return f"{len(value)} items"
        if isinstance(value, dict):
            return f"{len(value)} fields"
        return str(value)
    
    def _format_cell_value(self, value: Any, max_length: int = 50) -> str:
        """Format a value for table cell."""
        formatted = self._format_value(value)
        if len(formatted) > max_length:
            return formatted[:max_length-3] + "..."
        return formatted
    
    def format_tool_result(self, tool_name: str, result: Any) -> str:
        """Format a tool result with context."""
        # Detect result type based on tool name
        hint = None
        if 'user' in tool_name.lower():
            hint = 'users'
        elif 'offense' in tool_name.lower():
            hint = 'offenses'
        elif 'reference' in tool_name.lower():
            hint = 'reference_sets'
        
        return self.format(result, hint)
    
    def summarize_large_result(self, data: Any, max_items: int = 10) -> dict:
        """
        Create a summary for large results.
        
        Returns:
            dict with 'summary' (string) and 'data' (truncated)
        """
        if isinstance(data, list):
            total = len(data)
            truncated = data[:max_items]
            return {
                "summary": f"Found **{total:,}** items (showing first {min(max_items, total)})",
                "data": truncated,
                "total": total,
                "showing": len(truncated)
            }
        
        if isinstance(data, dict):
            return {
                "summary": f"Result with **{len(data)}** fields",
                "data": data,
                "total": len(data),
                "showing": len(data)
            }
        
        return {
            "summary": str(data)[:200],
            "data": data,
            "total": 1,
            "showing": 1
        }


# Global instance
formatter = ResponseFormatter()


def format_response(data: Any, hint: str = None) -> str:
    """Convenience function to format any response."""
    return formatter.format(data, hint)


def format_tool_result(tool_name: str, result: Any) -> str:
    """Convenience function to format tool results."""
    return formatter.format_tool_result(tool_name, result)
