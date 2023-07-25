import os
import time
import threading
import tkinter as tk
import tkinter.messagebox
import tkinter.simpledialog
from tkinter import ttk, Menu
from subprocess import Popen, PIPE
import subprocess

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Searcher")

        # Create widgets
        self.entry = tk.Entry(self)
        self.button = tk.Button(self, text="Search", command=self.search)
        self.update_button = tk.Button(self, text="Update Index", command=self.update_index)
        self.tree = ttk.Treeview(self, columns=("filename", "path", "time"), show="headings")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)

        # Configure treeview
        self.tree.heading("filename", text="Filename", command=lambda: self.sort_by("filename", False))
        self.tree.heading("path", text="Full Path", command=lambda: self.sort_by("path", False))
        self.tree.heading("time", text="Time Modified", command=lambda: self.sort_by("time", False))
        self.tree.column("filename", stretch=tk.YES, width=200)
        self.tree.column("path", stretch=tk.YES, width=300)
        self.tree.column("time", stretch=tk.YES, width=200)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Create right click context menu
        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="Open Directory", command=self.open_directory)
        self.menu.add_command(label="Open File", command=self.open_file)
        self.tree.bind("<Button-3>", self.show_menu)

        # Bind Return key to search function
        self.entry.bind("<Return>", self.search)

        # Layout
        self.entry.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.button.grid(row=1, column=0)
        self.update_button.grid(row=1, column=1)
        self.tree.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.scrollbar.grid(row=2, column=2, sticky='ns')

        # Configure column weights for resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        # Create progress bar
        self.progress = ttk.Progressbar(self, mode='indeterminate')

    def search(self, event=None):
        # Clear old results
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Get the filename from the entry
        filename = self.entry.get()

        # Call locate command
        process = Popen(['locate', '-b', filename], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

        # Insert each result into the treeview
        for line in stdout.decode().split("\n"):
            if line and os.path.exists(line):
                timestamp = os.path.getmtime(line)
                readable_time = time.ctime(timestamp)
                self.tree.insert("", "end", values=(line.split("/")[-1], line, readable_time))

    def update_index(self):
        password = tkinter.simpledialog.askstring("Password", "Enter password:", show='*')
        command = ['sudo', '-S', 'updatedb']

        # Start the progress bar
        self.progress.start()
        self.progress.grid(row=3, column=0, columnspan=2, sticky='ew')

        # Start a new thread to run updatedb
        threading.Thread(target=self.run_updatedb, args=(command, password), daemon=True).start()

    def run_updatedb(self, command, password):
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdin.write(password.encode())
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            tkinter.messagebox.showerror("Error", "Failed to update index. Error: " + stderr.decode())
        else:
            tkinter.messagebox.showinfo("Success", "Index updated successfully.")

        # Stop the progress bar
        self.progress.stop()
        self.progress.grid_forget()

    def sort_by(self, col, descending):
        # Sort the treeview by the given column
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            self.tree.move(item[1], '', indx)

        # Switch the heading so that it will sort in the opposite direction
        self.tree.heading(col, command=lambda col=col: self.sort_by(col, int(not descending)))

    def show_menu(self, event):
        # Select row under mouse
        self.tree.selection_set(self.tree.identify_row(event.y))
        # Show right click context menu
        self.menu.post(event.x_root, event.y_root)


    def open_directory(self):
        # Get selected item
        selected_items = self.tree.selection()
        if len(selected_items) > 0:
            item = selected_items[0]
            # Get file path
            path = self.tree.item(item)['values'][1]
            # Check if the path is a directory
            if os.path.isdir(path):
                # Open the directory
                subprocess.run(['nautilus', path])
            else:
                # Open the directory containing the file and select the file
                subprocess.run(['nautilus', '--select', path])
        else:
            tkinter.messagebox.showinfo("No selection", "Please select an item first.")

    def open_file(self):
        # Get selected item
        selected_items = self.tree.selection()
        if len(selected_items) > 0:
            item = selected_items[0]
            # Get file path
            path = self.tree.item(item)['values'][1]
            # Open the file
            subprocess.run(['nautilus', '--select', path])
        else:
            tkinter.messagebox.showinfo("No selection", "Please select an item first.")


if __name__ == "__main__":
    app = Application()
    app.mainloop()
