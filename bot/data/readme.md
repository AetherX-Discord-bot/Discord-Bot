# Data Folder

This folder contains persistent data and resources used by the bot.

- `database.db`: The main SQLite database file for storing bot data, such as user info, settings, or logs. If this file contains user data, it is not required for the bot to function and can be safely deleted or ignored; it may simply contain the developer's test data.
- Other files in this folder may include additional data, cache, or resources required for bot operation with the database.

> **Note:** Do not delete or modify files in this folder unless you know what you are doing, as it may affect the bot's functionality.

---

## Viewing the Database

- You can use the VS Code extension [Sqlite Viewer](https://marketplace.visualstudio.com/items?itemName=qwtel.sqlite-viewer) to view and (if paid for) edit `database.db` directly in VS Code.
- GitHub does not support native viewing of SQLite database files.
