import requests
import time
import os
import getpass
import random
MIN_DELAY = 1.2
MAX_DELAY = 1.5
RESULTS_DIR = "results"
def prompt_token():
    print("🔒 Discord User Token'ınızı girin (gizli):")
    token = getpass.getpass("Token: ").strip()
    return token
def build_headers(token):
    return {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
def get_self_user_id(headers):
    r = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
    if r.status_code == 200:
        return r.json()["id"]
    return None
def get_dm_channel(user_id, headers):
    r = requests.post(
        "https://discord.com/api/v9/users/@me/channels",
        headers=headers,
        json={"recipient_id": user_id}
    )
    if r.status_code == 200:
        return r.json()["id"]
    elif r.status_code == 400:
        chans = requests.get("https://discord.com/api/v9/users/@me/channels", headers=headers).json()
        for ch in chans:
            if ch.get("type") == 1 and ch.get("recipients", [{}])[0].get("id") == user_id:
                return ch["id"]
    return None
def get_all_messages(channel_id, headers, limit=100):
    messages = []
    before = None
    while True:
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"
        if before:
            url += f"&before={before}"
        r = requests.get(url, headers=headers)
        batch = r.json() if r.status_code == 200 else []
        if not batch:
            break
        messages.extend(batch)
        before = batch[-1]["id"]
        if len(batch) < limit:
            break
    return messages
def delete_message(channel_id, message_id, headers):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
    r = requests.delete(url, headers=headers)
    return r.status_code == 204
def save_deleted_links(channel_id, deleted_messages):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{channel_id}_deleted.txt")
    with open(path, "w", encoding="utf-8") as f:
        for msg_id in deleted_messages:
            f.write(f"https://discord.com/channels/@me/{channel_id}/{msg_id}\n")
    print(f"[✓] Silinen mesajlar '{path}' dosyasına kaydedildi.")
def clean_dm_with_user(user_id, self_id, headers):
    print(f"\n[i] DM alınıyor → Kullanıcı: {user_id}")
    channel_id = get_dm_channel(user_id, headers)
    if not channel_id:
        print("[!] DM kanalı bulunamadı, atlanıyor.")
        return
    print(f"[i] Kanal ID: {channel_id}")
    messages = get_all_messages(channel_id, headers)
    print(f"[i] Toplam {len(messages)} mesaj bulundu.")
    deleted_ids = []
    for msg in messages:
        if msg.get("author", {}).get("id") == self_id:
            msg_id = msg["id"]
            if delete_message(channel_id, msg_id, headers):
                print(f"[✓] Silindi: {msg_id}")
                deleted_ids.append(msg_id)
            else:
                print(f"[!] Silinemedi: {msg_id}")
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    print(f"[✓] {len(deleted_ids)} mesaj silindi.")
    save_deleted_links(channel_id, deleted_ids)
def main():
    token = prompt_token()
    headers = build_headers(token)
    self_id = get_self_user_id(headers)
    if not self_id:
        print("[!] Token hatalı olabilir, kullanıcı alınamadı.")
        return
    print("\n💬 DM'leri silinebilir kullanıcılar listesi alınıyor...")
    chans = requests.get("https://discord.com/api/v9/users/@me/channels", headers=headers).json()
    dm_users = [(ch["recipients"][0]["username"] + "#" + ch["recipients"][0]["discriminator"], ch["recipients"][0]["id"]) for ch in chans if ch.get("type") == 1 and ch.get("recipients")]
    if not dm_users:
        print("[!] Hiç DM bulunamadı.")
        return
    print("\n📋 Aşağıdaki DM kullanıcılarından silmek istediklerini numara ile seç:")
    for i, (name, _) in enumerate(dm_users, start=1):
        print(f"{i}) {name}")
    selected = input("\nSeçilenlerin numaraları (örn: 1,3,5): ").strip()
    selected_indices = [int(i)-1 for i in selected.split(",") if i.strip().isdigit() and 0 < int(i) <= len(dm_users)]
    if not selected_indices:
        print("[!] Geçerli bir seçim yapılmadı.")
        return
    selected_ids = [dm_users[i][1] for i in selected_indices]
    for user_id in selected_ids:
        clean_dm_with_user(user_id, self_id, headers)
if __name__ == "__main__":
    main()