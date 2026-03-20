"""
AI Coding Practice Mentor - Web Application
A personalized coding assistant that remembers student mistakes and adapts to their learning style.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import uuid
import json
import os
import hashlib
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from functools import wraps
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# Data storage (in production, use a real database)
STORAGE_PATH = 'data/'
if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH)

# Hindsight Cloud API Key
HINDSIGHT_API_KEY = "hsk_3b8acd2dfc9cae8889d98e02eacbddd1_e19bcbd62f97aaf1"


class ProgrammingLanguage:
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "c++"
    RUBY = "ruby"
    GO = "go"
    RUST = "rust"


class MistakeType:
    SYNTAX_ERROR = "syntax_error"
    LOGIC_ERROR = "logic_error"
    RUNTIME_ERROR = "runtime_error"
    OFF_BY_ONE = "off_by_one"
    TYPE_ERROR = "type_error"
    INDENTATION_ERROR = "indentation_error"
    VARIABLE_SCOPE = "variable_scope"
    ALGORITHM_MISUNDERSTANDING = "algorithm_misunderstanding"
    EDGE_CASE_MISSING = "edge_case_missing"
    PERFORMANCE_ISSUE = "performance_issue"


class Difficulty:
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserManager:
    """Manages user authentication and profiles"""
    
    def __init__(self):
        self.users_file = os.path.join(STORAGE_PATH, 'users.json')
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username: str, email: str, password: str, name: str) -> Dict:
        """Register a new user"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        # Check if username exists
        if username in users:
            return {'success': False, 'error': 'Username already exists'}
        
        # Check if email exists
        for user in users.values():
            if user.get('email') == email:
                return {'success': False, 'error': 'Email already registered'}
        
        # Validate password strength
        if len(password) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters'}
        
        # Create user
        student_id = str(uuid.uuid4())[:8]
        users[username] = {
            'username': username,
            'email': email,
            'password_hash': self._hash_password(password),
            'name': name,
            'student_id': student_id,
            'created_at': datetime.now().isoformat(),
            'preferred_languages': ['python'],
            'skill_level': {'python': 'beginner'},
            'common_mistakes': {},
            'completed_challenges': [],
            'mastery_levels': {},
            'weakest_concepts': [],
            'strongest_concepts': [],
            'streak_days': 0,
            'last_practice': None,
            'total_points': 0
        }
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        return {
            'success': True,
            'student_id': student_id,
            'username': username,
            'name': name
        }
    
    def login_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        if username not in users:
            return None
        
        user = users[username]
        if user['password_hash'] != self._hash_password(password):
            return None
        
        # Update last login and streak
        today = datetime.now().date().isoformat()
        if user.get('last_practice'):
            last_practice_date = datetime.fromisoformat(user['last_practice']).date()
            yesterday = datetime.now().date()
            if (yesterday - last_practice_date).days == 1:
                user['streak_days'] = user.get('streak_days', 0) + 1
            elif (yesterday - last_practice_date).days > 1:
                user['streak_days'] = 1
        else:
            user['streak_days'] = 1
        
        user['last_practice'] = datetime.now().isoformat()
        
        # Save updated user
        users[username] = user
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        return {
            'student_id': user['student_id'],
            'username': username,
            'name': user['name'],
            'streak_days': user['streak_days'],
            'total_points': user.get('total_points', 0)
        }
    
    def get_user_by_student_id(self, student_id: str) -> Optional[Dict]:
        """Get user by student ID"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        for username, user in users.items():
            if user['student_id'] == student_id:
                user_data = user.copy()
                user_data['username'] = username
                return user_data
        
        return None
    
    def update_user_profile(self, student_id: str, updates: Dict) -> bool:
        """Update user profile"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        for username, user in users.items():
            if user['student_id'] == student_id:
                user.update(updates)
                users[username] = user
                
                with open(self.users_file, 'w') as f:
                    json.dump(users, f, indent=2)
                return True
        
        return False
    
    def add_points(self, student_id: str, points: int) -> None:
        """Add points to user"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        for username, user in users.items():
            if user['student_id'] == student_id:
                user['total_points'] = user.get('total_points', 0) + points
                users[username] = user
                
                with open(self.users_file, 'w') as f:
                    json.dump(users, f, indent=2)
                break


class HindsightCloudMemory:
    """Manages persistent memory using Hindsight Cloud"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hindsight.cloud/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Local storage for demo
        self.students_file = os.path.join(STORAGE_PATH, 'students.json')
        self.mistakes_file = os.path.join(STORAGE_PATH, 'mistakes.json')
        
        # Initialize storage files
        for file in [self.students_file, self.mistakes_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    json.dump({}, f)
    
    def store_mistake(self, student_id: str, mistake: Dict) -> bool:
        """Store a coding mistake"""
        try:
            # Try cloud storage
            data = {
                "student_id": student_id,
                "mistake": mistake,
                "timestamp": mistake.get('timestamp', datetime.now().isoformat())
            }
            response = requests.post(
                f"{self.base_url}/memories/mistakes",
                headers=self.headers,
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Store locally
        with open(self.mistakes_file, 'r') as f:
            mistakes_data = json.load(f)
        
        if student_id not in mistakes_data:
            mistakes_data[student_id] = []
        
        mistakes_data[student_id].append(mistake)
        
        with open(self.mistakes_file, 'w') as f:
            json.dump(mistakes_data, f, indent=2)
        
        return True
    
    def get_student_mistakes(self, student_id: str, limit: int = 50) -> List[Dict]:
        """Retrieve student's past mistakes"""
        try:
            # Try cloud storage
            params = {"student_id": student_id, "limit": limit}
            response = requests.get(
                f"{self.base_url}/memories/mistakes",
                headers=self.headers,
                params=params,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("mistakes", [])
        except:
            pass
        
        # Get from local storage
        with open(self.mistakes_file, 'r') as f:
            mistakes_data = json.load(f)
        
        return mistakes_data.get(student_id, [])[:limit]
    
    def update_student_profile(self, profile: Dict) -> bool:
        """Update student learning profile"""
        try:
            # Try cloud storage
            response = requests.post(
                f"{self.base_url}/profiles/{profile['student_id']}",
                headers=self.headers,
                json=profile,
                timeout=5
            )
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Store locally
        with open(self.students_file, 'r') as f:
            students_data = json.load(f)
        
        students_data[profile['student_id']] = profile
        
        with open(self.students_file, 'w') as f:
            json.dump(students_data, f, indent=2)
        
        return True
    
    def get_student_profile(self, student_id: str) -> Optional[Dict]:
        """Retrieve student profile"""
        try:
            # Try cloud storage
            response = requests.get(
                f"{self.base_url}/profiles/{student_id}",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        # Get from local storage
        with open(self.students_file, 'r') as f:
            students_data = json.load(f)
        
        return students_data.get(student_id)


class PersonalizedChallengeGenerator:
    """Generates personalized coding challenges"""
    
    def __init__(self, memory: HindsightCloudMemory):
        self.memory = memory
        self.challenge_templates = self._load_challenge_templates()
        self.challenge_categories = self._load_categories()
    
    def _load_categories(self) -> Dict:
        """Load challenge categories with difficulty levels"""
        return {
            "arrays": {
                "beginner": ["array_sum", "find_max", "reverse_array", "count_even"],
                "intermediate": ["two_sum", "rotate_array", "merge_sorted", "find_duplicates"],
                "advanced": ["kadane", "three_sum", "max_subarray", "merge_intervals"]
            },
            "strings": {
                "beginner": ["reverse_string", "count_vowels", "palindrome", "to_uppercase"],
                "intermediate": ["anagram", "longest_prefix", "valid_parentheses", "string_compression"],
                "advanced": ["edit_distance", "kmp_search", "regex_matching", "minimum_window"]
            },
            "loops": {
                "beginner": ["fizzbuzz", "sum_numbers", "multiplication_table", "count_digits"],
                "intermediate": ["pattern_printing", "prime_numbers", "fibonacci", "factorial"],
                "advanced": ["nested_loops", "matrix_multiply", "sieve_of_eratosthenes"]
            },
            "functions": {
                "beginner": ["basic_function", "function_parameters", "return_values", "recursion_basic"],
                "intermediate": ["lambda_functions", "higher_order", "decorators", "closures"],
                "advanced": ["currying", "memoization", "function_composition"]
            },
            "dynamic_programming": {
                "beginner": ["fibonacci_dp", "climbing_stairs", "min_cost_climbing"],
                "intermediate": ["knapsack", "longest_increasing", "coin_change"],
                "advanced": ["edit_distance", "palindrome_partition", "wildcard_matching"]
            },
            "data_structures": {
                "beginner": ["stack_basic", "queue_basic", "linked_list_basic"],
                "intermediate": ["binary_tree", "hash_map", "heap_implementation"],
                "advanced": ["graph_bfs", "graph_dfs", "trie_implementation"]
            }
        }
    
    def _load_challenge_templates(self) -> Dict[str, List[Dict]]:
        """Load comprehensive challenge templates"""
        return {
            "arrays": [
                {
                    "id": "array_sum",
                    "title": "Array Sum",
                    "description": "Given an array of integers, return their sum.",
                    "difficulty": "beginner",
                    "points": 10,
                    "test_cases": [([1, 2, 3], 6), ([], 0), ([-1, 1], 0), ([5, 10, 15], 30)],
                    "concept": "arrays",
                    "starter_code": "def sum_array(arr):\n    # Your code here\n    pass\n\n# Test your code\n# print(sum_array([1, 2, 3]))  # Should print 6",
                    "examples": [
                        {"input": "[1, 2, 3]", "output": "6"},
                        {"input": "[5, 10, 15]", "output": "30"},
                        {"input": "[-1, 1]", "output": "0"}
                    ],
                    "hints": [
                        "Use a loop to iterate through the array",
                        "Initialize a variable to store the sum",
                        "Add each element to the sum variable"
                    ],
                    "solution": "def sum_array(arr):\n    return sum(arr) if arr else 0"
                },
                {
                    "id": "two_sum",
                    "title": "Two Sum",
                    "description": "Find two numbers in an array that add up to a target. Return their indices.",
                    "difficulty": "intermediate",
                    "points": 25,
                    "test_cases": [([2, 7, 11, 15], 9, [0, 1]), ([3, 2, 4], 6, [1, 2]), ([3, 3], 6, [0, 1])],
                    "concept": "arrays",
                    "starter_code": "def two_sum(nums, target):\n    # Your code here\n    pass\n\n# Test your code\n# print(two_sum([2, 7, 11, 15], 9))  # Should print [0, 1]",
                    "examples": [
                        {"input": "nums = [2, 7, 11, 15], target = 9", "output": "[0, 1]"},
                        {"input": "nums = [3, 2, 4], target = 6", "output": "[1, 2]"},
                        {"input": "nums = [3, 3], target = 6", "output": "[0, 1]"}
                    ],
                    "hints": [
                        "Use a hash map to store numbers you've seen",
                        "For each number, check if target - num exists in the map",
                        "Return indices when you find a match"
                    ],
                    "solution": "def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []"
                },
                {
                    "id": "find_max",
                    "title": "Find Maximum",
                    "description": "Given an array of integers, find and return the maximum value.",
                    "difficulty": "beginner",
                    "points": 10,
                    "test_cases": [([1, 2, 3], 3), ([-1, -2, -3], -1), ([5], 5)],
                    "concept": "arrays",
                    "starter_code": "def find_max(arr):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "[1, 2, 3]", "output": "3"},
                        {"input": "[-1, -2, -3]", "output": "-1"}
                    ],
                    "hints": [
                        "Initialize max with the first element",
                        "Loop through the array and compare",
                        "Update max when you find a larger number"
                    ],
                    "solution": "def find_max(arr):\n    if not arr:\n        return None\n    max_val = arr[0]\n    for num in arr:\n        if num > max_val:\n            max_val = num\n    return max_val"
                },
                {
                    "id": "rotate_array",
                    "title": "Rotate Array",
                    "description": "Rotate an array to the right by k steps.",
                    "difficulty": "intermediate",
                    "points": 25,
                    "test_cases": [([1,2,3,4,5], 2, [4,5,1,2,3]), ([-1,-100,3,99], 2, [3,99,-1,-100])],
                    "concept": "arrays",
                    "starter_code": "def rotate(nums, k):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "nums = [1,2,3,4,5], k = 2", "output": "[4,5,1,2,3]"},
                        {"input": "nums = [-1,-100,3,99], k = 2", "output": "[3,99,-1,-100]"}
                    ],
                    "hints": [
                        "Use array slicing",
                        "k might be larger than array length, use modulo",
                        "Consider using reverse technique"
                    ],
                    "solution": "def rotate(nums, k):\n    k = k % len(nums)\n    nums[:] = nums[-k:] + nums[:-k]\n    return nums"
                },
                {
                    "id": "kadane",
                    "title": "Maximum Subarray Sum",
                    "description": "Find the contiguous subarray with the largest sum.",
                    "difficulty": "advanced",
                    "points": 40,
                    "test_cases": [([-2,1,-3,4,-1,2,1,-5,4], 6), ([1], 1), ([5,4,-1,7,8], 23)],
                    "concept": "arrays",
                    "starter_code": "def max_subarray(nums):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "[-2,1,-3,4,-1,2,1,-5,4]", "output": "6"},
                        {"input": "[5,4,-1,7,8]", "output": "23"}
                    ],
                    "hints": [
                        "Use Kadane's algorithm",
                        "Track current sum and max sum",
                        "Reset current sum if it becomes negative"
                    ],
                    "solution": "def max_subarray(nums):\n    max_sum = current_sum = nums[0]\n    for num in nums[1:]:\n        current_sum = max(num, current_sum + num)\n        max_sum = max(max_sum, current_sum)\n    return max_sum"
                }
            ],
            "strings": [
                {
                    "id": "reverse_string",
                    "title": "Reverse String",
                    "description": "Reverse a given string.",
                    "difficulty": "beginner",
                    "points": 10,
                    "test_cases": [("hello", "olleh"), ("", ""), ("a", "a")],
                    "concept": "strings",
                    "starter_code": "def reverse_string(s):\n    # Your code here\n    pass\n\n# Test your code\n# print(reverse_string('hello'))  # Should print 'olleh'",
                    "examples": [
                        {"input": "'hello'", "output": "'olleh'"},
                        {"input": "'Python'", "output": "'nohtyP'"}
                    ],
                    "hints": [
                        "Strings can be sliced with [::-1]",
                        "Or convert to list, reverse, and join back",
                        "Consider using a loop to build the reversed string"
                    ],
                    "solution": "def reverse_string(s):\n    return s[::-1]"
                },
                {
                    "id": "valid_parentheses",
                    "title": "Valid Parentheses",
                    "description": "Check if the string has valid parentheses.",
                    "difficulty": "intermediate",
                    "points": 20,
                    "test_cases": [("()", True), ("()[]{}", True), ("(]", False), ("([)]", False)],
                    "concept": "strings",
                    "starter_code": "def is_valid(s):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "'()'", "output": "True"},
                        {"input": "'()[]{}'", "output": "True"},
                        {"input": "'(]'", "output": "False"}
                    ],
                    "hints": [
                        "Use a stack data structure",
                        "Push opening brackets, pop when closing",
                        "Check if stack is empty at the end"
                    ],
                    "solution": "def is_valid(s):\n    stack = []\n    mapping = {')': '(', '}': '{', ']': '['}\n    for char in s:\n        if char in mapping:\n            top = stack.pop() if stack else '#'\n            if mapping[char] != top:\n                return False\n        else:\n            stack.append(char)\n    return not stack"
                }
            ],
            "loops": [
                {
                    "id": "fizzbuzz",
                    "title": "FizzBuzz",
                    "description": "Print numbers 1 to n. For multiples of 3 print 'Fizz', for multiples of 5 print 'Buzz', for multiples of both print 'FizzBuzz'.",
                    "difficulty": "beginner",
                    "points": 10,
                    "test_cases": [(15, [1,2,"Fizz",4,"Buzz","Fizz",7,8,"Fizz","Buzz",11,"Fizz",13,14,"FizzBuzz"])],
                    "concept": "loops",
                    "starter_code": "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        # Your code here\n        pass\n    return result\n\n# Test your code\n# print(fizzbuzz(15))",
                    "examples": [
                        {"input": "n = 5", "output": "[1, 2, 'Fizz', 4, 'Buzz']"},
                        {"input": "n = 15", "output": "[1, 2, 'Fizz', 4, 'Buzz', 'Fizz', 7, 8, 'Fizz', 'Buzz', 11, 'Fizz', 13, 14, 'FizzBuzz']"}
                    ],
                    "hints": [
                        "Use modulo operator (%) to check divisibility",
                        "Check for multiples of 15 first (both 3 and 5)",
                        "Then check for multiples of 3 and 5 separately"
                    ],
                    "solution": "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            result.append('FizzBuzz')\n        elif i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(i)\n    return result"
                },
                {
                    "id": "fibonacci",
                    "title": "Fibonacci Sequence",
                    "description": "Generate the first n numbers in the Fibonacci sequence.",
                    "difficulty": "intermediate",
                    "points": 20,
                    "test_cases": [(5, [0,1,1,2,3]), (1, [0]), (0, [])],
                    "concept": "loops",
                    "starter_code": "def fibonacci(n):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "n = 5", "output": "[0, 1, 1, 2, 3]"},
                        {"input": "n = 7", "output": "[0, 1, 1, 2, 3, 5, 8]"}
                    ],
                    "hints": [
                        "Start with [0, 1]",
                        "Each new number is sum of previous two",
                        "Handle n=0 and n=1 cases separately"
                    ],
                    "solution": "def fibonacci(n):\n    if n <= 0:\n        return []\n    if n == 1:\n        return [0]\n    result = [0, 1]\n    for i in range(2, n):\n        result.append(result[-1] + result[-2])\n    return result"
                }
            ],
            "functions": [
                {
                    "id": "basic_function",
                    "title": "Basic Function",
                    "description": "Create a function that takes two numbers and returns their sum.",
                    "difficulty": "beginner",
                    "points": 10,
                    "test_cases": [(3, 5, 8), (-1, 1, 0), (0, 0, 0)],
                    "concept": "functions",
                    "starter_code": "def add(a, b):\n    # Your code here\n    pass\n\n# Test your code\n# print(add(3, 5))  # Should print 8",
                    "examples": [
                        {"input": "a = 3, b = 5", "output": "8"},
                        {"input": "a = -1, b = 1", "output": "0"}
                    ],
                    "hints": [
                        "Use the '+' operator to add numbers",
                        "Don't forget to return the result",
                        "The function should work for any numbers"
                    ],
                    "solution": "def add(a, b):\n    return a + b"
                },
                {
                    "id": "factorial",
                    "title": "Factorial",
                    "description": "Calculate the factorial of a number using recursion.",
                    "difficulty": "intermediate",
                    "points": 20,
                    "test_cases": [(5, 120), (0, 1), (1, 1)],
                    "concept": "functions",
                    "starter_code": "def factorial(n):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "n = 5", "output": "120"},
                        {"input": "n = 0", "output": "1"}
                    ],
                    "hints": [
                        "Base case: n == 0 or n == 1",
                        "Recursive case: n * factorial(n-1)",
                        "Handle negative numbers appropriately"
                    ],
                    "solution": "def factorial(n):\n    if n < 0:\n        return None\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
                }
            ],
            "dynamic_programming": [
                {
                    "id": "climbing_stairs",
                    "title": "Climbing Stairs",
                    "description": "You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. Find how many distinct ways you can climb to the top.",
                    "difficulty": "intermediate",
                    "points": 25,
                    "test_cases": [(2, 2), (3, 3), (4, 5), (5, 8)],
                    "concept": "dynamic_programming",
                    "starter_code": "def climb_stairs(n):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "n = 2", "output": "2 (1+1, 2)"},
                        {"input": "n = 3", "output": "3 (1+1+1, 1+2, 2+1)"}
                    ],
                    "hints": [
                        "This is a Fibonacci-like problem",
                        "Use dynamic programming to avoid recalculating",
                        "Ways(n) = Ways(n-1) + Ways(n-2)"
                    ],
                    "solution": "def climb_stairs(n):\n    if n <= 2:\n        return n\n    dp = [0] * (n + 1)\n    dp[1] = 1\n    dp[2] = 2\n    for i in range(3, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    return dp[n]"
                },
                {
                    "id": "coin_change",
                    "title": "Coin Change",
                    "description": "Find the fewest number of coins to make up a given amount.",
                    "difficulty": "advanced",
                    "points": 35,
                    "test_cases": [([1,2,5], 11, 3), ([2], 3, -1), ([1], 0, 0)],
                    "concept": "dynamic_programming",
                    "starter_code": "def coin_change(coins, amount):\n    # Your code here\n    pass",
                    "examples": [
                        {"input": "coins = [1,2,5], amount = 11", "output": "3 (5+5+1)"},
                        {"input": "coins = [2], amount = 3", "output": "-1"}
                    ],
                    "hints": [
                        "Use dynamic programming array",
                        "Initialize with infinity except dp[0] = 0",
                        "For each coin, update dp values"
                    ],
                    "solution": "def coin_change(coins, amount):\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for coin in coins:\n        for i in range(coin, amount + 1):\n            dp[i] = min(dp[i], dp[i - coin] + 1)\n    return dp[amount] if dp[amount] != float('inf') else -1"
                }
            ]
        }
    
    def get_random_challenge(self, student_profile: Dict, difficulty: str = None) -> Dict:
        """Get a random challenge for the student"""
        # Get weak concepts
        weak_concepts = student_profile.get('weakest_concepts', [])
        
        if not weak_concepts:
            weak_concepts = list(self.challenge_templates.keys())
        
        # Get skill level
        preferred_lang = student_profile.get('preferred_languages', ['python'])[0]
        skill_level = difficulty or student_profile.get('skill_level', {}).get(preferred_lang, 'beginner')
        
        # Find concept with challenges at appropriate difficulty
        available_challenges = []
        for concept in weak_concepts:
            if concept in self.challenge_templates:
                for challenge in self.challenge_templates[concept]:
                    if challenge['difficulty'] == skill_level:
                        available_challenges.append(challenge)
        
        # If no challenges at this difficulty, try all difficulties
        if not available_challenges:
            for concept in weak_concepts:
                if concept in self.challenge_templates:
                    available_challenges.extend(self.challenge_templates[concept])
        
        if not available_challenges:
            available_challenges = self.challenge_templates.get('arrays', [])
        
        # Select random challenge
        challenge = random.choice(available_challenges).copy()
        
        # Add personalization
        challenge['personalized_note'] = self._generate_personalized_note(student_profile, challenge.get('concept', ''))
        challenge['language_hints'] = self._get_language_hints(preferred_lang, challenge.get('concept', ''))
        
        return challenge
    
    def get_challenge_by_id(self, challenge_id: str) -> Optional[Dict]:
        """Get challenge by ID"""
        for concept, challenges in self.challenge_templates.items():
            for challenge in challenges:
                if challenge['id'] == challenge_id:
                    return challenge.copy()
        return None
    
    def generate_challenge(self, student_profile: Dict) -> Dict:
        """Generate personalized challenge"""
        # Get weak concepts
        weak_concepts = student_profile.get('weakest_concepts', [])
        
        if not weak_concepts:
            weak_concepts = list(self.challenge_templates.keys())
        
        # Find concept with challenges
        selected_concept = None
        for concept in weak_concepts:
            if concept in self.challenge_templates and self.challenge_templates[concept]:
                selected_concept = concept
                break
        
        if not selected_concept:
            selected_concept = list(self.challenge_templates.keys())[0]
        
        # Get challenges for concept
        available_challenges = self.challenge_templates.get(selected_concept, [])
        if not available_challenges:
            return self._get_default_challenge()
        
        # Get skill level
        preferred_lang = student_profile.get('preferred_languages', ['python'])[0]
        skill_level = student_profile.get('skill_level', {}).get(preferred_lang, 'beginner')
        
        # Filter by difficulty
        suitable_challenges = [
            c for c in available_challenges 
            if c['difficulty'] == skill_level
        ]
        
        if not suitable_challenges:
            suitable_challenges = available_challenges
        
        # Select challenge
        challenge = suitable_challenges[0].copy()
        
        # Add personalization
        challenge['personalized_note'] = self._generate_personalized_note(student_profile, selected_concept)
        challenge['language_hints'] = self._get_language_hints(preferred_lang, selected_concept)
        
        return challenge
    
    def _get_default_challenge(self) -> Dict:
        """Return default challenge"""
        return {
            "id": "hello_world",
            "title": "Hello World",
            "description": "Write a function that returns 'Hello, World!'",
            "difficulty": "beginner",
            "points": 5,
            "concept": "basics",
            "starter_code": "def hello_world():\n    # Your code here\n    return 'Hello, World!'\n\n# Test your code\n# print(hello_world())",
            "examples": [
                {"input": "No input", "output": "'Hello, World!'"}
            ],
            "hints": [
                "Return a string literal",
                "Make sure to use exactly 'Hello, World!'",
                "Don't forget the exclamation mark"
            ],
            "personalized_note": "Let's start with a simple function to build confidence!",
            "language_hints": "Python strings use quotes. Return the exact string."
        }
    
    def _generate_personalized_note(self, profile: Dict, concept: str) -> str:
        """Generate personalized note"""
        mistakes = profile.get('common_mistakes', {})
        concept_mistakes = sum(1 for m in mistakes.keys() if concept in m)
        
        if concept_mistakes > 0:
            return f"🎯 Based on your previous mistakes, let's practice {concept}. You've struggled with this before - take your time and test your code thoroughly!"
        else:
            return f"📚 This challenge focuses on {concept}. Remember to test your code with different inputs!"
    
    def _get_language_hints(self, language: str, concept: str) -> str:
        """Get language-specific hints"""
        hints = {
            "python": {
                "arrays": "Python lists are flexible. Use list comprehension for concise code.",
                "loops": "Remember that range(n) goes from 0 to n-1.",
                "strings": "Strings in Python are immutable. You'll need to create new strings.",
                "functions": "Use 'def' keyword and remember to return values.",
                "dynamic_programming": "Use memoization with @lru_cache or a dictionary.",
                "data_structures": "Python has built-in collections like list, dict, set."
            },
            "javascript": {
                "arrays": "JavaScript arrays have many built-in methods like map, filter, reduce.",
                "loops": "Watch out for var vs let scoping issues.",
                "strings": "Strings are immutable. Use split/join for modifications.",
                "functions": "Arrow functions can make your code more concise.",
                "dynamic_programming": "Use memoization with objects or Map.",
                "data_structures": "Use arrays, objects, and Map/Set."
            }
        }
        
        lang_hints = hints.get(language.lower(), hints["python"])
        return lang_hints.get(concept, "Review the concept fundamentals before starting.")
    
    def get_daily_challenge(self) -> Dict:
        """Get a daily challenge (same for all users)"""
        all_challenges = []
        for challenges in self.challenge_templates.values():
            all_challenges.extend(challenges)
        
        # Use day of year to determine daily challenge
        day_of_year = datetime.now().timetuple().tm_yday
        challenge_index = day_of_year % len(all_challenges)
        
        return all_challenges[challenge_index].copy()


