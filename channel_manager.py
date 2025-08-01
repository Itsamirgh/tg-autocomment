#!/usr/bin/env python3
import json
import os
import re

FILENAME = "config.json"

def load_cfg():
    if not os.path.exists(FILENAME):
        print(f"Error: {FILENAME} not found.")
        exit(1)
    return json.load(open(FILENAME, "r", encoding="utf-8"))

def save_cfg(cfg):
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def list_channels(channels):
    if not channels:
        print("No channels configured.")
    else:
        print("Configured channels:")
        for i, (ch, cfg_val) in enumerate(channels.items(), 1):
            if isinstance(cfg_val, dict):
                msgs = cfg_val.get("messages", [])
                freq = cfg_val.get("frequency", 1)
                preview = " ||| ".join(m.replace("\n", " ⏎ ") for m in msgs)
                print(f"  {i}. {ch} → [every {freq}th] {preview}")
            else:
                print(f"  {i}. {ch} → {cfg_val}")

def read_multiline_numbered(prompt):
    print(prompt)
    print("(Enter lines; start each segment with '1.' '2.' etc; finish all with ',' on an empty line)")
    lines = []
    while True:
        line = input()
        if line.strip() == ",":
            break
        lines.append(line)
    segments = []
    current = []
    for line in lines:
        m = re.match(r"^(\d+)\.(.*)$", line)
        if m:
            if current:
                segments.append("\n".join(current).strip())
            current = [m.group(2).strip()]
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current).strip())
    return segments

def add_channel(channels):
    ch = input("Enter channel username (no @): ").strip()
    if not ch or ch in channels:
        print("❌ Invalid or duplicate username.")
        return
    mode = input("Single message or numbered segments? (s/m): ").strip().lower()
    if mode == "m":
        messages = read_multiline_numbered("Enter numbered comment segments:")
        freq = int(input("Frequency (every Nth post): ").strip() or "1")
        channels[ch] = {"messages": messages, "frequency": freq}
    else:
        msg = input("Enter single comment text: ").strip()
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
    if ch not in channels:
        print("❌ Channel not found.")
        return
    cfg_val = channels[ch]
    if isinstance(cfg_val, dict):
        print("Current segments:")
        for idx, m in enumerate(cfg_val["messages"], 1):
            print(f"  {idx}. {m}")
        messages = read_multiline_numbered("Enter new numbered comment segments:")
        freq = int(input(f"Frequency [{cfg_val['frequency']}]: ").strip() or cfg_val['frequency'])
        channels[ch] = {"messages": messages, "frequency": freq}
    else:
        print(f"Current message: {cfg_val}")
        msg = input("Enter new comment text: ").strip()
        channels[ch] = msg
    print("✅ Channel updated.")

def main():
    cfg = load_cfg()
    channels = cfg.get("channels", {})
    while True:
        print("\nMenu:")
        print(" 1) List channels")
        print(" 2) Add channel")
        print(" 3) Delete channel")
        print(" 4) Edit channel")
        print(" 5) Save & Exit")
        choice = input("Choice [1-5]: ").strip()
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
            print("✅ Saved to config.json. Exiting.")
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
