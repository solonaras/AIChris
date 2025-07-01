import psutil
import time
import traceback
from datetime import datetime
import requests
import json
from discord.ext import commands, tasks

# === Self-Awareness Engine ===
def gather_system_metrics():
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        uptime = time.time() - psutil.boot_time()
        return {
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_percent": disk,
            "uptime_seconds": int(uptime)
        }
    except Exception as e:
        return {"error": f"System metrics error: {e}"}

def check_ollama_health(api_url):
    try:
        start = time.time()
        res = requests.get(f"{api_url}/api/tags", timeout=10)
        latency = time.time() - start
        if res.status_code == 200:
            return {"status": "online", "latency": round(latency, 2)}
        else:
            return {"status": "error", "code": res.status_code}
    except Exception as e:
        return {"status": "offline", "error": str(e)}

class SelfAwarenessEngine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_reflection.start()

    def gather_cognitive_status(self):
        return {
            "maturity_level": self.bot.current_age,
            "depressive_hits": self.bot.depressive_hits,
            "belief_snapshot": self.bot.beliefs,
            "interaction_count": self.bot.interaction_count
        }

    def generate_self_reflection(self):
        sys_metrics = gather_system_metrics()
        llm_status = check_ollama_health(self.bot.model_api_url)
        cog_status = self.gather_cognitive_status()
        now = datetime.utcnow().isoformat()

        reflection = (
            f"**Self-Reflection Report ({now})**\n"
            f"**System**:\n"
            f"CPU: {sys_metrics.get('cpu_percent', 'N/A')}% | "
            f"Memory: {sys_metrics.get('memory_percent', 'N/A')}% | "
            f"Disk: {sys_metrics.get('disk_percent', 'N/A')}%\n"
            f"Uptime: {sys_metrics.get('uptime_seconds', 'N/A')}s\n"
            f"**LLM**:\n"
            f"Status: {llm_status.get('status')} | "
            f"Latency: {llm_status.get('latency', 'N/A')}s\n"
            f"**Cognition**:\n"
            f"Age: {cog_status['maturity_level']} | "
            f"Depressive Hits: {cog_status['depressive_hits']} | "
            f"Interactions: {cog_status['interaction_count']}\n"
            f"Beliefs:\n{json.dumps(cog_status['belief_snapshot'], indent=2)}"
        )
        return reflection

    @commands.command()
    async def reflect(self, ctx):
        try:
            reflection = self.generate_self_reflection()
            await ctx.send(reflection)
        except Exception as e:
            error_msg = f"[Reflection Error] {traceback.format_exc()}"
            await ctx.send(error_msg)

    @tasks.loop(minutes=60)
    async def scheduled_reflection(self):
        try:
            reflection = self.generate_self_reflection()
            print(f"**Scheduled Self-Check**\n{reflection}")
        except Exception as e:
            print(f"[Scheduled Reflection Error] {e}")

    @scheduled_reflection.before_loop
    async def before_reflection(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(SelfAwarenessEngine(bot))

# In your main bot file, you would load this cog with:
# await bot.load_extension('self_awareness_engine')
