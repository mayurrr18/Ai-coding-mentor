#!/usr/bin/env python3
"""Validate challenge structure and identify issues"""

from app import PersonalizedChallengeGenerator

def validate_challenges():
    gen = PersonalizedChallengeGenerator(None)
    templates = gen._load_challenge_templates()
    
    required_fields = ['id', 'title', 'description', 'difficulty', 'points', 'concept', 
                       'starter_code', 'examples', 'hints', 'solution']
    
    issues = []
    fixed_count = 0
    
    for category, challenges in templates.items():
        for challenge in challenges:
            missing_fields = []
            for field in required_fields:
                if field not in challenge:
                    missing_fields.append(field)
            
            if missing_fields:
                issues.append(f"Challenge '{challenge.get('id', 'UNKNOWN')}' missing: {missing_fields}")
            
            # Check if test_cases exist
            if 'test_cases' not in challenge:
                issues.append(f"Challenge '{challenge.get('id')}' missing test_cases")
            
            # Validate structure
            if isinstance(challenge.get('examples'), list):
                for i, ex in enumerate(challenge['examples']):
                    if 'input' not in ex or 'output' not in ex:
                        issues.append(f"Challenge '{challenge.get('id')}' example {i} missing input/output")
    
    if not issues:
        print("✅ All challenges are properly structured!")
        return True
    else:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False

if __name__ == '__main__':
    validate_challenges()
