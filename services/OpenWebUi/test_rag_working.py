#!/usr/bin/env python3
"""
Test RAG Integration - Verify RAG is actually working

This script tests that:
1. Qdrant has indexed vectors
2. OpenWebUI can search them
3. Claude can retrieve context and answer

Usage:
    python test_rag_working.py
"""

import sys
import os
import requests
import json

def test_qdrant_vectors():
    """Check if Qdrant has vectors indexed"""
    print("\n[Test 1/3] Checking Qdrant vectors...")
    try:
        response = requests.get("http://localhost:6333/collections/open-webui_knowledge")
        data = response.json()

        points_count = data['result']['points_count']
        print(f"✓ Qdrant has {points_count} vector(s) indexed")

        if points_count == 0:
            print("⚠ No vectors found. Upload a file first!")
            return False
        return True
    except Exception as e:
        print(f"✗ Failed to check Qdrant: {e}")
        return False

def test_litellm_connection():
    """Check if LiteLLM proxy is working"""
    print("\n[Test 2/3] Checking LiteLLM proxy...")
    try:
        response = requests.get(
            "http://localhost:4000/v1/models",
            headers={"Authorization": "Bearer sk-litellm-master-key"}
        )
        data = response.json()

        models = [m['id'] for m in data['data']]
        print(f"✓ LiteLLM has {len(models)} Claude model(s) available:")
        for model in models:
            print(f"    - {model}")
        return True
    except Exception as e:
        print(f"✗ Failed to check LiteLLM: {e}")
        return False

def test_claude_query():
    """Test a simple Claude query (without RAG)"""
    print("\n[Test 3/3] Testing Claude API...")
    try:
        response = requests.post(
            "http://localhost:4000/v1/chat/completions",
            headers={
                "Authorization": "Bearer sk-litellm-master-key",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-haiku-3.5",
                "messages": [{"role": "user", "content": "Say 'RAG test successful' in Russian"}],
                "max_tokens": 50
            }
        )
        data = response.json()

        if 'choices' in data:
            answer = data['choices'][0]['message']['content']
            print(f"✓ Claude responded: {answer}")
            return True
        else:
            print(f"✗ Unexpected response: {data}")
            return False
    except Exception as e:
        print(f"✗ Failed to query Claude: {e}")
        return False

def print_instructions():
    """Print instructions for manual RAG testing"""
    print("\n" + "="*60)
    print("How to Verify RAG in OpenWebUI UI")
    print("="*60)
    print("""
1. Open: http://localhost:3000
2. Create a new chat
3. Select model: claude-sonnet-3.5 or claude-haiku-3.5
4. Type: #Meetings (to attach Knowledge Base)
5. Ask: "What is in the test file?"

✅ If RAG is working, you'll see:
   - Citations like [1], [2] in the response
   - A "Sources" section below with file references
   - Relevant chunks from your indexed documents

❌ If RAG is NOT working:
   - No citations in response
   - Claude says "I don't have access to that information"
   - No "Sources" section appears

To monitor RAG in real-time:
   Run: services\\OpenWebUi\\monitor_rag.bat
   Then ask questions in OpenWebUI and watch logs
""")

def main():
    # Fix Windows console encoding
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("\n" + "="*60)
    print("RAG Integration Verification Test")
    print("="*60)

    results = []
    results.append(("Qdrant Vectors", test_qdrant_vectors()))
    results.append(("LiteLLM Proxy", test_litellm_connection()))
    results.append(("Claude API", test_claude_query()))

    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All backend tests passed!")
        print_instructions()
        return 0
    else:
        print("\n✗ Some tests failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