class DebuggingAssistant:
    """Provides personalized debugging suggestions"""
    
    def __init__(self, memory: HindsightCloudMemory):
        self.memory = memory
    
    def analyze_code(self, student_id: str, code: str, language: str, error: Optional[str] = None) -> Dict:
        """Analyze code and provide suggestions"""
        past_mistakes = self.memory.get_student_mistakes(student_id, limit=20)
        
        suggestions = []
        similar_mistakes = []
        
        # Check for similar past mistakes
        for mistake in past_mistakes:
            if mistake.get('language') == language:
                if self._has_similar_pattern(code, mistake.get('code_snippet', '')):
                    similar_mistakes.append(mistake)
                    
                    suggestions.append({
                        "type": "pattern_matching",
                        "message": f"You've made a similar {mistake.get('mistake_type')} before. "
                                  f"Previously, you fixed it by: {mistake.get('corrected_code', '')[:100]}...",
                        "severity": mistake.get('severity', 3)
                    })
        
        # Analyze current error
        if error:
            error_suggestions = self._analyze_error(error, language)
            suggestions.extend(error_suggestions)
        
        # Add concept review suggestions
        concepts = []
        if similar_mistakes:
            concepts = list(set([m.get('concept') for m in similar_mistakes[:3]]))
            suggestions.append({
                "type": "resource",
                "message": f"📚 Review these concepts: {', '.join(concepts)}. You've struggled with them before."
            })
        
        return {
            "suggestions": suggestions,
            "similar_mistakes_count": len(similar_mistakes),
            "should_review_concepts": concepts if similar_mistakes else []
        }
    
    def _has_similar_pattern(self, code1: str, code2: str) -> bool:
        """Check for similar patterns"""
        if not code1 or not code2:
            return False
        words1 = set(code1.split())
        words2 = set(code2.split())
        return len(words1 & words2) > 3
    
    def _analyze_error(self, error: str, language: str) -> List[Dict]:
        """Analyze error message"""
        suggestions = []
        
        error_lower = error.lower()
        
        if "indentation" in error_lower:
            suggestions.append({
                "type": "syntax",
                "message": "⚠️ Indentation error detected. Python relies on consistent indentation. Use 4 spaces per level."
            })
        elif "name" in error_lower and "not defined" in error_lower:
            suggestions.append({
                "type": "scope",
                "message": "🔍 Variable name not found. Check if the variable is defined before use and is in the correct scope."
            })
        elif "type" in error_lower:
            suggestions.append({
                "type": "type",
                "message": "💡 Type mismatch error. Verify you're using the correct data types for operations."
            })
        elif "syntax" in error_lower:
            suggestions.append({
                "type": "syntax",
                "message": "🔧 Syntax error detected. Check for missing colons, parentheses, or quotes."
            })
        elif "index" in error_lower and "out of range" in error_lower:
            suggestions.append({
                "type": "logic",
                "message": "📏 Index out of range. Remember that list indices start at 0 and go to length-1."
            })
        elif "attribute" in error_lower:
            suggestions.append({
                "type": "attribute",
                "message": "🔧 Attribute error. Check if the object has the method/property you're trying to access."
            })
        
        return suggestions


