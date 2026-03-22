#!/usr/bin/env python3
"""Test script to verify challenges are loading correctly"""

from app import PersonalizedChallengeGenerator

try:
    gen = PersonalizedChallengeGenerator(None)
    templates = gen._load_challenge_templates()
    
    print("✅ Challenges loaded successfully!")
    print(f"\nTotal categories: {len(templates)}")
    
    for category, challenges in templates.items():
        print(f"\n{category.upper()}: {len(challenges)} challenges")
        for challenge in challenges[:2]:  # Show first 2 of each
            print(f"  - {challenge['id']}: {challenge['title']}")
        if len(challenges) > 2:
            print(f"  ... and {len(challenges) - 2} more")

except Exception as e:
    print(f"❌ Error loading challenges: {e}")
    import traceback
    traceback.print_exc()
