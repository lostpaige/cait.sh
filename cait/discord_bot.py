# This is a demo of cait.  Cait is an ai powered assitant, for now the demo will run soley via discord.

import discord
from dotenv import load_dotenv
import os

from smolagents import CodeAgent, LiteLLMModel
from .tools.change_enshrouded_difficulty import ChangeEnshroudedDifficultyTool


model = LiteLLMModel("ollama/qwen2.5:latest", api_base="https://lm2.lan.wrng.ai", api_key="ollama")
agent = CodeAgent(model=model, tools=[ChangeEnshroudedDifficultyTool()])

# Load environment variables from .env file
load_dotenv()

# Set up the bot with all intents enabled for message monitoring
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # Enable guild (server) events
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print(f'Connected to the following guilds:')
    for guild in client.guilds:
        print(f'- {guild.name} (id: {guild.id})')

@client.event
async def on_message(message):
    # Don't respond to our own messages to avoid loops
    if message.author == client.user:
        return

    # Create a status message that we'll update
    status_message = await message.channel.send("🤔 Processing your request...")

    async def update_status(status_text):
        await status_message.edit(content=f"🔄 {status_text}")

    try:
        # Create a new tool instance with the status callback in its context
        tool = ChangeEnshroudedDifficultyTool(
            context={"status_callback": update_status}
        )
        # Create a new agent instance with the tool
        current_agent = CodeAgent(model=model, tools=[tool])
        
        # Run the agent and handle both async and non-async responses
        response = current_agent.run(message.content)
        if hasattr(response, '__await__'):
            response = await response

        # Update the status message with the final response
        await status_message.edit(content=f"✅ {response}")
    except Exception as e:
        await status_message.edit(content=f"❌ Error: {str(e)}")

# Get token from environment variables
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("No DISCORD_TOKEN found in environment variables")

print('Starting bot...')    
client.run(token)