class LearningPathRecommender:
    """Recommends personalized learning paths"""
    
    def __init__(self, memory: HindsightCloudMemory):
        self.memory = memory
        self.concept_hierarchy = {
            "variables": {"prerequisites": [], "difficulty": 1},
            "data_types": {"prerequisites": ["variables"], "difficulty": 1},
            "operators": {"prerequisites": ["variables"], "difficulty": 1},
            "conditionals": {"prerequisites": ["operators"], "difficulty": 2},
            "loops": {"prerequisites": ["conditionals"], "difficulty": 2},
            "functions": {"prerequisites": ["loops"], "difficulty": 2},
            "arrays": {"prerequisites": ["data_types"], "difficulty": 2},
            "strings": {"prerequisites": ["data_types"], "difficulty": 2},
            "dynamic_programming": {"prerequisites": ["arrays", "functions"], "difficulty": 3},
            "data_structures": {"prerequisites": ["functions"], "difficulty": 3},
            "algorithms": {"prerequisites": ["arrays", "functions"], "difficulty": 3},
            "classes": {"prerequisites": ["functions"], "difficulty": 3}
        }
    
    def generate_learning_path(self, student_profile: Dict) -> Dict:
        """Generate personalized learning path"""
        weak_concepts = student_profile.get('weakest_concepts', [])
        
        if not weak_concepts:
            weak_concepts = ["variables", "data_types", "conditionals", "loops"]
        
        # Build learning path based on prerequisites
        learning_path = []
        for concept in weak_concepts:
            if concept in self.concept_hierarchy:
                # Add prerequisites
                for prereq in self.concept_hierarchy[concept]["prerequisites"]:
                    if prereq not in learning_path and prereq not in student_profile.get('strongest_concepts', []):
                        learning_path.append(prereq)
                if concept not in learning_path:
                    learning_path.append(concept)
        
        # Generate practice plan
        practice_plan = []
        for concept in learning_path:
            mastery = student_profile.get('mastery_levels', {}).get(concept, 0)
            practice_plan.append({
                "concept": concept,
                "current_mastery": mastery,
                "suggested_practices": self._get_practices_for_concept(concept, mastery),
                "estimated_time_hours": self._estimate_learning_time(mastery)
            })
        
        return {
            "student_id": student_profile['student_id'],
            "learning_path": learning_path,
            "practice_plan": practice_plan,
            "recommendations": self._generate_recommendations(student_profile),
            "next_learning_goals": self._suggest_next_goals(student_profile, learning_path)
        }
    
    def _get_practices_for_concept(self, concept: str, mastery: float) -> List[str]:
        """Get practice recommendations"""
        if mastery < 0.3:
            return [
                f"📚 Review {concept} fundamentals",
                f"✏️ Complete 5 basic exercises on {concept}",
                f"🎥 Watch video tutorials on {concept}"
            ]
        elif mastery < 0.7:
            return [
                f"💪 Solve 3 intermediate problems with {concept}",
                f"🌍 Apply {concept} to real-world scenarios",
                f"🔍 Review and fix past {concept} mistakes"
            ]
        else:
            return [
                f"🚀 Tackle advanced {concept} challenges",
                f"🏗️ Build a mini-project using {concept}",
                f"👥 Help peers understand {concept}"
            ]
    
    def _estimate_learning_time(self, mastery: float) -> float:
        """Estimate learning time"""
        if mastery < 0.3:
            return 4.0
        elif mastery < 0.7:
            return 2.0
        else:
            return 1.0
    
    def _generate_recommendations(self, profile: Dict) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        # Language recommendations
        for lang in profile.get('preferred_languages', []):
            skill = profile.get('skill_level', {}).get(lang, 'beginner')
            if skill == 'beginner':
                recommendations.append(f"🎯 Focus on {lang} fundamentals")
            elif skill == 'intermediate':
                recommendations.append(f"📈 Explore {lang} libraries and frameworks")
            elif skill == 'advanced':
                recommendations.append(f"🏆 Challenge yourself with advanced {lang} concepts")
        
        # Mistake pattern recommendations
        common_mistakes = profile.get('common_mistakes', {})
        if common_mistakes:
            top_mistake = max(common_mistakes.items(), key=lambda x: x[1])
            if top_mistake[1] > 3:
                recommendations.append(
                    f"⚠️ You've made {top_mistake[0]} {top_mistake[1]} times. Review this pattern!"
                )
        
        # Streak recommendation
        if profile.get('streak_days', 0) > 0:
            recommendations.append(f"🔥 You have a {profile.get('streak_days', 0)}-day streak! Keep it up!")
        
        if not recommendations:
            recommendations = [
                "💡 Solve at least one coding problem daily",
                "📝 Document your mistakes and learnings",
                "🤝 Join coding communities for support"
            ]
        
        return recommendations
    
    def _suggest_next_goals(self, profile: Dict, learning_path: List[str]) -> List[str]:
        """Suggest next goals"""
        goals = []
        
        if learning_path:
            goals.append(f"📌 Master {learning_path[0]} to build a strong foundation")
        
        if len(profile.get('preferred_languages', [])) == 1:
            goals.append(f"🔧 Deep dive into {profile['preferred_languages'][0]} ecosystem")
        else:
            goals.append("🔄 Practice switching between languages to reinforce concepts")
        
        goals.append("🏗️ Start a small project combining multiple concepts")
        
        return goals


