import os
import json
import subprocess
import sys
import time
from flask import Flask, jsonify, request
from discord.ext import commands
from threading import Thread
import asyncio

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

        @self.app.route('/guild_info')
        def guild_info():
            guild_id = request.args.get('guild_id')
            guild = self.bot.get_guild(int(guild_id)) if guild_id else None
            if not guild:
                return jsonify({'success': False, 'error': 'Guild not found'}), 404
            icon_url = guild.icon.url if guild.icon else None
            return jsonify({
                'id': guild.id,
                'name': guild.name,
                'icon_url': icon_url
            })

        @self.app.route('/guild_members')
        def guild_members():
            guild_id = request.args.get('guild_id')
            guild = self.bot.get_guild(int(guild_id)) if guild_id else None
            if not guild:
                return jsonify({'members': None}), 404
            members = [
                {'id': m.id, 'username': m.name, 'discriminator': m.discriminator, 'bot': m.bot}
                for m in guild.members
            ]
            return jsonify({'members': members})

        @self.app.route('/kick_member', methods=['POST'])
        def kick_member():
            data = request.get_json()
            guild_id = data.get('guild_id')
            user_id = data.get('user_id')
            token = data.get('token')
            # TODO: Validate token and permissions
            guild = self.bot.get_guild(int(guild_id)) if guild_id else None
            member = guild.get_member(int(user_id)) if guild else None
            if not member:
                return jsonify({'success': False, 'error': 'Member not found'}), 404
            # Use bot.loop to run the kick coroutine
            async def do_kick():
                try:
                    await member.kick(reason='Dashboard kick')
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 500
                return jsonify({'success': True})
            fut = asyncio.run_coroutine_threadsafe(do_kick(), self.bot.loop)
            return fut.result()

        @self.app.route('/ban_member', methods=['POST'])
        def ban_member():
            data = request.get_json()
            guild_id = data.get('guild_id')
            user_id = data.get('user_id')
            token = data.get('token')
            # TODO: Validate token and permissions
            guild = self.bot.get_guild(int(guild_id)) if guild_id else None
            member = guild.get_member(int(user_id)) if guild else None
            if not member:
                return jsonify({'success': False, 'error': 'Member not found'}), 404
            async def do_ban():
                try:
                    await member.ban(reason='Dashboard ban')
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 500
                return jsonify({'success': True})
            fut = asyncio.run_coroutine_threadsafe(do_ban(), self.bot.loop)
            return fut.result()

    def run_flask(self):
        self.app.run(host='0.0.0.0', port=5000)

    def start_node_ws_server(self):
        # Start the Node.js websocket server from the new webserver folder
        webserver_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'webserver')
        subprocess.Popen(['node', os.path.join(webserver_dir, 'websocket_server.js')], cwd=webserver_dir)
        time.sleep(2)

async def setup(bot):
    await bot.add_cog(webserver(bot))