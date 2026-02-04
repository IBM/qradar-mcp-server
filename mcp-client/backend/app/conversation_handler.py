"""
Conversation Handler Module

Handles conversation flow including:
- Ambiguous input detection
- Clarification requests
- Context-aware responses
- Turn handling
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ClarificationRequest:
    """A request for clarification from the user."""
    reason: str
    suggestions: List[str]
    original_message: str


class ConversationHandler:
    """
    Handles conversation flow and clarification logic.
    
    Features:
    - Detects ambiguous input
    - Generates clarification requests
    - Manages conversation context
    """
    
    # Patterns that indicate ambiguous requests
    AMBIGUOUS_PATTERNS = [
        r'^(it|this|that|they|them|those|these)[\s\?]*$',  # Pronouns only
        r'^(show|get|list|display|find)[\s]*$',  # Action without target
        r'^(yes|no|ok|okay|sure|maybe)[\s]*$',  # Confirmations without context
    ]
    
    # Keywords that need more context
    NEEDS_CONTEXT_KEYWORDS = {
        'more': 'What would you like to see more of?',
        'another': 'Another what specifically?',
        'same': 'Same as what?',
        'again': 'What would you like me to do again?',
        'different': 'Different how?',
    }
    
    # Domain-specific clarifications
    DOMAIN_CLARIFICATIONS = {
        'users': {
            'keywords': ['user', 'users', 'account', 'accounts'],
            'options': ['List all users', 'Show user details by ID', 'Find users by name', 'Show user permissions']
        },
        'offenses': {
            'keywords': ['offense', 'offenses', 'incident', 'incidents', 'alert', 'alerts'],
            'options': ['List recent offenses', 'Show offense by ID', 'Filter by severity', 'Show offense count']
        },
        'reference_sets': {
            'keywords': ['reference', 'set', 'sets', 'reference set', 'reference sets'],
            'options': ['List all reference sets', 'Show reference set entries', 'Search reference sets']
        },
        'system': {
            'keywords': ['system', 'version', 'health', 'status', 'info'],
            'options': ['Show system version', 'Check system health', 'Show deployment info']
        }
    }
    
    def __init__(self, max_clarifications: int = 1):
        self.max_clarifications = max_clarifications
        self.clarification_count = 0
        self.last_clarification_topic = None
    
    def analyze_input(self, message: str, context: Dict = None) -> Tuple[bool, Optional[ClarificationRequest]]:
        """
        Analyze user input and determine if clarification is needed.
        
        Args:
            message: User's message
            context: Previous conversation context
            
        Returns:
            Tuple of (needs_clarification: bool, clarification_request: Optional)
        """
        message_lower = message.lower().strip()
        
        # Don't ask for clarification too many times
        if self.clarification_count >= self.max_clarifications:
            self.clarification_count = 0
            return False, None
        
        # Check for empty or very short messages
        if len(message_lower) < 3:
            self.clarification_count += 1
            return True, ClarificationRequest(
                reason="Your message is too short to understand.",
                suggestions=["Please provide more details about what you'd like to do."],
                original_message=message
            )
        
        # Check ambiguous patterns
        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.match(pattern, message_lower):
                self.clarification_count += 1
                return True, ClarificationRequest(
                    reason="I need more context to understand your request.",
                    suggestions=["Please specify what you'd like me to do."],
                    original_message=message
                )
        
        # Check needs-context keywords
        words = message_lower.split()
        if len(words) <= 2:
            for word in words:
                if word in self.NEEDS_CONTEXT_KEYWORDS:
                    self.clarification_count += 1
                    return True, ClarificationRequest(
                        reason=self.NEEDS_CONTEXT_KEYWORDS[word],
                        suggestions=[],
                        original_message=message
                    )
        
        # If we got here, no clarification needed
        self.clarification_count = 0
        return False, None
    
    def get_domain_suggestions(self, message: str) -> List[str]:
        """Get domain-specific suggestions based on message content."""
        message_lower = message.lower()
        suggestions = []
        
        for domain, info in self.DOMAIN_CLARIFICATIONS.items():
            for keyword in info['keywords']:
                if keyword in message_lower:
                    suggestions.extend(info['options'])
                    break
        
        return suggestions[:4]  # Max 4 suggestions
    
    def format_clarification(self, request: ClarificationRequest) -> str:
        """Format a clarification request as a user-friendly message."""
        parts = [f"🤔 **Clarification needed**\n\n{request.reason}"]
        
        # Add suggestions if available
        domain_suggestions = self.get_domain_suggestions(request.original_message)
        all_suggestions = request.suggestions + domain_suggestions
        
        if all_suggestions:
            parts.append("\n**Did you mean:**")
            for i, suggestion in enumerate(all_suggestions[:5], 1):
                parts.append(f"- {suggestion}")
        
        return "\n".join(parts)
    
    def is_confirmation(self, message: str) -> bool:
        """Check if message is a confirmation response."""
        confirmations = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'proceed', 'do it', 'go ahead']
        message_lower = message.lower().strip()
        return message_lower in confirmations or any(c in message_lower for c in confirmations)
    
    def is_cancellation(self, message: str) -> bool:
        """Check if message is a cancellation response."""
        cancellations = ['no', 'nope', 'cancel', 'stop', 'abort', 'nevermind', 'forget it']
        message_lower = message.lower().strip()
        return message_lower in cancellations or any(c in message_lower for c in cancellations)
    
    def extract_intent(self, message: str) -> Dict[str, Any]:
        """
        Extract basic intent from message.
        
        Returns:
            Dict with 'action', 'target', 'filters'
        """
        message_lower = message.lower()
        
        # Common actions
        actions = {
            'list': ['list', 'show', 'get', 'display', 'find', 'fetch'],
            'count': ['count', 'how many', 'total', 'number of'],
            'create': ['create', 'add', 'new', 'insert'],
            'update': ['update', 'modify', 'change', 'edit'],
            'delete': ['delete', 'remove', 'drop', 'clear'],
            'search': ['search', 'find', 'filter', 'where']
        }
        
        detected_action = 'query'  # default
        for action, keywords in actions.items():
            if any(kw in message_lower for kw in keywords):
                detected_action = action
                break
        
        # Common targets
        targets = ['users', 'offenses', 'reference sets', 'events', 'flows', 
                  'rules', 'assets', 'domains', 'version', 'system']
        
        detected_target = None
        for target in targets:
            if target in message_lower:
                detected_target = target
                break
        
        return {
            'action': detected_action,
            'target': detected_target,
            'raw_message': message
        }


# Global instance
conversation_handler = ConversationHandler()


def needs_clarification(message: str, context: Dict = None) -> Tuple[bool, Optional[str]]:
    """Convenience function to check if clarification is needed."""
    needs_it, request = conversation_handler.analyze_input(message, context)
    if needs_it and request:
        return True, conversation_handler.format_clarification(request)
    return False, None


def extract_intent(message: str) -> Dict[str, Any]:
    """Convenience function to extract intent."""
    return conversation_handler.extract_intent(message)
