import discord
from discord.ext import commands
from typing import Optional

class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='purge', aliases=['clear', 'delete'])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_messages(self, ctx, amount: str, member: Optional[discord.Member] = None):
        """Delete messages in bulk (optionally from a specific user)
        
        Usage:
        !purge 10              - Deletes 10 messages
        !purge 10 @User        - Deletes 10 messages from @User
        !purge all             - Deletes all messages (requires admin)
        """
        try:
            if amount.lower() == 'all':
                if not ctx.author.guild_permissions.administrator:
                    await ctx.send("You need administrator permissions to purge all messages.", delete_after=5)
                    return
                
                def non_pinned_check(msg):
                    return not msg.pinned

                deleted = await ctx.channel.purge(limit=None, check=non_pinned_check)
                await ctx.send(f"Deleted {len(deleted)} messages (excluding pinned).", delete_after=5)
                return
            try:
                amt = int(amount)
            except ValueError:
                await ctx.send("Please provide a valid number or 'all'.", delete_after=5)
                return

            if amt <= 0:
                await ctx.send("Please provide a positive number greater than 0.", delete_after=5)
                return
            elif amt > 500:
                await ctx.send("Maximum purge limit is 500 messages at once.", delete_after=5)
                return
            
            limit = amt + 1
            
            def member_check(msg):
                if member:
                    return msg.author == member
                return True
            deleted = await ctx.channel.purge(limit=limit, check=member_check)
            
            msg = f"Deleted {len(deleted) - 1} messages"
            if member:
                msg += f" from {member.display_name}"
            await ctx.send(msg + ".", delete_after=5)
            
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}", delete_after=10)
            raise e

    @purge_messages.error
    async def purge_error(self, ctx, error):
        error_messages = {
            commands.MissingPermissions: "You don't have permission to manage messages.",
            commands.BotMissingPermissions: "I don't have permission to manage messages.",
            commands.BadArgument: "Please provide a valid number.",
            commands.MissingRequiredArgument: "Please specify how many messages to delete. Example: `!purge 10`"
        }
        
        for error_type, message in error_messages.items():
            if isinstance(error, error_type):
                await ctx.send(message, delete_after=10)
                return
        
        await ctx.send(f"An unexpected error occurred: {str(error)}", delete_after=10)

async def setup(bot):
    await bot.add_cog(PurgeCog(bot))