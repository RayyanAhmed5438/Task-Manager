# 🗂️ Task Manager – Offline-First with Cloud Sync
#----------------------------------------------------

A desktop Task & To-Do Manager built using Python and PyQt5, featuring an offline-first design with optional Firebase (Google Cloud Firestore) synchronization.

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

-> Fully functional offline

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

-> Note:
    ⚠️ The app runs safely without Firebase in offline mode.

## 🔐 Security Note

-> firebase_key.json is not included for security

-> Users/judges generate their own key

-> If missing, the app runs offline without crashing

## 🧠 Offline-First Design

-> All actions saved locally first

-> Cloud sync is non-blocking

-> Internet loss does not affect usability

-> Pending changes sync automatically on reconnection

👤 Author

**Rayyan Ahmed**
Hackathon Project – Desktop Application Development