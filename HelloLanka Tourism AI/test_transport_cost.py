import sys
import os
sys.path.append('src')
from agents.transport_agent import get_transport_cost

# Test the transport cost function directly
print("Testing get_transport_cost function...")

try:
    result = get_transport_cost("Colombo", "Galle", "driving")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
