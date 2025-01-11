from smolagents import Tool
import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

class ChangeEnshroudedDifficultyTool(Tool):
    name = "change_enshrouded_difficulty"
    description = """tool is used to change the difficulty of the enshrouded server."""
    inputs = {
        "difficulty": {"type": "string", "description": "The desired difficulty of the enshrouded server. (default, creative)"},
    }
    output_type = "string"

    def __init__(self, *args, **kwargs):
        self.context = kwargs.pop('context', {}) if 'context' in kwargs else {}
        super().__init__(*args, **kwargs)
        try:
            import paramiko
        except ImportError:
            raise ImportError(
                "You must install package `paramiko` to run this tool: run `pip install paramiko`."
            )
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    async def forward(self, difficulty: str) -> str:
        try:
            status_callback = self.context.get('status_callback')
            status_queue = Queue()
            
            if status_callback:
                await status_callback("Checking difficulty settings...")
                
            difficulties = {
                "default": {
                    "playerStaminaFactor": 1,
                    "enableDurability": True,
                    "miningDamageFactor": 1,
                    "resourceDropStackAmount": 1,
                    "factoryProductionFactor": 1,
                },
                "creative": {
                    "playerStaminaFactor": 4,
                    "enableDurability": False,
                    "miningDamageFactor": 2,
                    "resourceDropStackAmount": 2,
                    "factoryProductionFactor": 2,
                },
            }
            
            if difficulty not in difficulties:
                return f"Error: Invalid difficulty. Choose from {list(difficulties.keys())}"

            # Create a function for all the blocking SSH operations
            def ssh_operations():
                try:
                    status_queue.put("Connecting to server...")
                    host = os.getenv('ENSHROUDED_SSH_HOST')
                    username = os.getenv('ENSHROUDED_SSH_USERNAME')
                    password = os.getenv('ENSHROUDED_SSH_PASSWORD')

                    self.ssh.connect(host, username=username, password=password)
                    
                    status_queue.put("Reading current server configuration...")
                    config_path = "/home/steam/enshrouded/enshrouded_server.json"
                    sftp = self.ssh.open_sftp()
                    
                    try:
                        with sftp.file(config_path, 'r') as f:
                            config = json.load(f)
                    except FileNotFoundError:
                        return f"Error: Config file not found at {config_path}"
                    
                    status_queue.put("Updating game settings...")
                    if "gameSettings" not in config:
                        config["gameSettings"] = {}
                        
                    for key, value in difficulties[difficulty].items():
                        config["gameSettings"][key] = value
                    
                    status_queue.put("Writing new configuration...")
                    with sftp.file(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    sftp.close()
                    
                    status_queue.put("Restarting Enshrouded server (this may take a few minutes)...")
                    _, stdout, stderr = self.ssh.exec_command('sudo service enshrouded restart', timeout=300)
                    error = stderr.read().decode().strip()
                    if error:
                        return f"Config updated but server restart failed: {error}"
                    
                    stdout.channel.recv_exit_status()
                    return f"Successfully changed the difficulty to {difficulty} and restarted the server"
                except Exception as e:
                    return f"Error: {str(e)}"
                finally:
                    if self.ssh:
                        self.ssh.close()

            # Run the blocking operations in a thread pool
            loop = asyncio.get_event_loop()
            
            # Start a task to monitor the queue and update status
            async def update_status_from_queue():
                while True:
                    try:
                        # Check queue for 0.1 seconds
                        message = await loop.run_in_executor(None, status_queue.get, True, 0.1)
                        if status_callback:
                            await status_callback(message)
                    except:  # Queue.Empty or other errors
                        break

            # Run both the SSH operations and status updates
            status_task = loop.create_task(update_status_from_queue())
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, ssh_operations)
            
            # Cancel the status update task
            status_task.cancel()
            
            return result
        except Exception as e:
            return f"Error: {str(e)}"
