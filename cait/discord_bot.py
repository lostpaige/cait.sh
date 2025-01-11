# This is a demo of cait.  Cait is an ai powered assitant, for now the demo will run soley via discord.

import discord
from dotenv import load_dotenv
import os
import sys
import importlib
from pathlib import Path
from .hot_reload import HotReloader

from smolagents import CodeAgent, LiteLLMModel
from .tools.change_enshrouded_difficulty import ChangeEnshroudedDifficultyTool

# Move the bot setup into a function
def setup_bot():
    # Load environment variables from .env file
    load_dotenv()
    
    model = LiteLLMModel(
        os.getenv('OLLAMA_MODEL'),
        api_base=os.getenv('OLLAMA_API_BASE'),
        api_key=os.getenv('OLLAMA_API_KEY')
    )
    agent = CodeAgent(model=model, tools=[ChangeEnshroudedDifficultyTool()])

    # Set up the bot with all intents enabled
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    return discord.Client(intents=intents), model, agent

# Create a function to handle reloading
def reload_application():
    try:
        # Reload the tool module
        importlib.reload(sys.modules[ChangeEnshroudedDifficultyTool.__module__])
        print("✅ Successfully reloaded application modules")
    except Exception as e:
        print(f"❌ Error during reload: {str(e)}")

def main():
    client, model, agent = setup_bot()
    
    # Set up hot reloading
    cait_dir = Path(__file__).parent
    project_root = cait_dir.parent
    watch_paths = [
        str(cait_dir),  # Watch the cait directory
        str(project_root / '.env')  # Watch the .env file
    ]
    
    hot_reloader = HotReloader(
        reload_callback=reload_application,
        watch_paths=watch_paths,
        patterns=['.py', '.env']
    )
    hot_reloader.start()

    try:
        # Get token from environment variables
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            raise ValueError("No DISCORD_TOKEN found in environment variables")

        print('Starting bot...')    
        client.run(token)
    finally:
        hot_reloader.stop()

if __name__ == "__main__":
    main()
