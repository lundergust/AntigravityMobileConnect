
import json
import hashlib

# Mock implementation of the merging logic from bridge.py
def merge_messages(history, snapshot_messages):
    # Snapshot map for quick lookup
    snapshot_map = {m["id"]: m for m in snapshot_messages if "id" in m}
    
    # Set of IDs currently in history
    history_ids = set()
    
    # Update existing
    for msg in history:
        msg_id = msg.get("id")
        history_ids.add(msg_id)
        if msg_id in snapshot_map:
            # Update content, role, type
            new_msg = snapshot_map[msg_id]
            msg["content"] = new_msg.get("content", msg["content"])
            msg["role"] = new_msg.get("role", msg["role"])
            msg["type"] = new_msg.get("type", msg.get("type", "text"))

    # Append new
    for msg in snapshot_messages:
        if msg.get("id") not in history_ids:
            history.append(msg)
            
    return history

def test_merge_logic():
    print("🧪 Testing Message Merge Logic...")
    
    # Scene 1: Initial load
    history = []
    snapshot1 = [
        {"id": "msg1", "role": "user", "content": "Hello", "type": "text"},
        {"id": "msg2", "role": "assistant", "content": "Hi there", "type": "text"}
    ]
    
    merge_messages(history, snapshot1)
    assert len(history) == 2
    assert history[0]["content"] == "Hello"
    print("✅ Scene 1: Initial load passed")

    # Scene 2: Streaming update (content change)
    snapshot2 = [
        {"id": "msg1", "role": "user", "content": "Hello", "type": "text"},
        {"id": "msg2", "role": "assistant", "content": "Hi there! How can I help?", "type": "text"}
    ]
    
    merge_messages(history, snapshot2)
    assert len(history) == 2
    assert history[1]["content"] == "Hi there! How can I help?"
    print("✅ Scene 2: Streaming update passed")
    
    # Scene 3: New message (Assistant continued)
    snapshot3 = [
        {"id": "msg1", "role": "user", "content": "Hello", "type": "text"},
        {"id": "msg2", "role": "assistant", "content": "Hi there! How can I help?", "type": "text"},
        {"id": "msg3", "role": "assistant", "content": "I can write code.", "type": "text"}
    ]
    
    merge_messages(history, snapshot3)
    assert len(history) == 3
    assert history[2]["id"] == "msg3"
    print("✅ Scene 3: New message passed")
    
    # Scene 4: Virtualization (Old message drops off snapshot)
    snapshot4 = [
        # msg1 dropped
        {"id": "msg2", "role": "assistant", "content": "Hi there! How can I help?", "type": "text"},
        {"id": "msg3", "role": "assistant", "content": "I can write code.", "type": "text"},
        {"id": "msg4", "role": "user", "content": "Cool", "type": "text"}
    ]
    
    merge_messages(history, snapshot4)
    assert len(history) == 4
    assert history[0]["id"] == "msg1" # Should still be there!
    assert history[3]["id"] == "msg4"
    print("✅ Scene 4: Virtualization (persistence) passed")

    # Scene 5: Artifact detection update
    snapshot5 = [
         {"id": "msg2", "role": "assistant", "content": "Hi there! How can I help?", "type": "text"},
         {"id": "msg3", "role": "assistant", "content": "I can write code.", "type": "text"},
         {"id": "msg4", "role": "user", "content": "Cool", "type": "text"},
         {"id": "msg5", "role": "assistant", "content": "Artifact: file.txt", "type": "artifact"}
    ]
    merge_messages(history, snapshot5)
    assert len(history) == 5
    assert history[4]["type"] == "artifact"
    print("✅ Scene 5: Artifact rendering passed")

    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_merge_logic()
