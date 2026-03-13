import requests
import json

token = "rnd_3adpHxXmImmgOYVeM7TyBl9sTGBo"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

def check_render():
    response = requests.get("https://api.render.com/v1/services?limit=20", headers=headers)
    if response.status_code == 200:
        services = response.json()
        for s in services:
            svc = s['service']
            print(f"Service: {svc['name']} ({svc['id']})")
            # Get latest deploy
            deploy_resp = requests.get(f"https://api.render.com/v1/services/{svc['id']}/deploys?limit=1", headers=headers)
            if deploy_resp.status_code == 200:
                deploys = deploy_resp.json()
                if deploys:
                    d = deploys[0]['deploy']
                    print(f"  Latest Deploy Status: {d['status']} - Created At: {d['createdAt']}")
                    if d['status'] == 'live':
                        print(f"  LIVE!")
                    else:
                        print(f"  DEPLOYING/FAILED/STALLED")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_render()
