import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv
from modules.vpn_functions import initialize_db, create_user, delete_client, list_clients

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(',')))
ADMIN_NAMES = os.getenv("ADMIN_NAMES").split(",")
ALL_ADMINS = ADMIN_IDS + [SUPERADMIN_ID]

# Create a mapping of admin IDs to their names
ADMINS = {SUPERADMIN_ID: "Superadmin"}
ADMINS.update({admin_id: admin_name.strip() for admin_id, admin_name in zip(ADMIN_IDS, ADMIN_NAMES)})

# Conversation states
GET_CLIENT_NAME, DELETE_CLIENT_NAME = range(2)

# Utility functions to manage admin access
def is_superadmin(user_id):
    return user_id == SUPERADMIN_ID

def is_admin(user_id):
    return user_id in ALL_ADMINS

def restricted_access(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            update.message.reply_text("🚫 Unauthorized access.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

# Start command with inline buttons
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("🚫 Unauthorized access.")
        return
    
    # Inline keyboard with available actions
    keyboard = [
        [InlineKeyboardButton("➕ Create Client", callback_data='create')],
        [InlineKeyboardButton("🗑️ Delete Client", callback_data='delete')],
        [InlineKeyboardButton("📋 List Clients", callback_data='list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome to OpenVPN Bot! Choose an action:", reply_markup=reply_markup)

# Inline button handler
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    # Determine which button was pressed and initiate the appropriate conversation state
    if query.data == 'create':
        query.edit_message_text(text="Please enter a name for the new client:")
        return GET_CLIENT_NAME
    elif query.data == 'delete':
        query.edit_message_text(text="Please enter the name of the client you want to delete:")
        return DELETE_CLIENT_NAME
    elif query.data == 'list':
        list_clients(update, context, ADMINS)  # Pass ADMINS to the list_clients function
        return ConversationHandler.END  # End the conversation after listing clients

# Handlers for creating and deleting clients
def create_user_handler(update: Update, context: CallbackContext):
    if create_user(update, context, bot=context.bot):
        return ConversationHandler.END
    return GET_CLIENT_NAME

def delete_client_handler(update: Update, context: CallbackContext):
    if delete_client(update, context):  # Perform the delete operation
        return ConversationHandler.END  # End the conversation
    else:
        update.message.reply_text("❌ Unable to delete the client. Make sure the name is correct and try again.")
        return ConversationHandler.END

# Main function to initialize and run the bot
def main():
    initialize_db()  # Ensure the database is initialized
    
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Restrict available commands to just `/start`
    updater.bot.set_my_commands([
        ('start', 'Show the main menu')
    ])

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            GET_CLIENT_NAME: [MessageHandler(Filters.text & ~Filters.command, create_user_handler)],
            DELETE_CLIENT_NAME: [MessageHandler(Filters.text & ~Filters.command, delete_client_handler)]
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
