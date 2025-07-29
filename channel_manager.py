#!/usr/bin/env python3
import json
import os

FILENAME = "config.json"

def load_cfg():
    if not os.path.exists(FILENAME):
        print(f"Error: {FILENAME} not found.")
        exit(1)
    with open(FILENAME, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cfg(cfg):
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def list_channels(channels):
    if not channels:
        print("No channels configured.")
    else:
        print("Configured channels:")
        for i, (ch, msg) in enumerate(channels.items(), 1):
            preview = msg.replace("\n", " ⏎ ")
            print(f"  {i}. {ch} → {preview}")

def read_multiline(prompt):
    print(prompt)
    print("(Enter lines; to finish, enter a single comma ',' on an empty line)")
    lines = []
    while True:
        line = input()
        if line.strip() == ",":
            break
        lines.append(line)
    return "\n".join(lines)

def add_channel(channels):
    ch = input("Enter channel username (no @): ").strip()
    if not ch:
        print("Username cannot be empty.")
        return
    if ch in channels:
        print("⚠️ This channel is already in the list.")
        return
    msg = read_multiline("Enter comment text for channel:")
    if not msg:
        print("Comment text cannot be empty.")
        return
    channels[ch] = msg
    print("✅ Channel added.")

def delete_channel(channels):
    ch = input("Enter channel username to delete: ").strip()
    if ch in channels:
        del channels[ch]
        print("✅ Channel removed.")
    else:
        print("❌ Channel not found.")

def edit_channel(channels):
    ch = input("Enter channel username to edit: ").strip()
    if ch in channels:
        print("Current message:")
        print(channels[ch])
        msg = read_multiline("Enter new comment text for channel:")
        if msg:
            channels[ch] = msg
            print("✅ Message updated.")
        else:
            print("No changes made.")
    else:
        print("❌ Channel not found.")

def main():
    cfg = load_cfg()
    channels = cfg.get("channels", {})

    while True:
        print("\nMenu:")
        print(" 1) List channels")
        print(" 2) Add channel")
        print(" 3) Delete channel")
        print(" 4) Edit channel message")
        print(" 5) Save & Exit")
        choice = input("Your choice [1-5]: ").strip()

        if choice == "1":
            list_channels(channels)
        elif choice == "2":
            add_channel(channels)
        elif choice == "3":
            delete_channel(channels)
        elif choice == "4":
            edit_channel(channels)
        elif choice == "5":
            cfg["channels"] = channels
            save_cfg(cfg)
            print("✅ Changes saved to config.json. Exiting.")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
