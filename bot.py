import discord
import os

# โค้ดทดสอบการเชื่อมต่อแบบเพียวๆ
TOKEN = os.environ.get('TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ SUCCEEDED! Logged in as {client.user}')
    print(f'✅ Bot ID: {client.user.id}')
    print('-------------------------------------------')

@client.event
async def on_connect():
    print('🟡 Connected to Discord Gateway... Waiting for handshake...')

print("🚀 Starting Bot...")
if not TOKEN:
    print("❌ Error: ไม่พบ TOKEN")
else:
    print(f"🔑 Found Token: {TOKEN[:5]}... (Hidden)")
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f"❌ Critical Error: {e}")

