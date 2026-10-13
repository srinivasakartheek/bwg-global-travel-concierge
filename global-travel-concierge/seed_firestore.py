"""Seed script for populating Firestore with sample destinations/attractions."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-4ff6ed4e49c0"

SAMPLE_DESTINATIONS = [
    {
        "id": "paris-louvre",
        "city": "Paris",
        "name": "Louvre Museum",
        "category": "Culture & Art",
        "estimated_duration_hours": 3.0,
        "estimated_cost_usd": 25.0,
        "description": "World's largest art museum and historic monument home to the Mona Lisa.",
        "latitude": 48.8606,
        "longitude": 2.3376,
    },
    {
        "id": "paris-eiffel-tower",
        "city": "Paris",
        "name": "Eiffel Tower",
        "category": "Sightseeing",
        "estimated_duration_hours": 2.5,
        "estimated_cost_usd": 35.0,
        "description": "Iconic iron lattice tower on the Champ de Mars with panoramic city views.",
        "latitude": 48.8584,
        "longitude": 2.2945,
    },
    {
        "id": "tokyo-sensoji",
        "city": "Tokyo",
        "name": "Sensō-ji Temple",
        "category": "History & Culture",
        "estimated_duration_hours": 2.0,
        "estimated_cost_usd": 0.0,
        "description": "Tokyo's oldest and most significant ancient Buddhist temple located in Asakusa.",
        "latitude": 35.7148,
        "longitude": 139.7967,
    },
    {
        "id": "tokyo-shibuya-sky",
        "city": "Tokyo",
        "name": "Shibuya Sky",
        "category": "Observation & Modern",
        "estimated_duration_hours": 1.5,
        "estimated_cost_usd": 20.0,
        "description": "Open-air rooftop observatory with a 360-degree view of the Shibuya crossing and Tokyo skyline.",
        "latitude": 35.6585,
        "longitude": 139.7022,
    },
    {
        "id": "nyc-central-park",
        "city": "New York",
        "name": "Central Park",
        "category": "Nature & Outdoors",
        "estimated_duration_hours": 2.5,
        "estimated_cost_usd": 0.0,
        "description": "Urban park in Manhattan featuring walking paths, ponds, and landscaped gardens.",
        "latitude": 40.785091,
        "longitude": -73.968285,
    },
    {
        "id": "sf-golden-gate-bridge",
        "city": "San Francisco",
        "name": "Golden Gate Bridge",
        "category": "Sightseeing & Landmark",
        "estimated_duration_hours": 2.0,
        "estimated_cost_usd": 0.0,
        "description": "The world-famous orange suspension bridge spanning the Golden Gate strait.",
        "latitude": 37.8199,
        "longitude": -122.4783,
    },
    {
        "id": "sf-alcatraz-island",
        "city": "San Francisco",
        "name": "Alcatraz Island",
        "category": "History & Tour",
        "estimated_duration_hours": 3.5,
        "estimated_cost_usd": 45.0,
        "description": "Historic federal penitentiary on an island in San Francisco Bay, accessible by ferry.",
        "latitude": 37.8267,
        "longitude": -122.4230,
    },
    {
        "id": "sf-fishermans-wharf",
        "city": "San Francisco",
        "name": "Fisherman's Wharf & Pier 39",
        "category": "Food & Entertainment",
        "estimated_duration_hours": 2.5,
        "estimated_cost_usd": 25.0,
        "description": "Bustling waterfront neighborhood famous for sea lions, clam chowder sourdough bowls, and shopping.",
        "latitude": 37.8080,
        "longitude": -122.4177,
    },
    {
        "id": "sf-golden-gate-park",
        "city": "San Francisco",
        "name": "Golden Gate Park",
        "category": "Nature & Outdoors",
        "estimated_duration_hours": 3.0,
        "estimated_cost_usd": 0.0,
        "description": "Massive urban park featuring the Japanese Tea Garden, de Young Museum, and Conservatory of Flowers.",
        "latitude": 37.7694,
        "longitude": -122.4862,
    },
]


def seed_firestore():
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("destinations")
    print(f"Seeding items into 'destinations' collection in project '{PROJECT_ID}'...")
    for item in SAMPLE_DESTINATIONS:
        doc_ref = collection.document(item["id"])
        doc_ref.set(item)
        print(f"  ✓ Added: {item['name']} ({item['city']})")
    print("Done seeding destinations.")


if __name__ == "__main__":
    seed_firestore()
