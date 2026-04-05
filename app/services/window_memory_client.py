"""
Window Memory Client Example
Demonstrates how to use the Window Memory API with the chat service.
"""

import requests
import json
import uuid
import time
from datetime import datetime


class WindowMemoryChatClient:
    """Client for interacting with the chat API using Window Memory."""

    def __init__(self, api_url: str = "http://localhost:8080/api"):
        self.api_url = api_url
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []

    def send_message(self, message: str) -> str:
        """
        Send a message and get a response with conversation memory.
        
        Args:
            message: User message
            
        Returns:
            Assistant response (streamed)
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] User: {message}")
        
        url = f"{self.api_url}/chat"
        params = {"session_id": self.session_id}
        payload = {"query": message}
        
        try:
            response = requests.post(
                url,
                json=payload,
                params=params,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            # Stream the response
            full_response = ""
            print("Assistant: ", end="", flush=True)
            
            for chunk in response.iter_content(decode_unicode=True):
                if chunk:
                    print(chunk, end="", flush=True)
                    full_response += chunk
            
            print()  # Newline after response
            
            # Store in local history
            self.conversation_history.append({
                "role": "user",
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "message": full_response,
                "timestamp": datetime.now().isoformat()
            })
            
            return full_response
            
        except Exception as e:
            print(f"Error: {e}")
            return ""

    def get_conversation_history(self) -> list:
        """Retrieve full conversation history from server."""
        url = f"{self.api_url}/chat/history/{self.session_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("messages", [])
        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []

    def display_statistics(self) -> None:
        """Display conversation statistics."""
        url = f"{self.api_url}/chat/history/{self.session_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            print("\n" + "="*50)
            print("CONVERSATION STATISTICS")
            print("="*50)
            print(f"Session ID: {self.session_id}")
            print(f"Total Messages: {data.get('message_count', 0)}")
            
            stats = data.get("statistics", {})
            print(f"User Messages: {stats.get('user_count', 0)}")
            print(f"Assistant Messages: {stats.get('assistant_count', 0)}")
            
            print("\nMessage History:")
            for msg in data.get("messages", []):
                role = msg.get("role", "unknown").upper()
                content = msg.get("message", "")[:100] + "..."
                print(f"  [{role}] {content}")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"Error displaying statistics: {e}")

    def clear_history(self) -> bool:
        """Clear conversation history."""
        url = f"{self.api_url}/chat/history/{self.session_id}"
        
        try:
            response = requests.delete(url, timeout=10)
            response.raise_for_status()
            print(f"✓ Session history cleared")
            self.conversation_history = []
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False

    def check_health(self) -> bool:
        """Check if Window Memory service is healthy."""
        url = f"{self.api_url}/chat/health"
        
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            
            is_healthy = data.get("status") == "healthy"
            redis_connected = data.get("redis_connected", False)
            active_sessions = data.get("active_sessions", 0)
            
            print(f"Window Memory Status: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
            print(f"Redis Connected: {'✓ Yes' if redis_connected else '✗ No'}")
            print(f"Active Sessions: {active_sessions}")
            
            return is_healthy
        except Exception as e:
            print(f"Error checking health: {e}")
            return False


def interactive_chat_session():
    """Run an interactive chat session with Window Memory."""
    
    print("="*60)
    print("E-Commerce RAG Chat with Window Memory")
    print("="*60)
    
    client = WindowMemoryChatClient()
    
    # Check health
    print("\nChecking service health...")
    if not client.check_health():
        print("⚠️ Warning: Window Memory service may not be available")
    
    print(f"\nSession ID: {client.session_id}")
    print("Commands: 'history' - show stats, 'clear' - clear history, 'quit' - exit\n")
    
    # Example conversation
    example_messages = [
        "Bạn có những loại sản phẩm electronics nào?",
        "Tôi muốn mua laptop dưới 20 triệu đồng",
        "Có chiếc nào giảm giá không?",
    ]
    
    while True:
        try:
            # Use example messages or get user input
            if example_messages:
                user_input = example_messages.pop(0)
                print(f"(Auto) {user_input}")
            else:
                user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print("Goodbye!")
                break
            elif user_input.lower() == "history":
                client.display_statistics()
            elif user_input.lower() == "clear":
                if client.clear_history():
                    print("✓ History cleared, starting fresh conversation")
            else:
                # Send message and get response
                response = client.send_message(user_input)
                if not response:
                    print("No response received. Check server logs.")
        
        except KeyboardInterrupt:
            print("\n\nSession interrupted by user")
            break
        except Exception as e:
            print(f"\nError: {e}")
            continue


def batch_conversation_example():
    """Example of multiple conversations in sequence."""
    
    print("="*60)
    print("Batch Conversation Example")
    print("="*60)
    
    # Simulate multiple users
    conversations = [
        {
            "user_id": "user_alice",
            "messages": [
                "Show me all Phones",
                "Filter by price under 15 million",
                "What about accessories?",
            ]
        },
        {
            "user_id": "user_bob",
            "messages": [
                "I'm looking for Laptops",
                "Do you have gaming laptops?",
                "Can you compare prices?",
            ]
        }
    ]
    
    for conv in conversations:
        print(f"\n{'='*60}")
        print(f"Conversation with {conv['user_id']}")
        print(f"{'='*60}")
        
        client = WindowMemoryChatClient()
        client.session_id = conv["user_id"]
        
        for message in conv["messages"]:
            client.send_message(message)
            time.sleep(1)  # Delay between messages
        
        # Show final statistics
        client.display_statistics()


def monitor_sessions():
    """Monitor active window memory sessions."""
    
    print("="*60)
    print("Window Memory Session Monitor")
    print("="*60)
    
    api_url = "http://localhost:8080/api"
    
    try:
        # Check health
        response = requests.get(f"{api_url}/chat/health", timeout=5)
        data = response.json()
        
        print(f"\nService Status: {data.get('status')}")
        print(f"Redis: {'Connected' if data.get('redis_connected') else 'Disconnected'}")
        print(f"Active Sessions: {data.get('active_sessions')}")
        
        print("\n" + "-"*60)
        print("Session Monitoring Tips:")
        print("-"*60)
        print("1. Monitor Redis memory: redis-cli INFO memory")
        print("2. Check active keys: redis-cli KEYS 'window_memory:*'")
        print("3. View session stats: redis-cli HGETALL 'window_memory:meta:SESSION_ID'")
        print("4. Clear old sessions: Use API DELETE endpoint")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            interactive_chat_session()
        elif sys.argv[1] == "batch":
            batch_conversation_example()
        elif sys.argv[1] == "monitor":
            monitor_sessions()
    else:
        print("Window Memory Client Examples")
        print("\nUsage:")
        print("  python window_memory_client.py interactive  - Interactive chat")
        print("  python window_memory_client.py batch        - Run batch conversations")
        print("  python window_memory_client.py monitor      - Monitor sessions")
