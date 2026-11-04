"""Run locally; never paste your bot token into chat."""
import tkinter as tk
from tkinter import ttk
import json
import urllib.request
import urllib.error
import re
from telegram_alerts import CONFIG

def valid_token(token):
 return re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{35}", token) is not None

def ask_token():
 root=tk.Tk()
 root.title("Anuraksana - Connect Telegram")
 root.resizable(False, False)
 frame=ttk.Frame(root,padding=20)
 frame.pack()
 ttk.Label(frame,text="Copy the complete NEW token from BotFather, including numbers and colon.").pack(anchor="w")
 entry=ttk.Entry(frame,width=70,show="*")
 entry.pack(fill="x",pady=10)
 status=ttk.Label(frame,text="Your token stays hidden. Do not share screenshots of BotFather's token.")
 status.pack(anchor="w")
 result=[]
 def paste():
  try:
   value=root.clipboard_get().strip()
  except tk.TclError:
   status.config(text="Clipboard has no text. Copy the token in Telegram first.")
   return
  entry.delete(0,tk.END)
  entry.insert(0,value)
  status.config(text="Pasted. Click Continue." if valid_token(value) else "Copied text is not a complete token. Copy the numbers, colon and secret together.")
 def submit():
  value=entry.get().strip()
  if not valid_token(value):
   status.config(text="Incomplete token. Copy the whole token including the numbers and colon.")
   return
  result.append(value)
  root.destroy()
 buttons=ttk.Frame(frame)
 buttons.pack(pady=(12,0))
 ttk.Button(buttons,text="Paste token",command=paste).pack(side="left",padx=5)
 ttk.Button(buttons,text="Continue",command=submit).pack(side="left",padx=5)
 ttk.Button(buttons,text="Cancel",command=root.destroy).pack(side="left",padx=5)
 root.bind("<Return>",lambda event:submit())
 entry.focus_set()
 root.mainloop()
 return result[0] if result else None

def main():
 config=json.loads(CONFIG.read_text(encoding="utf-8"))
 token=ask_token()
 if token is None:
  print("Setup cancelled. Nothing saved.");return
 if not valid_token(token):
  print("Token format is invalid. Paste only the latest token, without message text, spaces or the time (AM/PM).");return
 try:
  with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates",timeout=15) as r:
   updates=json.load(r)
  chats={str(u["message"]["chat"]["id"]):u["message"]["chat"].get("first_name","Worker") for u in updates.get("result",[]) if u.get("message",{}).get("chat",{}).get("type")=="private"}
 except urllib.error.HTTPError as error:
  messages={401:"Telegram rejected the token. Use the latest token from BotFather; revoked tokens do not work.",404:"Telegram could not find this bot token. Copy the latest token exactly.",409:"Another bot poller or webhook is active. Stop it before running setup.",429:"Telegram rate limit reached. Wait a minute and retry."}
  print(messages.get(error.code,f"Telegram returned HTTP {error.code}. Retry later."));return
 except (urllib.error.URLError, TimeoutError, OSError):
  print("Cannot connect to api.telegram.org. Check internet, firewall or proxy settings, then retry. No token was saved.");return
 except (ValueError, KeyError, TypeError):
  print("Telegram returned an unexpected response. Retry later. No token was saved.");return
 if not updates.get("ok"):
  print("Telegram did not accept the request. Check the latest bot token.");return
 if len(chats)<3:
  print(f"Found {len(chats)} private account(s); three are required. Have each worker send a fresh message to this bot, then rerun setup.");return
 print("Private chats that contacted this bot:")
 for cid,name in chats.items():print(cid,name)
 ids=[]
 for i in range(1,4):
  cid=input(f"Chat ID for WORKER-0{i}: ").strip()
  if cid not in chats or cid in ids:print("Choose three distinct IDs from the list.");return
  ids.append(cid)
 config.update(bot_token=token,workers=[dict(worker_id=f"WORKER-0{i+1}",chat_id=cid) for i,cid in enumerate(ids)])
 config["enabled"]=input("Enable automatic FD001 demo alerts to these three workers? Type YES: ").strip().upper()=="YES"
 CONFIG.write_text(json.dumps(config,indent=2),encoding="utf-8")
 print("Configuration saved locally. Restart the portal. No test message was sent.")
if __name__=="__main__":main()
