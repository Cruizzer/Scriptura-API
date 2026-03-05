"""
Example usage of the new API endpoints.
Run this after starting the Django server with: python manage.py runserver
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_collections():
    """Test Collection CRUD operations."""
    print("\n=== Testing Collections CRUD ===\n")
    
    # List collections
    print("1. GET /api/collections/ (list all collections)")
    response = requests.get(f"{BASE_URL}/collections/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    
    # Create a collection
    print("2. POST /api/collections/ (create a collection)")
    new_collection = {
        "name": "Hope and Faith",
        "description": "Verses about trusting God",
        "verses": [1, 2, 3],  # Replace with actual verse IDs from your DB
        "themes": [1]  # Replace with actual theme IDs
    }
    response = requests.post(f"{BASE_URL}/collections/", json=new_collection)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}\n")
    
    if response.status_code == 201:
        collection_id = data['id']
        
        # Get a collection
        print(f"3. GET /api/collections/{collection_id}/ (retrieve a collection)")
        response = requests.get(f"{BASE_URL}/collections/{collection_id}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Update a collection
        print(f"4. PUT /api/collections/{collection_id}/ (update a collection)")
        updated = {
            "name": "Updated Hope and Faith",
            "description": "Verses about trusting God - updated",
            "verses": [1, 2, 3, 4],
            "themes": [1]
        }
        response = requests.put(f"{BASE_URL}/collections/{collection_id}/", json=updated)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Delete a collection
        print(f"5. DELETE /api/collections/{collection_id}/ (delete a collection)")
        response = requests.delete(f"{BASE_URL}/collections/{collection_id}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")


def test_similarity_graph():
    """Test the lexical similarity graph endpoint."""
    print("\n=== Testing Lexical Similarity Graph ===\n")
    
    # Get similarity graph with default settings
    print("1. GET /api/analytics/similarity-graph/ (default threshold)")
    response = requests.get(f"{BASE_URL}/analytics/similarity-graph/")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Number of books (nodes): {len(data['nodes'])}")
    print(f"Number of connections (edges): {len(data['edges'])}")
    print(f"Graph metric: {data['metric']}")
    print(f"Threshold: {data['threshold']}")
    print("\nSample nodes:")
    for node in data['nodes'][:3]:
        print(f"  - {node['id']} ({node['testament']}) - size: {node['size']}")
    print("\nSample edges:")
    for edge in data['edges'][:3]:
        print(f"  - {edge['source']} <-> {edge['target']}: {edge['weight']}\n")
    
    # Get similarity graph with higher threshold
    print("2. GET /api/analytics/similarity-graph/?threshold=0.5 (higher threshold)")
    response = requests.get(f"{BASE_URL}/analytics/similarity-graph/?threshold=0.5")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Number of connections with threshold=0.5: {len(data['edges'])}\n")


def test_verse_recommendations():
    """Test the verse recommendation endpoint."""
    print("\n=== Testing Verse Recommendations ===\n")
    
    # First, get a verse ID from the database
    print("1. Get a sample verse ID")
    response = requests.get(f"{BASE_URL}/verses/?limit=1")
    if response.status_code == 200:
        verses = response.json()
        if isinstance(verses, dict) and 'results' in verses:
            verse_id = verses['results'][0]['id']
        elif isinstance(verses, list) and len(verses) > 0:
            verse_id = verses[0]['id']
        else:
            print("Could not find a verse in the database")
            return
        
        print(f"Found verse ID: {verse_id}\n")
        
        # Get recommendations
        print(f"2. GET /api/analytics/verse-recommendations/?verse_id={verse_id}")
        response = requests.get(f"{BASE_URL}/analytics/verse-recommendations/?verse_id={verse_id}")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Reference verse: {data['reference_verse']['reference']}")
        print(f"Text: {data['reference_verse']['text'][:80]}...\n")
        print(f"Top 5 similar verses:")
        for rec in data['recommendations']:
            print(f"  - {rec['reference']} (similarity: {rec['similarity']})")
            print(f"    {rec['text'][:60]}...\n")


if __name__ == "__main__":
    print("=" * 80)
    print("Scriptura API - New Features Demo")
    print("=" * 80)
    
    try:
        test_collections()
        test_similarity_graph()
        test_verse_recommendations()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server at localhost:8000")
        print("Make sure to run: python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Demo complete!")
    print("=" * 80)
