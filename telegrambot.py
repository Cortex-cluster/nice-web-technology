from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

BOT_TOKEN = "8280181843:AAEg8XuZbHztiVSAX6hKMjszQyy4nDUUndI"

console = Console()


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"Hello {user.first_name}! Bot is connected successfully."
    )

    show_user_info(user, "/start command used")


# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text

    show_user_info(user, f"Message: {message_text}")

    await update.message.reply_text(
        f"Received your message: {message_text}"
    )


def show_user_info(user, extra_info):
    table = Table(
        title="Telegram User Details",
        box=box.ROUNDED,
        show_lines=True
    )

    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("User ID", str(user.id))
    table.add_row("First Name", str(user.first_name))
    table.add_row("Last Name", str(user.last_name))
    table.add_row("Username", str(user.username))
    table.add_row("Is Bot", str(user.is_bot))
    table.add_row("Language Code", str(user.language_code))
    table.add_row("Extra Info", str(extra_info))

    console.print(
        Panel.fit(
            table,
            title="[bold yellow]New User Activity[/bold yellow]",
            border_style="bright_blue"
        )
    )


app = ApplicationBuilder().token(BOT_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

console.print(
    Panel.fit(
        "[bold green]Bot is running successfully...[/bold green]",
        title="Telegram Bot",
        border_style="green"
    )
)

app.run_polling()