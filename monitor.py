import requests
import json
import os
from datetime import datetime, timedelta
import time

def load_json(file, default=None):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default or {}

def save_json(file, data):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def fetch_user(user_id, api_key):
    url = f"https://api.torn.com/user/{user_id}?selections=profile&key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def main():
    api_key = os.environ.get('TORN_API_KEY')
    users_to_monitor = load_json('data/users.json', [])
    activity_data = load_json('data/activity.json', {})
    
    print(f"Monitoring {len(users_to_monitor)} users...")
    
    for user_id in users_to_monitor[:10]:  # Rate limit: 10 users per run
        print(f"Checking {user_id}...")
        user_data = fetch_user(user_id, api_key)
        
        if not user_data:
            continue
            
        # Initialize user if new
        if str(user_id) not in activity_data:
            activity_data[str(user_id)] = {
                'name': user_data.get('name', 'Unknown'),
                'sessions': [],
                'stats': {}
            }
        
        user_activity = activity_data[str(user_id)]
        user_activity['name'] = user_data.get('name', user_activity['name'])
        
        # Check if online
        is_online = user_data.get('last_action', {}).get('status') == 'Online'
        timestamp = int(time.time())
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Handle session tracking
        sessions = user_activity['sessions']
        
        if is_online:
            # Start new session if not already in one
            if not sessions or sessions[-1].get('end'):
                sessions.append({
                    'start': timestamp,
                    'end': None,
                    'date': date
                })
        else:
            # End current session if online
            if sessions and not sessions[-1].get('end'):
                sessions[-1]['end'] = timestamp
        
        # Clean old sessions (keep 30 days)
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        user_activity['sessions'] = [s for s in sessions if s['date'] >= cutoff]
        
        time.sleep(1)  # Small delay
    
    save_json('data/activity.json', activity_data)
    print("Done!")

if __name__ == '__main__':
    main()
