import json
import uuid
from pathlib import Path
import threading
from flask import Flask, request, jsonify
import requests
import tkinter as tk
from tkinter import ttk, messagebox



class Storage:
    def __init__(self, filename="media.json"):
        self.filename = Path(filename)
        if not self.filename.exists():
            self.filename.write_text(json.dumps({}, indent=4))
        self._load()

    def _load(self):
        with self.filename.open("r") as f:
            self.data = json.load(f)

    def _save(self):
        with self.filename.open("w") as f:
            json.dump(self.data, f, indent=4)

    def get_all(self):
        return list(self.data.values())

    def get_item(self, item_id):
        return self.data.get(item_id)

    def get_by_category(self, category):
        return [
            m for m in self.data.values()
            if m["category"].lower() == category.lower()
        ]

    def get_by_name(self, name):
        for m in self.data.values():
            if m["name"].lower() == name.lower():
                return m
        return None

    def add_item(self, obj):
        item_id = str(uuid.uuid4())
        obj["id"] = item_id
        self.data[item_id] = obj
        self._save()
        return obj

    def delete_item(self, item_id):
        if item_id in self.data:
            del self.data[item_id]
            self._save()
            return True
        return False


# Backend using flask

app = Flask(__name__)
storage = Storage()


@app.route("/media", methods=["GET"])
def api_get_all():
    return jsonify(storage.get_all())


@app.route("/media/category/<category>", methods=["GET"])
def api_get_category(category):
    return jsonify(storage.get_by_category(category))


@app.route("/media/search", methods=["GET"])
def api_search():
    name = request.args.get("name", "")
    result = storage.get_by_name(name)
    return jsonify(result if result else {})


@app.route("/media/<item_id>", methods=["GET"])
def api_get_item(item_id):
    item = storage.get_item(item_id)
    return jsonify(item if item else {})


@app.route("/media", methods=["POST"])
def api_add():
    data = request.json
    required = {"name", "author", "date", "category"}

    if not data or not required.issubset(data.keys()):
        return jsonify({"error": "missing fields"}), 400

    new_item = storage.add_item(data)
    return jsonify(new_item), 201


@app.route("/media/<item_id>", methods=["DELETE"])
def api_delete(item_id):
    ok = storage.delete_item(item_id)
    return jsonify({"success": ok}), (200 if ok else 404)



# Frontend using tkinter



API_URL = "http://127.0.0.1:5000"


class LibraryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital - Library")
        self.root.configure(bg="#2A2A2A")

        # Top control bar


        frame = tk.Frame(root, bg="#2A2A2A")
        frame.pack(pady=10)

        tk.Label(frame, text="Category:", bg="#2A2A2A", fg="white").grid(row=0, column=0)

        self.category = ttk.Combobox(
            frame, values=["All", "Books", "Movies", "Magazines"], width=15
        )
        self.category.current(0)
        self.category.grid(row=0, column=1)

        tk.Button(frame, text="Load",
          command=self.load_category,
          bg="#3a3a3a", fg="white", activebackground="#505050").grid(row=0, column=2, padx=5)    

        tk.Label(frame, text="Name:", bg="#2A2A2A", fg="white").grid(row=0, column=3)
        self.search_entry = tk.Entry(frame, width=20)
        self.search_entry.grid(row=0, column=4)

        tk.Button(frame, text="Search", command=self.search_media,
        bg="#3a3a3a", fg="white", activebackground="#505050").grid(row=0, column=5, padx=5)


        #style

        style = ttk.Style()
        style.theme_use("clam")


        style.configure("Treeview",
                background="#000000",
                foreground="white",
                rowheight=25,
                fieldbackground="#0f0e0e",
                bordercolor="#1e1e1e",
                borderwidth=0)


        style.configure("Treeview.Heading",
                background="#3a3a3a",
                foreground="white",
                relief="flat")


        style.layout("Treeview",
             [('Treeview.treearea', {'sticky': 'nswe'})])
        



         # Table

    
        cols = ("name", "author", "date", "category")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=180)
        self.tree.pack(padx=20, pady=20)
        self.tree.bind("<Double-1>", self.show_details)



        # Bottom Buttons


        bottom = tk.Frame(root,bg="#2A2A2A")
        bottom.pack(pady=10)

        tk.Button(bottom, text="All", width=10, command=self.load_all, bg="#3a3a3a", fg="white", activebackground="#505050").pack(side=tk.LEFT, padx=5)
        tk.Button(bottom, text="New", width=10, command=self.new_media, bg="#3a3a3a", fg="white", activebackground="#505050").pack(side=tk.LEFT, padx=5)
        tk.Button(bottom, text="Delete", width=10, command=self.delete_selected, bg="#3a3a3a", fg="white", activebackground="#505050").pack(side=tk.LEFT, padx=5)

        self.load_all()

    # Helpers

    def clear_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def insert_rows(self, data):
        self.clear_table()
        for item in data:
            self.tree.insert("", "end", values=(
                item["name"],
                item["author"],
                item["date"],
                item["category"]
              ),
                 tags=(item["id"],)
            )

    # Functions

    def load_all(self):
        data = requests.get(f"{API_URL}/media").json()
        self.insert_rows(data)

    def load_category(self):
        cat = self.category.get()
        if cat == "All":
            self.load_all()
            return
        data = requests.get(f"{API_URL}/media/category/{cat}").json()
        self.insert_rows(data)

    def search_media(self):
        name = self.search_entry.get().strip()
        if not name:
            messagebox.showinfo("Note", "Please enter a name.")
            return
        result = requests.get(f"{API_URL}/media/search?name={name}").json()
        if result:
            self.insert_rows([result])
        else:
            messagebox.showinfo("Info", "No media found.")

    def show_details(self, event):
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item)["values"]
        name, author, date, category = values
        _id = self.tree.item(item)["tags"][0]

        message = f"""
Name: {name}
Autor: {author}
Date: {date}
Category: {category}
"""
        messagebox.showinfo("Details", message)

    def new_media(self):
        win = tk.Toplevel()
        win.title("New Medium")

        entries = {}
        fields = ["Name", "Author", "Date (DD-MM-YYYY)", "Category"]

        for i, field in enumerate(fields):
            tk.Label(win, text=field).grid(row=i, column=0, padx=5, pady=5)
            e = tk.Entry(win, width=30)
            e.grid(row=i, column=1)
            entries[field] = e

        def save_new():
            data = {
                "name": entries["Name"].get(),
                "author": entries["Author"].get(),
                "date": entries["Date (DD-MM-YYYY)"].get(),
                "category": entries["Category"].get(),
            }
            if not all(data.values()):
                messagebox.showerror("Error", "Fill in all fields!")
                return
            requests.post(f"{API_URL}/media", json=data)
            self.load_all()
            win.destroy()

        tk.Button(win, text="Save", command=save_new).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def delete_selected(self):
        item = self.tree.focus()
        if not item:
            messagebox.showwarning("Warning", "Please select an item.")
            return

        _id = self.tree.item(item)["tags"][0]


        if messagebox.askyesno("Delete", "You want to delete this?"):
            requests.delete(f"{API_URL}/media/{_id}")
            self.load_all()



# To start Flask + Tkinter GUI

def start_flask():
    app.run(port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    
    # Start backend in separate thread
    threading.Thread(target=start_flask, daemon=True).start()

    # Start GUI
    root = tk.Tk()
    gui = LibraryGUI(root)
    root.mainloop()
