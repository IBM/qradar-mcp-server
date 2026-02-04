"""
Session Memory Module

Short-term memory system for maintaining context across conversation turns.
Handles:
- Last N exchanges
- Tracking fetched data
- Avoiding duplicate tool calls
- Context-aware responses
"""

import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict


@dataclass
class ToolCallRecord:
    """Record of a tool call."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    timestamp: float
    success: bool
    
    def is_expired(self, ttl_seconds: int = 300) -> bool:
        """Check if this record is older than TTL."""
        return time.time() - self.timestamp > ttl_seconds


@dataclass
class Exchange:
    """A single user-assistant exchange."""
    user_message: str
    assistant_response: str
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class SessionMemory:
    """
    Session memory for maintaining conversation context.
    
    Features:
    - Stores last N exchanges
    - Caches tool call results
    - Detects duplicate queries
    - Provides context summaries
    """
    
    def __init__(
        self,
        max_exchanges: int = 5,
        tool_cache_ttl: int = 300,  # 5 minutes
        max_cache_size: int = 50
    ):
        self.max_exchanges = max_exchanges
        self.tool_cache_ttl = tool_cache_ttl
        self.max_cache_size = max_cache_size
        
        self.exchanges: List[Exchange] = []
        self.tool_cache: OrderedDict[str, ToolCallRecord] = OrderedDict()
        self.session_start = time.time()
        self.metadata: Dict[str, Any] = {}
    
    def add_exchange(
        self,
        user_message: str,
        assistant_response: str,
        tool_calls: List[Dict] = None
    ):
        """Add a new exchange to memory."""
        tool_records = []
        if tool_calls:
            for tc in tool_calls:
                record = ToolCallRecord(
                    tool_name=tc.get("name", ""),
                    arguments=tc.get("args", {}),
                    result=tc.get("result"),
                    timestamp=time.time(),
                    success=tc.get("status") == "success"
                )
                tool_records.append(record)
                # Also add to cache
                self._cache_tool_call(record)
        
        exchange = Exchange(
            user_message=user_message,
            assistant_response=assistant_response,
            tool_calls=tool_records
        )
        
        self.exchanges.append(exchange)
        
        # Trim to max size
        while len(self.exchanges) > self.max_exchanges:
            self.exchanges.pop(0)
    
    def _cache_tool_call(self, record: ToolCallRecord):
        """Cache a tool call result."""
        # Create cache key from tool name and arguments
        cache_key = self._make_cache_key(record.tool_name, record.arguments)
        
        self.tool_cache[cache_key] = record
        
        # Trim cache if needed
        while len(self.tool_cache) > self.max_cache_size:
            self.tool_cache.popitem(last=False)
    
    def _make_cache_key(self, tool_name: str, arguments: Dict) -> str:
        """Create a cache key for a tool call."""
        # Remove credentials from cache key
        safe_args = {k: v for k, v in arguments.items() 
                    if k not in ['qradar_token', 'qradar_host', 'token', 'api_key']}
        return f"{tool_name}:{json.dumps(safe_args, sort_keys=True)}"
    
    def get_cached_result(self, tool_name: str, arguments: Dict) -> Optional[Any]:
        """
        Get cached result for a tool call if available and not expired.
        
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._make_cache_key(tool_name, arguments)
        
        if cache_key in self.tool_cache:
            record = self.tool_cache[cache_key]
            if not record.is_expired(self.tool_cache_ttl) and record.success:
                return record.result
            else:
                # Remove expired entry
                del self.tool_cache[cache_key]
        
        return None
    
    def is_duplicate_query(self, message: str, threshold: float = 0.9) -> Optional[str]:
        """
        Check if this message is similar to a recent one.
        
        Returns:
            Previous response if duplicate, None otherwise
        """
        message_lower = message.lower().strip()
        
        for exchange in reversed(self.exchanges):
            prev_message = exchange.user_message.lower().strip()
            
            # Simple exact match (could be enhanced with fuzzy matching)
            if message_lower == prev_message:
                return exchange.assistant_response
            
            # Check for very similar messages
            if self._similarity(message_lower, prev_message) >= threshold:
                return exchange.assistant_response
        
        return None
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Simple word-based similarity score."""
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def get_context_summary(self) -> str:
        """
        Get a summary of recent context for the LLM.
        
        Returns:
            Summary string to prepend to conversation
        """
        if not self.exchanges:
            return ""
        
        lines = ["Previous context:"]
        
        for i, exchange in enumerate(self.exchanges[-3:], 1):  # Last 3 exchanges
            user_short = exchange.user_message[:100]
            if len(exchange.user_message) > 100:
                user_short += "..."
            
            assistant_short = exchange.assistant_response[:150]
            if len(exchange.assistant_response) > 150:
                assistant_short += "..."
            
            lines.append(f"- User asked: {user_short}")
            lines.append(f"  Assistant: {assistant_short}")
        
        return "\n".join(lines)
    
    def get_fetched_data_summary(self) -> Dict[str, Any]:
        """
        Get summary of data fetched in this session.
        
        Returns:
            Dict with tool names and what was fetched
        """
        summary = {}
        
        for record in self.tool_cache.values():
            if record.success and not record.is_expired(self.tool_cache_ttl):
                tool_name = record.tool_name
                if tool_name not in summary:
                    summary[tool_name] = []
                
                # Extract endpoint from arguments
                endpoint = record.arguments.get("endpoint", "unknown")
                summary[tool_name].append(endpoint)
        
        return summary
    
    def clear(self):
        """Clear all memory."""
        self.exchanges.clear()
        self.tool_cache.clear()
        self.session_start = time.time()
        self.metadata.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "exchanges_stored": len(self.exchanges),
            "max_exchanges": self.max_exchanges,
            "cached_tool_calls": len(self.tool_cache),
            "session_duration_seconds": int(time.time() - self.session_start),
            "metadata": self.metadata
        }


# Session storage (in production, use Redis or database)
_sessions: Dict[str, SessionMemory] = {}


def get_session(session_id: str) -> SessionMemory:
    """Get or create a session."""
    if session_id not in _sessions:
        _sessions[session_id] = SessionMemory()
    return _sessions[session_id]


def clear_session(session_id: str):
    """Clear a session's memory."""
    if session_id in _sessions:
        _sessions[session_id].clear()


def clear_all_sessions():
    """Clear all sessions."""
    _sessions.clear()
