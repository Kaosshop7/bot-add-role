import discord
import os
import time
import psutil
import asyncio
import random
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "<h1>Bot is Alive!</h1><p>System Status: Online & Safe</p>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

def keep_alive():
    t = Thread(target=run_http)
    t.start()

TOKEN = os.environ.get('TOKEN')
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.status_loop.start()
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"⚠️ Sync Failed: {e}")

    async def on_ready(self):
        print(f'✅ Logged in as {self.user} (ID: {self.user.id})')

    @tasks.loop(seconds=20)
    async def status_loop(self):
        try:
            process = psutil.Process(os.getpid())
            ram_usage = process.memory_info().rss / 1024 / 1024
            total_members = sum(guild.member_count for guild in self.guilds)

            statuses = [
                discord.Activity(type=discord.ActivityType.watching, name=f"👥 Members: {total_members:,}"),
                discord.Activity(type=discord.ActivityType.playing, name=f"💾 RAM: {ram_usage:.2f} MB"),
                discord.Activity(type=discord.ActivityType.listening, name="/help เพื่อดูคำสั่ง")
            ]
            await self.change_presence(activity=random.choice(statuses))
        except Exception as e:
            print(f"Status Error: {e}")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()

bot = MyBot()

user_last_click = {}
COOLDOWN_TIME = 3.0 

def get_discord_color(hex_str):
    try:
        if hex_str.startswith("#"): return discord.Color.from_str(hex_str)
        return getattr(discord.Color, hex_str, discord.Color.blue())()
    except: return discord.Color.default()

def create_embed(title, desc, color_hex, img, thumb):
    embed = discord.Embed(title=title, description=desc.replace("\\n", "\n"), color=get_discord_color(color_hex))
    if img: embed.set_image(url=img)
    if thumb: embed.set_thumbnail(url=thumb)
    return embed

async def fetch_message_safe(interaction, message_id):
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        if msg.author != interaction.client.user:
            await interaction.response.send_message("❌ บอทแก้ได้เฉพาะข้อความของตัวเองเท่านั้น", ephemeral=True)
            return None
        return msg
    except:
        await interaction.response.send_message("❌ ไม่พบข้อความ", ephemeral=True)
        return None

@bot.tree.command(name="setup_embed", description="สร้าง embed")
@app_commands.checks.has_permissions(administrator=True)
async def setup_embed(interaction: discord.Interaction, title: str, description: str, color_hex: str = "#3498db", image_url: str = None, thumbnail_url: str = None):
    embed = create_embed(title, description, color_hex, image_url, thumbnail_url)
    embed.set_footer(text=f"Setup by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message("✅ สร้าง Embed เรียบร้อย", ephemeral=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="add_button", description="เพิ่มปุ่มรับยศ")
@app_commands.checks.has_permissions(administrator=True)
async def add_button(interaction: discord.Interaction, message_id: str, role: discord.Role, label: str, color: str = "blurple", emoji: str = None):
    msg = await fetch_message_safe(interaction, message_id)
    if not msg: return
    view = discord.ui.View.from_message(msg)
    
    style_map = {"blurple": discord.ButtonStyle.blurple, "green": discord.ButtonStyle.green, "red": discord.ButtonStyle.red, "grey": discord.ButtonStyle.grey}
    style = style_map.get(color.lower(), discord.ButtonStyle.blurple)
    
    button = discord.ui.Button(style=style, label=label, emoji=emoji, custom_id=f"role:{role.id}")
    view.add_item(button)
    await msg.edit(view=view)
    await interaction.response.send_message(f"✅ เพิ่มปุ่ม **{label}** เรียบร้อย!", ephemeral=True)

@bot.tree.command(name="remove_button", description="ลบปุ่มรับยศ")
@app_commands.checks.has_permissions(administrator=True)
async def remove_button(interaction: discord.Interaction, message_id: str, label: str):
    msg = await fetch_message_safe(interaction, message_id)
    if not msg: return
    view = discord.ui.View.from_message(msg)
    remaining = [item for item in view.children if isinstance(item, discord.ui.Button) and item.label != label]
    if len(remaining) == len(view.children):
        await interaction.response.send_message(f"❌ ไม่พบปุ่มชื่อ '{label}'", ephemeral=True)
        return
    new_view = discord.ui.View(timeout=None)
    for item in remaining: new_view.add_item(item)
    await msg.edit(view=new_view)
    await interaction.response.send_message(f"🗑️ ลบปุ่มเรียบร้อย", ephemeral=True)

@bot.tree.command(name="ping", description="เช็คปิง")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"ตรวจสอบค่าปิง **{latency}ms**", ephemeral=True)

@bot.tree.command(name="help", description="คู่มือ")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="คู่มือการเซ็ตบอทตัวนี้", color=discord.Color.gold())
    embed.add_field(name="ทั่วไป", value="`/ping`, `/help`", inline=False)
    if interaction.user.guild_permissions.administrator:
        embed.add_field(name="แอดมิน", value="`/setup_embed`, `/add_button`, `/remove_button`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id", "").startswith("role:"):
        
        user_id = interaction.user.id
        current_time = time.time()

        if user_id in user_last_click:
            last_click = user_last_click[user_id]
            if current_time - last_click < COOLDOWN_TIME:
                remaining = round(COOLDOWN_TIME - (current_time - last_click), 1)
                await interaction.response.send_message(f"⏳ **อย่ากดถี่ๆนะครับ** รออีก {remaining} วินาทีค่อยกดใหม่นะ", ephemeral=True)
                return

        user_last_click[user_id] = current_time

        try:
            role_id = int(interaction.data["custom_id"].split(":")[1])
            role = interaction.guild.get_role(role_id)
            user = interaction.user
            
            if not role:
                await interaction.response.send_message("❌ ไม่พบยศนี้", ephemeral=True)
                return

            if role in user.roles:
                await user.remove_roles(role)
                await interaction.response.send_message(f"➖ เอาบทบาท **{role.name}** ออกแล้ว", ephemeral=True)
            else:
                await user.add_roles(role)
                await interaction.response.send_message(f"➕ รับบทบาท **{role.name}** เรียบร้อย", ephemeral=True)

        except discord.errors.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์แจกยศนี้ (เอายศบอทไว้สูงกว่านี้)", ephemeral=True)
        except Exception as e:
            print(f"Error: {e}")
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด", ephemeral=True)

def run_bot_safe():
    if not TOKEN:
        print("❌ Error: ไม่พบ TOKEN")
        return

    retry_count = 0
    base_wait_time = 60

    while True:
        try:
            print("🚀 Starting Bot...")
            bot.run(TOKEN)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⛔ BLOCKED (429)! Sleeping...")
                wait_time = min(base_wait_time * (2 ** retry_count), 3600)
                jitter = random.randint(1, 30)
                time.sleep(wait_time + jitter)
                retry_count += 1
            else:
                print(f"❌ Error: {e}. Retry in 10s...")
                time.sleep(10)
        except Exception as e:
            print(f"⚠️ Critical Error: {e}. Retry in 30s...")
            time.sleep(30)
            retry_count = 0

if __name__ == '__main__':
    keep_alive()
    run_bot_safe()
