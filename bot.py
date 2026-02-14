import discord
import os
import time
import psutil
import asyncio
import random
import logging
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    return "<h1>Bot is Alive!</h1><p>Running on Render</p>"

def run_http():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

def keep_alive():
    t = Thread(target=run_http)
    t.daemon = True
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

def get_discord_color(color_name):
    colors = {
        "red": discord.Color.red(),
        "blue": discord.Color.blue(),
        "green": discord.Color.green(),
        "gold": discord.Color.gold(),
        "orange": discord.Color.orange(),
        "purple": discord.Color.purple(),
        "magenta": discord.Color.magenta(),
        "teal": discord.Color.teal(),
        "dark_theme": discord.Color.from_rgb(47, 49, 54),
        "blurple": discord.Color.blurple(),
        "grey": discord.Color.light_grey(),
        "dark_red": discord.Color.dark_red(),
        "dark_blue": discord.Color.dark_blue(),
        "dark_green": discord.Color.dark_green(),
        "dark_orange": discord.Color.dark_orange(),
        "dark_purple": discord.Color.dark_purple(),
        "dark_gold": discord.Color.dark_gold(),
        "black": discord.Color.default(),
        "white": discord.Color.from_rgb(255, 255, 255),
        "pink": discord.Color.from_rgb(255, 192, 203),
        "cyan": discord.Color.from_rgb(0, 255, 255),
        "lime": discord.Color.from_rgb(50, 205, 50),
        "yellow": discord.Color.from_rgb(255, 255, 0),
    }
    if color_name.startswith("#"):
        return discord.Color.from_str(color_name)
    
    return colors.get(color_name, discord.Color.default())

def create_embed(title, desc, color_input, img, thumb):
    embed = discord.Embed(title=title, description=desc.replace("\\n", "\n"), color=get_discord_color(color_input))
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
@app_commands.choices(color_select=[
    app_commands.Choice(name="🔴 Red", value="red"),
    app_commands.Choice(name="🔵 Blue", value="blue"),
    app_commands.Choice(name="🟢 Green", value="green"),
    app_commands.Choice(name="🟡 Gold", value="gold"),
    app_commands.Choice(name="🟠 Orange", value="orange"),
    app_commands.Choice(name="🟣 Purple", value="purple"),
    app_commands.Choice(name="🌸 Pink", value="pink"),
    app_commands.Choice(name="⚫ Dark Theme (เนียนไปกับพื้นหลัง)", value="dark_theme"),
    app_commands.Choice(name="⚪ White", value="white"),
    app_commands.Choice(name="🌑 Black", value="black"),
    app_commands.Choice(name="🌊 Teal", value="teal"),
    app_commands.Choice(name="🔮 Magenta", value="magenta"),
    app_commands.Choice(name="🎮 Blurple (สีดิสคอร์ด)", value="blurple"),
    app_commands.Choice(name="🌫️ Grey", value="grey"),
    app_commands.Choice(name="🧪 Lime", value="lime"),
    app_commands.Choice(name="💎 Cyan", value="cyan"),
    app_commands.Choice(name="🩸 Dark Red", value="dark_red"),
    app_commands.Choice(name="🌌 Dark Blue", value="dark_blue"),
    app_commands.Choice(name="🌲 Dark Green", value="dark_green"),
    app_commands.Choice(name="🎃 Dark Orange", value="dark_orange"),
    app_commands.Choice(name="🍆 Dark Purple", value="dark_purple"),
])
async def setup_embed(
    interaction: discord.Interaction, 
    title: str, 
    description: str, 
    color_select: str = "blurple",
    custom_hex: str = None,
    image_url: str = None, 
    thumbnail_url: str = None
):
    
    final_color = custom_hex if custom_hex else color_select
    
    embed = create_embed(title, description, final_color, image_url, thumbnail_url)
    embed.set_footer(text=f"Setup by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message("✅ สร้าง Embed เรียบร้อย", ephemeral=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="add_button", description="เพิ่มปุ่มรับยศ")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(color=[
    app_commands.Choice(name="Blurple (สีม่วงฟ้า)", value="blurple"),
    app_commands.Choice(name="Green (สีเขียว)", value="green"),
    app_commands.Choice(name="Red (สีแดง)", value="red"),
    app_commands.Choice(name="Grey (สีเทา)", value="grey"),
])
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
    embed = discord.Embed(title="คู่มือการเซ็ตบอท", color=discord.Color.gold())
    embed.add_field(name="ทั่วไป", value="`/ping`, `/help`", inline=False)
    if interaction.user.guild_permissions.administrator:
        embed.add_field(name="แอดมิน", value="`/setup_embed` - สร้างข้อความ (เลือกสีได้)\n`/add_button` - เพิ่มปุ่มแจกยศ\n`/remove_button` - ลบปุ่ม", inline=False)
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
                await interaction.response.send_message("❌ ไม่พบยศนี้ (อาจถูกลบไปแล้ว)", ephemeral=True)
                return

            if role in user.roles:
                await user.remove_roles(role)
                await interaction.response.send_message(f"➖ เอาบทบาท **{role.name}** ออกแล้ว", ephemeral=True)
            else:
                await user.add_roles(role)
                await interaction.response.send_message(f"➕ รับบทบาท **{role.name}** เรียบร้อย", ephemeral=True)

        except discord.errors.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์แจกยศนี้ (โปรดลากยศบอทไว้สูงกว่ายศที่จะแจก)", ephemeral=True)
        except Exception as e:
            print(f"Error: {e}")
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด", ephemeral=True)

def run_bot_safe():
    if not TOKEN:
        print("❌ Error: ไม่พบ TOKEN ใน Environment Variables")
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
