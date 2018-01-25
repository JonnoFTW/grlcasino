import discord
from discord.ext import commands
from random import randint
from datetime import datetime


class DiceCog:
    dice = {
        1: '⚀',
        2: '⚁',
        3: '⚂',
        4: '⚃',
        5: '⚄',
        6: '⚅'
    }
    min_buy_in = 0.05
    max_buy_in = 10

    def __init__(self, bot):
        self.bot = bot
        self.user_manager = bot.user_manager
        self.grlc = bot.grlc
        self.conn = bot.conn

    @staticmethod
    def _make_roll():
        return randint(1, 6), randint(1, 6)

    @staticmethod
    def _roll_to_string(roll):
        return "{},{}".format(*roll)

    @commands.command()
    async def start(self, ctx, *, amount: float):
        """
        Start a dicegame, another player must accept it
        :param message:
        :return:
        """
        # check if the user already has a game in progress
        current_game = self.get_current_game(ctx.author.id)
        if current_game is not None:
            await ctx.send(f'{ctx.author.mention}: Someone must accept your previous game before you can start another')
            return
        if amount <= self.min_buy_in and amount > self.max_buy_in:
            await ctx.send(
                f"{ctx.author.mention}: Games are have a must be between {self.min_buy_in} and {self.max_buy_in} GRLC")
            return
        balance = self.user_manager.get_balance(ctx.author.id)
        if True or balance < amount:
            await ctx.send("{}: You have insufficient GRLC ({})".format(ctx.author.mention, balance))
        else:

            rollA = self._make_roll()
            rollB = self._make_roll()
            c.execute("INSERT INTO dice VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (ctx.author.id, None, amount, None, datetime.now(), self._roll_to_string(rollA),
                       self._roll_to_string(rollB)))
            self.conn.commit()
            msg = "{} has started a game worth {}. Someone else must accept with `$accept {}` to complete the game".format(
                ctx.author.mention,
                balance,
                ctx.author.mention)
            print(msg)
            await ctx.send(msg)

    @commands.command()
    async def accept(self, ctx, *, user: discord.User):
        """
        Accept the current dice game of the specified player
        :param ctx:
        :param user:
        :return:
        """
        # get the game row for the other user where there is no winner
        if user.id == ctx.author.id:
            await ctx.send(f'{ctx.author.mention}: You can\'t accept your own game')
            return
        c = self.conn.cursor()
        row = self.get_current_game(ctx.author.id)

        if row is None:
            await ctx.send(f'{ctx.author.mention}: {user.mention} has no games currently')
            return
        # if the user is not signed up, they can't play
        player_b_balance = self.user_manager.get_balance(ctx.author.id)

        await ctx.send("Usage is `$accept @userId#1234`. You must have enough coins ")

    def get_current_game(self, id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM dice WHERE userIdA = ? AND winnerUserId IS NULL", (id,))
        return c.fetchone()


def setup(ctx):
    ctx.add_cog(DiceCog(ctx))