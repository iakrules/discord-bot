import asyncio
import discord
from discord.ext import commands
import youtube_dl
import os

ffmpeg_options = {
    'options': '-vn'
}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicCog(commands.Cog):

    def __init__(self, client):
        self.client = client

    # Commands

    @commands.command()
    async def play(self, ctx, url):
        """Streams from a url"""
        try:
            channel = ctx.author.voice.channel
            await channel.connect()
        except:
            pass
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.client.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Now playing: {player.title}')

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            voice = ctx.voice_client
            if voice != None and voice.is_paused():
                voice.resume()
            else:
                await ctx.send("Missing URL!")

    @commands.command(aliases=['disconnect, dc'])
    async def leave(self, ctx):
        """Disconnects bot from the voice channel"""
        voice = ctx.voice_client
        if voice.is_connected():
            await voice.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def pause(self, ctx):
        """Pauses audio"""
        voice = ctx.voice_client
        if voice.is_playing():
            voice.pause()
        else:
            await ctx.send("Currently no audio is playing.")

    @commands.command()
    async def resume(self, ctx):
        """Resumes currently paused audio"""
        voice = ctx.voice_client
        if voice.is_paused():
            voice.resume()
        else:
            await ctx.send("The audio is not paused.")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        voice = ctx.voice_client
        voice.stop()

    @commands.command(aliases=['join'])
    async def connect(self, ctx):
        """Connects bot to currently connected voice channel"""
        channel = ctx.author.voice.channel
        try:
            await channel.connect()
        except:
            voice = ctx.voice_client
            if voice.is_connected() and voice.channel != channel:
                await voice.disconnect()
                await channel.connect()

def setup(client):
    client.add_cog(MusicCog(client))