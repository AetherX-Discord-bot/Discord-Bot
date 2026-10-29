import discord
from discord.ext import commands
from discord.ui import Select, View, Button
import aiohttp
import random
import asyncio
import html

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trivia_categories = {}
        self.difficulties = ["Easy", "Medium", "Hard"]
        self.active_trivias = {}
        self.session = aiohttp.ClientSession()
        self.EMBED_COLOR = discord.Color.from_rgb(0, 0, 139)  # Dark blue

    async def fetch_categories(self):
        """Fetch categories from OpenTDB API"""
        async with self.session.get("https://opentdb.com/api_category.php") as resp:
            data = await resp.json()
            self.trivia_categories = {cat['name']: cat['id'] for cat in data['trivia_categories']}

    @commands.command(name="trivia", aliases=["quiz"])
    async def trivia_command(self, ctx):
        """Start a trivia game with customizable options"""
        if not self.trivia_categories:
            await self.fetch_categories()

        embed = discord.Embed(
            title="🎲 Trivia Game Setup",
            description="Please select a category for your trivia game:",
            color=self.EMBED_COLOR
        )
        
        category_select = Select(
            placeholder="Choose a category...",
            options=[
                discord.SelectOption(label=cat, value=str(cat_id))
                for cat, cat_id in self.trivia_categories.items()
            ]
        )
        
        view = View()
        view.add_item(category_select)
        
        async def category_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("This isn't your trivia game!", ephemeral=True)
                return
                
            selected_category_id = int(category_select.values[0])
            selected_category = next(cat for cat, cat_id in self.trivia_categories.items() if cat_id == selected_category_id)
            
            difficulty_embed = discord.Embed(
                title="🎲 Trivia Difficulty",
                description="Please select a difficulty level:",
                color=self.EMBED_COLOR
            )
            
            difficulty_select = Select(
                placeholder="Choose a difficulty...",
                options=[
                    discord.SelectOption(label=diff, value=diff.lower())
                    for diff in self.difficulties
                ]
            )
            
            diff_view = View()
            diff_view.add_item(difficulty_select)
            
            async def difficulty_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("This isn't your trivia game!", ephemeral=True)
                    return
                    
                selected_difficulty = difficulty_select.values[0]
                
                count_embed = discord.Embed(
                    title="🎲 Trivia Questions Count",
                    description="How many questions would you like? (1-20)",
                    color=self.EMBED_COLOR
                )
                
                await interaction.response.edit_message(embed=count_embed, view=None)
                
                def count_check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= 20
                
                try:
                    count_msg = await self.bot.wait_for('message', timeout=60.0, check=count_check)
                    question_count = int(count_msg.content)
                    
                    try:
                        await count_msg.delete()
                    except:
                        pass
                    
                    await self.start_trivia(ctx, interaction.message, selected_category_id, selected_category, selected_difficulty, question_count)
                    
                except asyncio.TimeoutError:
                    await ctx.send("Timed out waiting for question count. Trivia cancelled.")
                    return
                    
            difficulty_select.callback = difficulty_callback
            
            await interaction.response.edit_message(embed=difficulty_embed, view=diff_view)
        
        category_select.callback = category_callback
        
        await ctx.send(embed=embed, view=view)
    
    async def start_trivia(self, ctx, message, category_id, category_name, difficulty, count):
        """Start the trivia game with selected options"""
        try:
            async with self.session.get(
                f"https://opentdb.com/api.php?amount={count}&category={category_id}&difficulty={difficulty}&type=multiple"
            ) as resp:
                data = await resp.json()
                
            if data['response_code'] != 0:
                await ctx.send("Failed to fetch questions from the API. Please try again later.")
                return
                
            questions = data['results']
            
            self.active_trivias[ctx.author.id] = {
                "questions": questions,
                "current_index": 0,
                "score": 0,
                "message": message,
                "category": category_name,
                "difficulty": difficulty,
                "timeout_task": None,
                "channel": ctx.channel,
                "author": ctx.author
            }
            
            await self.display_question(ctx.author.id)
            
        except Exception as e:
            await ctx.send(f"An error occurred while starting the trivia: {e}")
    
    async def display_question(self, user_id):
        """Display the current question with answer buttons"""
        trivia_data = self.active_trivias[user_id]
        current_index = trivia_data["current_index"]
        question_data = trivia_data["questions"][current_index]
        
        question = html.unescape(question_data['question'])
        correct_answer = html.unescape(question_data['correct_answer'])
        incorrect_answers = [html.unescape(ans) for ans in question_data['incorrect_answers']]
        
        embed = discord.Embed(
            title=f"Trivia Question {current_index + 1}/{len(trivia_data['questions'])}",
            description=question,
            color=self.EMBED_COLOR
        )
        embed.add_field(name="Category", value=trivia_data["category"], inline=True)
        embed.add_field(name="Difficulty", value=trivia_data["difficulty"].capitalize(), inline=True)
        embed.add_field(name="Score", value=trivia_data["score"], inline=True)
        
        view = discord.ui.View(timeout=30.0)
        
        answers = incorrect_answers + [correct_answer]
        random.shuffle(answers)

        for answer in answers:
            button_label = answer[:80]
            button = Button(label=button_label, style=discord.ButtonStyle.secondary)
            button.callback = self.create_answer_callback(user_id, answer == correct_answer, correct_answer)
            view.add_item(button)
        
        if trivia_data.get("timeout_task"):
            trivia_data["timeout_task"].cancel()
        
        trivia_data["timeout_task"] = asyncio.create_task(
            self.question_timeout(user_id))

        await trivia_data["message"].edit(embed=embed, view=view)
    
    async def question_timeout(self, user_id):
        """Handle question timeout after 30 seconds"""
        try:
            await asyncio.sleep(30)
            
            if user_id not in self.active_trivias:
                return
                
            trivia_data = self.active_trivias[user_id]
            
            await trivia_data["channel"].send(f"⌛ Time's up for {trivia_data['author'].mention}! The correct answer was not selected in time.")
            
            trivia_data["current_index"] += 1
            
            if trivia_data["current_index"] < len(trivia_data["questions"]):
                await self.display_question(user_id)
            else:
                embed = discord.Embed(
                    title="Trivia Game Over! (Timed Out)",
                    description=f"Your final score: {trivia_data['score']}/{len(trivia_data['questions'])}",
                    color=self.EMBED_COLOR
                )
                await trivia_data["message"].edit(embed=embed, view=None)
                del self.active_trivias[user_id]
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in question_timeout: {e}")
            if user_id in self.active_trivias:
                del self.active_trivias[user_id]
    
    def create_answer_callback(self, user_id, is_correct, correct_answer):
        """Create a callback function for answer buttons"""
        async def answer_callback(interaction):
            if interaction.user.id != user_id:
                await interaction.response.send_message("This isn't your trivia game!", ephemeral=True)
                return
                
            trivia_data = self.active_trivias[user_id]
            
            if trivia_data.get("timeout_task"):
                trivia_data["timeout_task"].cancel()
            
            if is_correct:
                trivia_data["score"] += 1
                result = "✅ Correct!"
            else:
                result = f"❌ Incorrect! The correct answer was: **{correct_answer}**"
            
            await interaction.response.send_message(result, ephemeral=True)
            
            trivia_data["current_index"] += 1
            
            if trivia_data["current_index"] < len(trivia_data["questions"]):
                await self.display_question(user_id)
            else:
                embed = discord.Embed(
                    title="Trivia Game Over!",
                    description=f"Your final score: {trivia_data['score']}/{len(trivia_data['questions'])}",
                    color=self.EMBED_COLOR
                )
                await trivia_data["message"].edit(embed=embed, view=None)
                del self.active_trivias[user_id]
        
        return answer_callback

    def cog_unload(self):
        """Clean up the aiohttp session when cog is unloaded"""
        asyncio.create_task(self.session.close())

async def setup(bot):
    await bot.add_cog(Trivia(bot))