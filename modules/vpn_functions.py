import os
import sqlite3
import subprocess
from datetime import datetime
import re
from telegram import Bot

DB_FILE = "/root/openbot/openvpn_clients.db"

def initialize_db():
    """Initialize the database if it doesn't already exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        admin_id INTEGER
    )
    """)
    conn.commit()
    conn.close()

def add_client_to_db(client_name, admin_id):
    """Add a client to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO clients (name, admin_id) VALUES (?, ?)", (client_name, admin_id))
        conn.commit()
    except sqlite3.IntegrityError:
        print("Client name already exists in the database.")
    finally:
        conn.close()

def delete_client_from_db(client_name):
    """Delete a client from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE name = ?", (client_name,))
    conn.commit()
    conn.close()

def list_clients(update, context, admins):
    """List all clients, grouped by their admin."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    user_id = update.effective_user.id
    if user_id == int(os.getenv("SUPERADMIN_ID")):  # If the user is the Superadmin
        cursor.execute("SELECT name, admin_id FROM clients")
    else:
        cursor.execute("SELECT name FROM clients WHERE admin_id = ?", (user_id,))
    
    clients = [{"name": row[0], "admin_id": row[1]} for row in cursor.fetchall()] if user_id == int(os.getenv("SUPERADMIN_ID")) else [{"name": row[0]} for row in cursor.fetchall()]
    conn.close()

    if user_id == int(os.getenv("SUPERADMIN_ID")):  # Superadmin: grouped by admin
        grouped_clients = {}
        for client in clients:
            admin_name = admins.get(client['admin_id'], "Unknown Admin")
            if admin_name not in grouped_clients:
                grouped_clients[admin_name] = []
            grouped_clients[admin_name].append(client)

        # Build the formatted message
        client_list = []
        for admin_name, admin_clients in grouped_clients.items():
            client_list.append(f"👤 *{admin_name}*\n")
            client_list.extend([f"{i + 1}. `{client['name']}`" for i, client in enumerate(admin_clients)])
            client_list.append("\n- - -\n")  # Separator with a gap above and below

        final_message = "\n".join(client_list).rstrip("\n- - -\n")
    else:  # Regular admins
        final_message = "\n".join([f"{i + 1}. `{client['name']}`" for i, client in enumerate(clients)]) if clients else "📂 No clients found."

    update.callback_query.edit_message_text(f"📋 *Client List:*\n\n{final_message}", parse_mode="Markdown")

def create_user(update, context, bot: Bot):
    client_base_name = update.message.text.strip()
    admin_id = update.message.from_user.id
    if not re.match(r'^[\w-]+$', client_base_name):
        update.message.reply_text("⚠️ Invalid username format. Use only alphanumeric characters, underscores, or dashes.")
        return False

    date_suffix = datetime.now().strftime("%d-%m")
    username = f"{client_base_name}_{date_suffix}"

    try:
        process = subprocess.run(
            ["./openvpn-install.sh"],
            input=f"1\n{username}\n".encode(),
            cwd='/root/openbot',
            check=True,
            capture_output=True,
            shell=True
        )
        
        ovpn_path = f"/root/{username}.ovpn"
        if os.path.exists(ovpn_path):
            add_client_to_db(username, admin_id)
            with open(ovpn_path, 'rb') as f:
                bot.send_document(chat_id=update.message.chat_id, document=f, filename=f"{username}.ovpn")
            os.remove(ovpn_path)
        else:
            stderr_output = process.stderr.decode()
            if "The specified client CN was already found" in stderr_output:
                update.message.reply_text("❗ Client name already exists. Please choose another name.")
                return False
            else:
                update.message.reply_text("⚠️ An unexpected error occurred. Please try again.")

    except subprocess.CalledProcessError as e:
        update.message.reply_text(f"Error occurred: {e.stderr.decode()}")
        print(e.stderr.decode())

    return True

def delete_client(update, context):
    client_name = update.message.text.strip()
    try:
        process = subprocess.run(
            ["./openvpn-install.sh"],
            input=f"2\n{client_name}\n".encode(),  # Use option "2" to revoke the client
            cwd='/root/openbot',
            check=True,
            capture_output=True,
            shell=True
        )
        output = process.stdout.decode()

        if "Certificate for client" in output and "revoked" in output:
            delete_client_from_db(client_name)  # Remove from the database
            update.message.reply_text(f"✅ Client `{client_name}` has been deleted.", parse_mode="Markdown")
            return True
        else:
            print(f"Unexpected output while deleting client:\n{output}")  # Debugging: Unexpected issues
            return False
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode()
        update.message.reply_text(f"⚠️ Error occurred while deleting client:\n{error_message}")
        return False
