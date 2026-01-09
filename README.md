# 🗂️ Task Manager – Offline-First with Cloud Sync
#----------------------------------------------------

A desktop Task & To-Do Manager built using Python and PyQt5, featuring an offline-first design with Firebase (Google Cloud Firestore) synchronization.

Designed for a hackathon with focus on usability, reliability, and real-world behavior.

##  🚀 Features
✅ Core

-> Add, view, edit, delete tasks

-> Deadlines with remaining-day calculation

-> Task completion & prioritization

-> Separate Tasks and To-Dos

-> Persistent local storage using JSON

## ☁️ Cloud Sync (Google Technology)

-> Uses Firebase Firestore

-> Fully functional offline without it

-> Auto-syncs when internet is available 

-> Sync status indicator:

   -> Offline

   -> Syncing

   -> Synced

## 🖥️ UI

-> Built with PyQt5

-> Scrollable views

-> Visual deadline alerts (overdue, due soon, completed)

-> Clean, responsive layout with emoji-based controls

## 🛠️ Tech Stack

-> Python

-> PyQt5

-> Firebase Firestore (Google Cloud)

-> Firebase Admin SDK

-> JSON (local storage)

## 📂 Project Structure

Task Manager/
├── main.py
├── requirements.txt
├── tasks.json
├── todos.json
├── README.md
└── assets/
    ├── bg.png
    └── digit.ttf

## ⚙️ How to Run

pip install -r requirements.txt
python main.py

## ☁️ Firebase Setup

-> Create a Firebase project

-> Enable Cloud Firestore

-> Generate a Service Account key

-> Save it as "firebase_key.json"

-> Place it in the project root

⚠️ Firebase credentials are not included for security reasons.
To enable cloud sync, create a Firebase project and add `firebase_key.json`
in the root directory. The app works fully offline without it.

## 🔐 Security Note

-> firebase_key.json is not included for security

-> Users/judges generate their own key

-> If missing, the app runs offline without crashing

## 🧠 Offline-First Design

-> All actions saved locally first

-> Cloud sync is non-blocking

-> Internet loss does not affect usability

-> In case of sync conflict (cloud and local datas differ because of internet loss mid run or corrupt local json files)
   user get a choice to whether load data from cloud or continue with the local data depending
   upon which data is recent

👤 Author

**Rayyan Ahmed**

Hackathon Project – Desktop Application Development



