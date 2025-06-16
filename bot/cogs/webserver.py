import os
import json
import subprocess
import sys
import time
from flask import Flask, jsonify
from discord.ext import commands
from threading import Thread

class webserver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = Flask(__name__)
        self.setup_routes()
        # Start Flask server in a separate thread
        self.flask_thread = Thread(target=self.run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()
        # Start the Node.js websocket server
        self.start_node_ws_server()

    def setup_routes(self):
        @self.app.route('/guild_count')
        def guild_count():
            return jsonify({'guild_count': len(self.bot.guilds)})

    def run_flask(self):
        self.app.run(host='0.0.0.0', port=5000)

    def start_node_ws_server(self):
        subprocess.Popen(['node', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'websocket_server.js')])
        time.sleep(2)

async def setup(bot):
    await bot.add_cog(webserver(bot))