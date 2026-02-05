import discord
import os
import time
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# ==========================================
# ส่วน Web Server สำหรับ Render
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive! Running..."

def run():
    # ใช้ Port ตามที่ Render กำหนด หรือ 8080 ถ้าไม่มี
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# ส่วนของ Discord Bot
# ==========================================

# ตรวจสอบ Token ก่อนรัน
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    print("❌ Error: ไม่พบ TOKEN ใน Environment Variables")

# กำหนด Intents (สำคัญมาก ต้องเปิดใน Discord Developer Portal ด้วย)
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            # Sync คำสั่ง Slash Commands
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
        except Exception as e:
            # ถ้า Sync ไม่ผ่าน ให้แจ้งเตือนแต่ไม่ต้อง Crash
            print(f"⚠️ Sync Failed: {e}")

    async def on_ready(self):
        print(f'✅ Logged in as {self.user} (ID: {self.user.id})')
        print('--------------------------------------------------')

bot = MyBot()

# --- ส่วนจัดการ Interaction (ปุ่ม) ---
@bot.event
async def on_interaction(interaction: discord.Interaction):
    # เช็คว่าเป็นปุ่มรับยศหรือไม่
    if interaction.type == discord.InteractionType.component and \
       interaction.data.get("custom_id", "").startswith("role:"):
        
        try:
            role_id = int(interaction.data["custom_id"].split(":")[1])
            role = interaction.guild.get_role(role_id)
            user = interaction.user

            if not role:
                await interaction.response.send_message("❌ ไม่พบยศนี้ (อาจถูกลบไปแล้ว)", ephemeral=True)
                return

            # เช็คว่าบอทมียศสูงกว่ายศที่จะแจกไหม
            if role >= interaction.guild.me.top_role:
                await interaction.response.send_message("⚠️ ยศนี้สูงกว่ายศบอท บอทแจกไม่ได้", ephemeral=True)
                return

            # ระบบ Toggle (มีให้ลบ / ไม่มีให้เพิ่ม)
            if role in user.roles:
                await user.remove_roles(role)
                await interaction.response.send_message(f"➖ เอาบทบาท **{role.name}** ออกแล้ว", ephemeral=True)
            else:
                await user.add_roles(role)
                await interaction.response.send_message(f"➕ รับบทบาท **{role.name}** เรียบร้อย", ephemeral=True)

        except discord.errors.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์จัดการยศนี้ (ตรวจสอบลำดับยศ)", ephemeral=True)
        except Exception as e:
            print(f"Error handling interaction: {e}")
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด", ephemeral=True)

# --- คำสั่ง Slash Commands ---

