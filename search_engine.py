import os
import re
import jwt
import requests
import getpass
import pickle
import datetime


class SearchEngine:
    def __init__(self):
        self.drives = []
        self.selected_drive = None

        self.menu_level = 0
        self.menu_selected = 0

        self.logged_in = False
        self.current_user = None

        self.history = None
        self.file_index = None

        self.results = []
        self.matches = 0
        self.records = 0

        self.menu = {
            1: {"name": "Drives", "function": self.drives_option, "options": ["Detect Drives", "View Drives", "Back"]},
            2: {"name": "Search", "function": self.search_option, "options": ["Select Drive", "Load Index", "Build Index", "Search", "Back"]},
            3: {"name": "History", "function": self.history_option, "options": ["View History", "Delete Record", "Back"]},
            4: {"name": "Error Logger", "function": self.error_option, "options": ["View All Error Logs", "View Specific Error Log", "Update Status", "Back"]},
            5: {"name": "Transaction Module", "function": self.transaction_option, "options": ["Get All Transactions", "Get All Transactions Between Dates", "Back"]},
            6: {"name": "User Configuration", "function": self.user_option, "options": ["Create User", "Edit User", "View User", "Back"]},
            8: {"name": "Notification Configurations"},
            9: {"name": "Analytics"},
            10: {"name": "Logout", "function": self.logout},
            11: {"name": "Quit", "function": quit}
        }

    def post_error(self, action, message):
        data = {
            "timestamp": str(datetime.datetime.now()),
            "user": self.current_user["username"],
            "action": action,
            "message": message,
            "status": "unresolved"
        }
        response = requests.post(
            'http://localhost:3000/errors', json=data)

        self.post_transaction("Post Error")

    def post_transaction(self, action):
        data = {
            "timestamp": str(datetime.datetime.now()),
            "user": self.current_user["username"],
            "action": action
        }
        response = requests.post(
            'http://localhost:3000/transactions', json=data)

    def login(self):
        try:
            username = input("Enter username: ")
            password = getpass.getpass("Enter password: ")

            data = {"username": username, "password": password}
            token = jwt.encode(data, 'secret')

            response = requests.get(
                'http://localhost:3001/users', params={'token': token})

            if response.status_code == 200:
                d = response.json()
                data["permissions"] = d.get("permissions")
                data["id"] = d.get("id")
                self.current_user = data
                self.logged_in = True
                input("\nLogin successful. Press ENTER to continue ...")
                self.post_transaction("Login")
            else:
                print("\n" + response.text)
                input("Press ENTER to continue...")
        except Exception as e:
            self.post_error("login", str(e))

    def logout(self):
        self.post_transaction("Logout")
        self.logged_in = False
        self.current_user = None

    def drives_option(self, option):
        try:
            if option == 1:
                self.detect_drive()
                input("Drive detection completed. Press ENTER to continue ...")

            elif option == 2:
                self.view_drives()
                input("\nPress ENTER to continue ...")
        except Exception as e:
            self.post_error("drives menu", str(e))

    def detect_drive(self):
        self.drives = re.findall(
            r"[A-Z]+:.*$", os.popen("mountvol /").read(), re.MULTILINE)

    def view_drives(self):
        if self.drives:
            print(
                f"Available Drives: {', '.join(sorted([s[:-2] for s in self.drives]))}")
        else:
            print("No drives detected.")

    def search_option(self, choice):
        try:
            if choice == 1:
                self.select_drive()
            elif choice == 2:
                self.load_index()
            elif choice == 3:
                self.build_index()
            elif choice == 4:
                self.search()
        except Exception as e:
            self.post_error("search menu", str(e))

    def select_drive(self):
        drive = input("Enter drive: ")
        self.file_index = None
        self.history = None
        if f"{drive}:\\" in self.drives:
            self.selected_drive = drive
            input("\nDrive selected successfully. Press ENTER to continue...")
        else:
            input("\nInvalid drive. Try Drives menu option. Press ENTER to continue...")

    def load_index(self):
        if self.selected_drive is None:
            input("You must select a drive first. Press ENTER to continue...")
            return

        try:
            with open(f'{self.selected_drive}.pkl', 'rb') as f:
                self.file_index = pickle.load(f)
                input("Index loaded successfully. Press ENTER to continue...")

        except Exception as e:
            print("\nIndex not found. Index needs to be built.")
            self.file_index = []
            self.build_index()

    def build_index(self):
        if self.selected_drive is None:
            input("You must select a drive first. Press ENTER to continue...")
            return

        print("Building index. It may take a while.")
        root_path = self.selected_drive + ":\\"

        # !WARNING Remove next line for production
        root_path = 'C:\\Users\\msoum\\Desktop'

        self.file_index = [(root, files)
                           for root, dirs, files in os.walk(root_path) if files]

        with open(f'{self.selected_drive}.pkl', 'wb') as f:
            pickle.dump(self.file_index, f)

        input("Index build successfully. Press ENTER to continue...")

    def search(self):
        if self.selected_drive is None:
            input("You must select a drive first. Press ENTER to continue...")
            return

        if self.file_index is None:
            input("You must load or build file index. Press ENTER to continue...")
            return

        self.results = []
        self.matches = 0
        self.records = 0

        query = input("Enter query: ")

        if self.history is None:
            print("\nHistory not found. Loading history from server.")
            response = requests.get(
                'http://localhost:3000/history')
            self.history = response.json()

        found = False
        for item in self.history:
            if item["query"] == query:
                self.results = item["results"]
                self.records = item["records"]
                self.matches = item["matches"]
                print("\nQuery found in history.")
                found = True
                break

        if not found:
            for root, files in self.file_index:
                for file in files:
                    self.records += 1
                    if query.lower() in file.lower():
                        self.results.append(root + '\\' + file)
                        self.matches += 1

            data = {"drive": self.selected_drive, "query": query,
                    "results": self.results, "records": self.records, "matches": self.matches}

            self.history.append(data)
            response = requests.post(
                'http://localhost:3000/history/', json=data)

        print(f"{self.matches} matches found out of {self.records} records.")

        if self.matches > 0:
            n = int(input("Enter number of records to be shown: "))
            n = min(n, self.matches)
            for i in range(n):
                print(self.results[i])

        input("\nPress ENTER to continue...")

    def history_option(self, option):
        try:
            if option == 1:
                self.view_history()
            elif option == 2:
                self.delete_record()
        except Exception as e:
            self.post_error("history menu", str(e))

    def view_history(self):
        if self.history is None:
            print("\nHistory not found. Loading history from server.")
            response = requests.get(
                'http://localhost:3000/history')
            self.history = response.json()

        if len(self.history) == 0:
            print("\nHistory is empty. Press ENTER to continue")
            return

        for item in self.history:
            print(f"ID: {item['id']}")
            print(f"Query: {item['query']}")
            print(f"Records: {item['records']}")
            print(f"Matches: {item['matches']}")
            print()

        input("\nPress ENTER to continue...")

    def delete_record(self):
        id = int(input("Enter ID of history to be deleted: "))
        response = requests.delete(f'http://localhost:3000/history/{id}')

        if response.status_code == 200:
            input("\nHistory deleted successfully. Press ENTER to continue...")
        else:
            input("\nHistory deletion unsuccessful. Press ENTER to continue...")

    def error_option(self, option):
        try:
            if option == 1:
                self.view_all_errors()
            elif option == 2:
                self.view_error()
            elif option == 3:
                self.update_error()
        except Exception as e:
            self.post_error("error menu", str(e))

    def view_all_errors(self):
        response = requests.get('http://localhost:3000/errors')
        errors = response.json()
        for error in errors:
            print(f"\nID: {error['id']}")
            print(f"Timestamp: {error['timestamp']}")
            print(f"User: {error['user']}")
            print(f"Action: {error['action']}")
            print(f"Message: {error['message']}")
            print(f"Status: {error['status']}")

        input("\nPress ENTER to continue...")

    def view_error(self):
        id = int(input("Enter ID of error to be viewed: "))
        response = requests.get(f'http://localhost:3000/errors/{id}')
        error = response.json()
        print(f"\nID: {error['id']}")
        print(f"Timestamp: {error['timestamp']}")
        print(f"User: {error['user']}")
        print(f"Action: {error['action']}")
        print(f"Message: {error['message']}")
        print(f"Message: {error['status']}")

        input("\nPress ENTER to continue...")

    def update_error(self):
        id = int(input("Enter ID of error to be updated: "))
        status = input("Enter new status: ")
        data = requests.get(
            f'http://localhost:3000/errors/{id}').json()
        data["status"] = status
        response = requests.put(
            f'http://localhost:3000/errors/{id}', json=data)

        if response.status_code == 200:
            input("\nError updated successfully. Press ENTER to continue...")
        else:
            input("\nError update unsuccessful. Press ENTER to continue...")

    def transaction_option(self, option):
        try:
            if option == 1:
                self.get_all_transactions()
            elif option == 2:
                self.get_transactions_between_dates()
        except Exception as e:
            self.post_error("transaction menu", str(e))

    def get_all_transactions(self):
        response = requests.get('http://localhost:3000/transactions')
        transactions = response.json()
        for transaction in transactions:
            print(f"\nID: {transaction['id']}")
            print(f"Timestamp: {transaction['timestamp']}")
            print(f"User: {transaction['user']}")
            print(f"Action: {transaction['action']}")

        input("\nPress ENTER to continue...")

    def get_transactions_between_dates(self):
        start_date = datetime.datetime.strptime(
            input("Enter start date (YYYY-MM-DD): "), "%Y-%m-%d")
        end_date = datetime.datetime.strptime(
            input("Enter end date (YYYY-MM-DD): "), "%Y-%m-%d")
        response = requests.get(
            f'http://localhost:3000/transactions')
        transactions = response.json()
        for transaction in transactions:
            date = datetime.datetime.strptime(
                transaction["timestamp"][:10], "%Y-%m-%d")
            if start_date <= date <= end_date:
                print(f"\nID: {transaction['id']}")
                print(f"Timestamp: {transaction['timestamp']}")
                print(f"User: {transaction['user']}")
                print(f"Action: {transaction['action']}")

        input("\nPress ENTER to continue...")

    def user_option(self, option):
        try:
            if option == 1:
                self.create_user()
            elif option == 2:
                self.edit_user()
            elif option == 3:
                self.view_user()
        except Exception as e:
            self.post_error("user menu", str(e))

    def create_user(self):
        username = input("\nEnter username: ")
        password = getpass.getpass("Enter password: ")
        search = input("Enter search permissions [Y/N]: ")
        delete = input("Enter delete permissions [Y/N]: ")
        drives = input("Enter drives user can access (space separated): ")

        data = {"username": username, "password": password, "permissions": {"search": search.strip().lower() == 'y',
                "delete": delete.strip().lower() == 'y', "drives": drives.strip().upper().split(' ')}}
        token = jwt.encode(data, 'secret')

        response = requests.post(
            'http://localhost:3001/users', params={'token': token})

        if response.status_code == 200:
            input("\nUser created successfully. Press ENTER to continue ...")
        else:
            print("\n" + response.text)
            input("Press ENTER to continue...")

    def edit_user(self):
        username = input("\nEnter username: ")
        password = getpass.getpass("Enter password: ")
        search = input("Enter search permissions [Y/N]: ")
        delete = input("Enter delete permissions [Y/N]: ")
        drives = input("Enter drives user can access (space separated): ")

        data = {"id": self.current_user.get("id"), "username": username, "password": password, "permissions": {"search": search.strip().lower() == 'y',
                "delete": delete.strip().lower() == 'y', "drives": drives.strip().upper().split(' ')}}
        token = jwt.encode(data, 'secret')

        response = requests.put(
            'http://localhost:3001/users', params={'token': token})

        if response.status_code == 200:
            input("\nUser edited successfully. Press ENTER to continue ...")
        else:
            print("\n" + response.text)
            input("Press ENTER to continue...")

    def view_user(self):
        print("\nUsername: " + self.current_user["username"])
        print("Password: " + self.current_user["password"])
        print("Permissions:-")
        for key, value in self.current_user["permissions"].items():
            print(f"{key.title()}: {value}")

        input("\nPress ENTER to continue...")

    def run(self):
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{'#' * 49}\n{'Search Engine':^49}\n{'#' * 49}")

            if not self.logged_in:
                print("You must be logged in to use the Search Engine.\n")
                self.login()
                continue

            if self.menu_level == 0:
                for key, value in self.menu.items():
                    print(f"{key}. {value['name']}")

                self.menu_selected = int(input("Enter choice: "))
                print()

                self.menu_level = 1

            elif self.menu_selected not in self.menu:
                return

            elif "options" in self.menu[self.menu_selected]:
                for index, option in enumerate(self.menu[self.menu_selected]["options"]):
                    print(f"{index + 1}. {option}")

                choice = int(input("Enter choice: "))
                print()

                if choice < len(self.menu[self.menu_selected]["options"]):
                    self.menu[self.menu_selected]["function"](choice)
                else:
                    self.menu_level = 0
                    self.menu_selected = 0

            else:
                self.menu[self.menu_selected]["function"]()
                self.menu_level = 0
                self.menu_selected = 0


if __name__ == "__main__":
    obj = SearchEngine()
    obj.run()
