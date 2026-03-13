import requests
import json

token = "rnd_3adpHxXmImmgOYVeM7TyBl9sTGBo"
service_id = "srv-d6nkp1nkijhs739mp1k0"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def trigger_deploy():
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    response = requests.post(url, headers=headers, json={"clearCache": "clear"})
    if response.status_code in [200, 201]:
        print(f"Deployment triggered successfully!")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    trigger_deploy()