@bot.tree.command(name="setup_embed", description="สร้าง embed (Admin Only)")
@app_commands.describe(
    title="หัวข้อ", description="เนื้อหา", 
    color_hex="สี (เช่น #FF0000 หรือ red)",
    image_url="รูปใหญ่ด้านล่าง", thumbnail_url="รูปเล็กมุมขวา"
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_embed(interaction: discord.Interaction, title: str, description: str, color_hex: str = "#3498db", image_url: str = None, thumbnail_url: str = None):
    
    embed = create_embed(title, description, color_hex, image_url, thumbnail_url)
    embed.set_footer(text=f"Setup by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

    await interaction.response.send_message("✅ สร้าง Embed เรียบร้อย", ephemeral=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="edit_embed", description="แก้ไขข้อความ/รูปภาพ (Admin Only)")
@app_commands.describe(message_id="ID ของข้อความที่ต้องการแก้")
@app_commands.checks.has_permissions(administrator=True)
async def edit_embed(interaction: discord.Interaction, message_id: str, title: str = None, description: str = None, color_hex: str = None, image_url: str = None, thumbnail_url: str = None):
    
    msg = await fetch_message_safe(interaction, message_id)
    if not msg: return

    old_embed = msg.embeds[0]
    
    new_title = title if title else old_embed.title
    new_desc = description.replace("\\n", "\n") if description else old_embed.description
    
    if color_hex:
        new_color = get_discord_color(color_hex)
    else:
        new_color = old_embed.color

    new_image = image_url if image_url else (old_embed.image.url if old_embed.image else None)
    new_thumb = thumbnail_url if thumbnail_url else (old_embed.thumbnail.url if old_embed.thumbnail else None)

    new_embed = discord.Embed(title=new_title, description=new_desc, color=new_color)
    if new_image: new_embed.set_image(url=new_image)
    if new_thumb: new_embed.set_thumbnail(url=new_thumb)
    
    # เช็คว่ามี footer เดิมไหม
    if old_embed.footer:
        new_embed.set_footer(text=old_embed.footer.text, icon_url=old_embed.footer.icon_url)

    await msg.edit(embed=new_embed)
    await interaction.response.send_message(f"✅ อัปเดต Embed (ID: {message_id}) เรียบร้อย!", ephemeral=True)

@bot.tree.command(name="add_button", description="เพิ่มปุ่มรับยศ (Admin Only)")
@app_commands.describe(
    message_id="ID ของข้อความ",
    role="เลือกยศ", label="ข้อความบนปุ่ม", emoji="อิโมจิ",
    color="สีปุ่ม"
)
@app_commands.choices(color=[
    app_commands.Choice(name="Blurple (น้ำเงินม่วง)", value="blurple"),
    app_commands.Choice(name="Green (เขียว)", value="green"),
    app_commands.Choice(name="Red (แดง)", value="red"),
    app_commands.Choice(name="Grey (เทา)", value="grey"),
])
@app_commands.checks.has_permissions(administrator=True)
async def add_button(interaction: discord.Interaction, message_id: str, role: discord.Role, label: str, color: app_commands.Choice[str], emoji: str = None):
    
    msg = await fetch_message_safe(interaction, message_id)
    if not msg: return

    view = discord.ui.View.from_message(msg)
    
    style = getattr(discord.ButtonStyle, color.value)
    button = discord.ui.Button(
        style=style,
        label=label,
        emoji=emoji,
        custom_id=f"role:{role.id}" 
    )
    
    view.add_item(button)
    
    await msg.edit(view=view)
    await interaction.response.send_message(f"✅ เพิ่มปุ่ม **{label}** เรียบร้อย!", ephemeral=True)

@bot.tree.command(name="remove_button", description="ลบปุ่มรับยศ (Admin Only)")
@app_commands.checks.has_permissions(administrator=True)
async def remove_button(interaction: discord.Interaction, message_id: str, label: str):
    
    msg = await fetch_message_safe(interaction, message_id)
    if not msg: return

    view = discord.ui.View.from_message(msg)
    
    remaining_items = [item for item in view.children if isinstance(item, discord.ui.Button) and item.label != label]
    
    if len(remaining_items) == len(view.children):
        await interaction.response.send_message(f"❌ ไม่พบปุ่มชื่อ '{label}' ในข้อความนี้", ephemeral=True)
        return

    new_view = discord.ui.View(timeout=None)
    for item in remaining_items:
        new_view.add_item(item)

    await msg.edit(view=new_view)
    await interaction.response.send_message(f"🗑️ ลบปุ่ม **{label}** ออกแล้ว", ephemeral=True)

# --- Helper Functions ---

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
        await interaction.response.send_message("❌ ไม่พบข้อความ (ต้องพิมพ์คำสั่งในห้องเดียวกับข้อความ)", ephemeral=True)
        return None

# ==========================================
# Run Bot
# ==========================================
if __name__ == '__main__':
    keep_alive()
    if TOKEN:
        try:
            bot.run(TOKEN)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("⛔ BLOCKED BY DISCORD (429).")
                print("System will sleep for 1 hour to Reset Rate Limit.")
                # ถ้าโดนแบน ให้โปรแกรมหยุดทำงานไปเลย เพื่อให้ Render ไม่ Restart ถี่ๆ
                time.sleep(3600)
            else:
                print(f"Error: {e}")
    else:
        print("Please set TOKEN in Environment Variables")

