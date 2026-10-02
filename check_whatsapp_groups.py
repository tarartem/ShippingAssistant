import requests
import json
import config

def main():
    print(f"Connecting to WhatsApp Bridge at {config.WHATSAPP_BRIDGE_URL}...")
    try:
        res = requests.get(f"{config.WHATSAPP_BRIDGE_URL}/groups", timeout=10)
        if res.status_code == 200:
            groups = res.json().get("groups", [])
            if not groups:
                print("No WhatsApp groups found for this account. Create a group first with your family!")
                return
            
            print("\n📋 Found WhatsApp Groups:")
            print("-" * 65)
            for g in groups:
                print(f"Group Name: {g['subject']}")
                print(f"Group ID:   {g['id']}")
                print(f"Members:    {g['participantsCount']}")
                print("-" * 65)
            
            print("\n💡 Copy the Group ID of your Family Group and set it in your .env file:")
            print("WHATSAPP_TARGET_GROUP=<GroupIDHere>")
        else:
            print(f"WhatsApp Bridge returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Could not connect to WhatsApp Bridge: {e}")
        print("Make sure the WhatsApp bridge is running (in whatsapp_bridge: node server.js)")

if __name__ == "__main__":
    main()
