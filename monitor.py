import requests
import json
import os
from datetime import datetime, timedelta
import time

class TornMonitor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.torn.com/user"
        self.data_file = "data/activity_data.json"
        self.users_file = "data/users.json"
        
    def load_data(self):
        """Load existing activity data"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_data(self, data):
        """Save activity data"""
        os.makedirs('data', exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_users(self):
        """Load list of users to monitor"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                return json.load(f)
        return []
    
    def is_online(self, last_action_timestamp):
        """Check if user is considered online (active within 15 minutes)"""
        current_time = int(time.time())
        return (current_time - last_action_timestamp) < 900  # 15 minutes
    
    def fetch_user_data(self, user_id):
        """Fetch user data from Torn API"""
        url = f"{self.base_url}/{user_id}?selections=profile&key={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching user {user_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception fetching user {user_id}: {e}")
            return None
    
    def update_activity(self, user_id, user_data, activity_data):
        """Update activity data for a user"""
        current_timestamp = int(time.time())
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize user data if not exists
        if user_id not in activity_data:
            activity_data[user_id] = {
                "name": user_data.get("name", "Unknown"),
                "online_periods": [],
                "last_check": None,
                "currently_online": False
            }
        
        user_activity = activity_data[user_id]
        user_activity["name"] = user_data.get("name", user_activity["name"])
        
        last_action = user_data.get("last_action", {})
        last_timestamp = last_action.get("timestamp", 0)
        is_currently_online = self.is_online(last_timestamp)
        
        # Track online periods
        if is_currently_online and not user_activity["currently_online"]:
            # User came online
            user_activity["online_periods"].append({
                "start": current_timestamp,
                "end": None,
                "date": current_date
            })
        elif not is_currently_online and user_activity["currently_online"]:
            # User went offline
            if user_activity["online_periods"] and user_activity["online_periods"][-1]["end"] is None:
                user_activity["online_periods"][-1]["end"] = current_timestamp
        
        user_activity["currently_online"] = is_currently_online
        user_activity["last_check"] = current_timestamp
        
        # Clean old data (keep last 30 days)
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        user_activity["online_periods"] = [
            period for period in user_activity["online_periods"]
            if period["date"] >= cutoff_date
        ]
    
    def monitor_users(self):
        """Main monitoring function"""
        users = self.load_users()
        activity_data = self.load_data()
        
        if not users:
            print("No users to monitor. Add user IDs to data/users.json")
            return
        
        print(f"Monitoring {len(users)} users...")
        
        for i, user_id in enumerate(users):
            if i >= 10:  # Rate limit: max 10 calls per run
                print("Rate limit reached, stopping this run")
                break
                
            print(f"Checking user {user_id}...")
            user_data = self.fetch_user_data(user_id)
            
            if user_data:
                self.update_activity(str(user_id), user_data, activity_data)
            
            # Small delay between requests
            time.sleep(1)
        
        self.save_data(activity_data)
        print("Monitoring complete")

if __name__ == "__main__":
    api_key = os.environ.get("TORN_API_KEY")
    if not api_key:
        print("TORN_API_KEY environment variable not set")
        exit(1)
    
    monitor = TornMonitor(api_key)
    monitor.monitor_users()
