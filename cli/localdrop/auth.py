import httpx
import time
import sys
from .config import config, set_auth_token, save_config


async def login(server_url: str = None):
    base_url = (server_url or config.server_url).rstrip("/")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        device_response = await client.post(f"{base_url}/auth/device")
        if device_response.status_code != 200:
            print("Failed to initiate device flow. Is the server running?")
            return False
        
        device_data = device_response.json()
        device_code = device_data.get("device_code")
        verification_url = device_data.get("verification_url")
        user_code = device_data.get("user_code")
        
        print(f"Visit {verification_url} and enter code: {user_code}")
        print("Or open this URL and complete the Google OAuth flow...")
        
        for i in range(60):
            time.sleep(2)
            token_response = await client.get(
                f"{base_url}/auth/device/token",
                params={"device_code": device_code}
            )
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                set_auth_token(access_token)
                print(f"\n✅ Logged in successfully!")
                return True
            
            if token_response.status_code == 400:
                continue
        
        print("\n❌ Login timed out. Please try again.")
        return False


def logout():
    config.auth_token = None
    save_config(config)
    print("Logged out successfully.")