# Initialize components
user_manager = UserManager()
memory = HindsightCloudMemory(HINDSIGHT_API_KEY)
challenge_generator = PersonalizedChallengeGenerator(memory)
debugging_assistant = DebuggingAssistant(memory)
learning_recommender = LearningPathRecommender(memory)

# Store active sessions
active_sessions = {}


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            return jsonify({'error': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Render main page"""
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """Render dashboard (requires login)"""
    if 'student_id' not in session:
        return redirect(url_for('index'))
    return render_template('index.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = user_manager.login_user(username, password)
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['student_id'] = user['student_id']
    session['username'] = user['username']
    session['name'] = user['name']
    
    return jsonify({
        'success': True,
        'student_id': user['student_id'],
        'username': user['username'],
        'name': user['name'],
        'streak_days': user['streak_days'],
        'total_points': user['total_points']
    })


@app.route('/api/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not all([username, email, password, name]):
        return jsonify({'error': 'All fields required'}), 400
    
    # Validate email
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    result = user_manager.register_user(username, email, password, name)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'success': True,
        'student_id': result['student_id'],
        'username': result['username'],
        'name': result['name']
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True})


@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'student_id' in session:
        user = user_manager.get_user_by_student_id(session['student_id'])
        return jsonify({
            'authenticated': True,
            'student_id': session['student_id'],
            'username': session.get('username'),
            'name': session.get('name'),
            'total_points': user.get('total_points', 0) if user else 0,
            'streak_days': user.get('streak_days', 0) if user else 0
        })
    return jsonify({'authenticated': False})


@app.route('/api/challenge/<student_id>', methods=['GET'])
@login_required
def get_challenge(student_id):
    """Get personalized challenge"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    profile = memory.get_student_profile(student_id)
    
    if not profile:
        # Get from user manager
        user = user_manager.get_user_by_student_id(student_id)
        if user:
            profile = {
                'student_id': student_id,
                'preferred_languages': user.get('preferred_languages', ['python']),
                'skill_level': user.get('skill_level', {'python': 'beginner'}),
                'common_mistakes': user.get('common_mistakes', {}),
                'completed_challenges': user.get('completed_challenges', []),
                'mastery_levels': user.get('mastery_levels', {}),
                'weakest_concepts': user.get('weakest_concepts', []),
                'strongest_concepts': user.get('strongest_concepts', [])
            }
        else:
            return jsonify({'error': 'Student not found'}), 404
    
    challenge = challenge_generator.generate_challenge(profile)
    challenge['student_id'] = student_id
    
    # Start session
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        'student_id': student_id,
        'challenge': challenge,
        'start_time': datetime.now().isoformat(),
        'submissions': [],
        'mistakes': []
    }
    
    challenge['session_id'] = session_id
    
    return jsonify(challenge)


@app.route('/api/random-challenge/<student_id>', methods=['GET'])
@login_required
def get_random_challenge(student_id):
    """Get a random challenge"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    difficulty = request.args.get('difficulty', None)
    
    profile = memory.get_student_profile(student_id)
    
    if not profile:
        user = user_manager.get_user_by_student_id(student_id)
        if user:
            profile = {
                'student_id': student_id,
                'preferred_languages': user.get('preferred_languages', ['python']),
                'skill_level': user.get('skill_level', {'python': 'beginner'}),
                'common_mistakes': user.get('common_mistakes', {}),
                'completed_challenges': user.get('completed_challenges', []),
                'mastery_levels': user.get('mastery_levels', {}),
                'weakest_concepts': user.get('weakest_concepts', []),
                'strongest_concepts': user.get('strongest_concepts', [])
            }
    
    challenge = challenge_generator.get_random_challenge(profile, difficulty)
    challenge['student_id'] = student_id
    
    # Start session
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        'student_id': student_id,
        'challenge': challenge,
        'start_time': datetime.now().isoformat(),
        'submissions': [],
        'mistakes': []
    }
    
    challenge['session_id'] = session_id
    
    return jsonify(challenge)


@app.route('/api/daily-challenge', methods=['GET'])
def get_daily_challenge():
    """Get daily challenge (no login required)"""
    challenge = challenge_generator.get_daily_challenge()
    return jsonify(challenge)


@app.route('/api/submit', methods=['POST'])
@login_required
def submit_code():
    """Submit code for evaluation"""
    data = request.json
    session_id = data.get('session_id')
    code = data.get('code')
    error = data.get('error')
    is_correct = data.get('is_correct', False)
    
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session_data = active_sessions[session_id]
    student_id = session_data['student_id']
    
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Record submission
    session_data['submissions'].append({
        'code': code,
        'timestamp': datetime.now().isoformat(),
        'error': error,
        'is_correct': is_correct
    })
    
    # Get debugging suggestions if there's an error
    suggestions = {}
    if error:
        suggestions = debugging_assistant.analyze_code(
            student_id, code, 'python', error
        )
    
    # If correct, update profile
    if is_correct:
        session_data['end_time'] = datetime.now().isoformat()
        session_data['success'] = True
        
        # Update student profile
        profile = memory.get_student_profile(student_id)
        user = user_manager.get_user_by_student_id(student_id)
        
        if profile:
            # Update completed challenges
            challenge_id = session_data['challenge']['id']
            if challenge_id not in profile.get('completed_challenges', []):
                profile['completed_challenges'].append(challenge_id)
            
            # Update mastery levels
            concept = session_data['challenge'].get('concept')
            points = session_data['challenge'].get('points', 10)
            
            if concept:
                current_mastery = profile.get('mastery_levels', {}).get(concept, 0)
                profile['mastery_levels'][concept] = min(1.0, current_mastery + 0.1)
            
            # Add points
            user_manager.add_points(student_id, points)
            
            # Update skill level based on progress
            if len(profile.get('completed_challenges', [])) > 5:
                for lang in profile.get('preferred_languages', []):
                    profile['skill_level'][lang] = 'intermediate'
            elif len(profile.get('completed_challenges', [])) > 15:
                for lang in profile.get('preferred_languages', []):
                    profile['skill_level'][lang] = 'advanced'
            
            memory.update_student_profile(profile)
        
        # Update user's completed challenges
        if user:
            if challenge_id not in user.get('completed_challenges', []):
                user['completed_challenges'] = user.get('completed_challenges', []) + [challenge_id]
                user_manager.update_user_profile(student_id, user)
    
    return jsonify({
        'is_correct': is_correct,
        'debugging_suggestions': suggestions,
        'submission_count': len(session_data['submissions'])
    })


@app.route('/api/mistake', methods=['POST'])
@login_required
def record_mistake():
    """Record a coding mistake"""
    data = request.json
    student_id = data.get('student_id')
    
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    mistake = {
        'mistake_id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'language': data.get('language', 'python'),
        'mistake_type': data.get('mistake_type', 'logic_error'),
        'code_snippet': data.get('code_snippet', ''),
        'error_message': data.get('error_message', ''),
        'corrected_code': data.get('corrected_code', ''),
        'concept': data.get('concept', ''),
        'context': data.get('context', ''),
        'severity': data.get('severity', 3)
    }
    
    # Store mistake
    memory.store_mistake(student_id, mistake)
    
    # Update profile with mistake pattern
    profile = memory.get_student_profile(student_id)
    if profile:
        mistake_type = mistake['mistake_type']
        profile['common_mistakes'][mistake_type] = profile['common_mistakes'].get(mistake_type, 0) + 1
        
        # Update weakest concepts
        concept_mistakes = {}
        all_mistakes = memory.get_student_mistakes(student_id)
        for m in all_mistakes:
            concept = m.get('concept')
            if concept:
                concept_mistakes[concept] = concept_mistakes.get(concept, 0) + 1
        
        # Sort concepts by mistake frequency
        profile['weakest_concepts'] = sorted(
            concept_mistakes.keys(),
            key=lambda c: concept_mistakes[c],
            reverse=True
        )[:5]
        
        memory.update_student_profile(profile)
    
    return jsonify({'success': True, 'mistake_id': mistake['mistake_id']})


@app.route('/api/learning-path/<student_id>', methods=['GET'])
@login_required
def get_learning_path(student_id):
    """Get personalized learning path"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    profile = memory.get_student_profile(student_id)
    
    if not profile:
        user = user_manager.get_user_by_student_id(student_id)
        if user:
            profile = {
                'student_id': student_id,
                'preferred_languages': user.get('preferred_languages', ['python']),
                'skill_level': user.get('skill_level', {'python': 'beginner'}),
                'common_mistakes': user.get('common_mistakes', {}),
                'completed_challenges': user.get('completed_challenges', []),
                'mastery_levels': user.get('mastery_levels', {}),
                'weakest_concepts': user.get('weakest_concepts', []),
                'strongest_concepts': user.get('strongest_concepts', [])
            }
    
    if not profile:
        return jsonify({'error': 'Student not found'}), 404
    
    learning_path = learning_recommender.generate_learning_path(profile)
    return jsonify(learning_path)


@app.route('/api/profile/<student_id>', methods=['GET'])
@login_required
def get_profile(student_id):
    """Get student profile"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    profile = memory.get_student_profile(student_id)
    
    if not profile:
        user = user_manager.get_user_by_student_id(student_id)
        if user:
            return jsonify(user)
    
    if not profile:
        return jsonify({'error': 'Student not found'}), 404
    
    return jsonify(profile)


@app.route('/api/mistakes/<student_id>', methods=['GET'])
@login_required
def get_mistakes(student_id):
    """Get student's mistakes"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    mistakes = memory.get_student_mistakes(student_id)
    return jsonify({'mistakes': mistakes, 'count': len(mistakes)})


@app.route('/api/stats/<student_id>', methods=['GET'])
@login_required
def get_stats(student_id):
    """Get student statistics"""
    if student_id != session['student_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    profile = memory.get_student_profile(student_id)
    mistakes = memory.get_student_mistakes(student_id)
    user = user_manager.get_user_by_student_id(student_id)
    
    if not profile and not user:
        return jsonify({'error': 'Student not found'}), 404
    
    if not profile:
        profile = {}
    
    # Calculate statistics
    total_challenges = len(profile.get('completed_challenges', [])) or len(user.get('completed_challenges', []))
    total_mistakes = len(mistakes)
    
    # Group mistakes by type
    mistake_types = {}
    for mistake in mistakes:
        mtype = mistake.get('mistake_type', 'unknown')
        mistake_types[mtype] = mistake_types.get(mtype, 0) + 1
    
    # Calculate average mastery
    mastery_levels = profile.get('mastery_levels', {})
    avg_mastery = sum(mastery_levels.values()) / max(len(mastery_levels), 1) if mastery_levels else 0
    
    return jsonify({
        'total_challenges_completed': total_challenges,
        'total_mistakes': total_mistakes,
        'mistake_types': mistake_types,
        'average_mastery': avg_mastery,
        'skill_level': profile.get('skill_level', user.get('skill_level', {})),
        'weakest_concepts': profile.get('weakest_concepts', [])[:3],
        'learning_speed': profile.get('learning_speed', 0),
        'streak_days': user.get('streak_days', 0),
        'total_points': user.get('total_points', 0)
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)